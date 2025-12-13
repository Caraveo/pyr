#!/usr/bin/env python3
"""
Local AI Agent Runtime
A fully local AI development toolchain powered by Ollama.
"""

import sys
import os
import json
import argparse
from pathlib import Path
from typing import List, Dict, Optional, Any

# Add tools directory to path
sys.path.insert(0, str(Path(__file__).parent))

from tools.fs import (
    load_project_context,
    read_file,
    write_file,
    delete_file,
    find_design_file
)
from tools.shell import (
    run_command,
    check_ollama_available,
    get_ollama_model,
    run_ollama
)
from tools.diff import generate_unified_diff


# Agent modes
MODES = ['code', 'design', 'craft', 'debug', 'test']


class Agent:
    """Main agent class that handles AI interactions and actions."""
    
    def __init__(self, mode: str, cwd: Optional[Path] = None):
        self.mode = mode
        self.cwd = Path(cwd) if cwd else Path.cwd()
        self.conversation_history: List[Dict[str, str]] = []
        self.project_context: Dict[str, str] = {}
        
        # Load prompt
        prompt_file = Path(__file__).parent / 'prompts' / f'{mode}.txt'
        if prompt_file.exists():
            with open(prompt_file, 'r') as f:
                self.base_prompt = f.read()
        else:
            self.base_prompt = f"You are an AI assistant in {mode} mode."
        
        # Load project context
        self.load_context()
    
    def load_context(self):
        """Load project context and design document if available."""
        print("Loading project context...", file=sys.stderr)
        self.project_context = load_project_context(self.cwd)
        
        # For design mode, also load design document
        if self.mode == 'design':
            design_file = find_design_file(self.cwd)
            if design_file:
                design_content = read_file(design_file)
                if design_content:
                    self.project_context['__design__'] = design_content
    
    def build_prompt(self, user_input: str) -> str:
        """Build the full prompt including context and history."""
        prompt_parts = [self.base_prompt]
        
        # Add project context
        if self.project_context:
            prompt_parts.append("\n\nPROJECT CONTEXT:")
            prompt_parts.append("=" * 80)
            
            # Format context as file listings
            for file_path, content in list(self.project_context.items())[:50]:  # Limit context size
                if file_path != '__design__':
                    prompt_parts.append(f"\n--- {file_path} ---")
                    # Truncate very long files
                    if len(content) > 5000:
                        content = content[:5000] + "\n... (truncated)"
                    prompt_parts.append(content)
            
            if len(self.project_context) > 50:
                prompt_parts.append(f"\n... and {len(self.project_context) - 50} more files")
        
        # Add design document if in design mode
        if self.mode == 'design' and '__design__' in self.project_context:
            prompt_parts.append("\n\nEXISTING DESIGN DOCUMENT:")
            prompt_parts.append("=" * 80)
            prompt_parts.append(self.project_context['__design__'])
        
        # Add conversation history
        if self.conversation_history:
            prompt_parts.append("\n\nCONVERSATION HISTORY:")
            prompt_parts.append("=" * 80)
            for entry in self.conversation_history[-5:]:  # Last 5 exchanges
                prompt_parts.append(f"\nUser: {entry['user']}")
                prompt_parts.append(f"Assistant: {entry['assistant']}")
        
        # Add current user input
        prompt_parts.append("\n\nCURRENT REQUEST:")
        prompt_parts.append("=" * 80)
        prompt_parts.append(f"\n{user_input}\n")
        
        prompt_parts.append("\n\nRespond with JSON actions only:")
        
        return "\n".join(prompt_parts)
    
    def parse_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse JSON response from the model."""
        try:
            # Try to extract JSON from response
            response = response.strip()
            
            # Find JSON object in response
            start = response.find('{')
            end = response.rfind('}') + 1
            
            if start == -1 or end == 0:
                print(f"Error: No JSON found in response", file=sys.stderr)
                return None
            
            json_str = response[start:end]
            return json.loads(json_str)
        
        except json.JSONDecodeError as e:
            print(f"Error parsing JSON: {e}", file=sys.stderr)
            print(f"Response was: {response[:500]}", file=sys.stderr)
            return None
    
    def execute_actions(self, actions: List[Dict[str, Any]]) -> str:
        """Execute a list of actions and return a summary."""
        results = []
        
        for action in actions:
            action_type = action.get('type', '').lower()
            target = action.get('target', '')
            content = action.get('content', '')
            
            if action_type == 'edit':
                result = self._action_edit(target, content)
                results.append(result)
            
            elif action_type == 'create':
                result = self._action_create(target, content)
                results.append(result)
            
            elif action_type == 'delete':
                result = self._action_delete(target, content)
                results.append(result)
            
            elif action_type == 'run':
                result = self._action_run(target, content)
                results.append(result)
            
            elif action_type == 'message':
                result = f"Message: {content}"
                results.append(result)
                print(content)
            
            else:
                results.append(f"Unknown action type: {action_type}")
        
        return "\n".join(results)
    
    def _action_edit(self, target: str, content: str) -> str:
        """Edit an existing file."""
        file_path = self.cwd / target
        
        if not file_path.exists():
            return f"Error: File {target} does not exist. Use 'create' action instead."
        
        # Read old content for diff
        old_content = read_file(file_path)
        if old_content is None:
            return f"Error: Could not read {target}"
        
        # Show diff
        diff = generate_unified_diff(old_content, content, str(target))
        if diff.strip():
            print(f"\n--- Changes to {target} ---", file=sys.stderr)
            print(diff, file=sys.stderr)
        
        # Write new content
        if write_file(file_path, content, create_backup=True):
            return f"✓ Edited {target}"
        else:
            return f"✗ Failed to edit {target}"
    
    def _action_create(self, target: str, content: str) -> str:
        """Create a new file."""
        file_path = self.cwd / target
        
        if file_path.exists():
            return f"Error: File {target} already exists. Use 'edit' action instead."
        
        if write_file(file_path, content, create_backup=False):
            print(f"\n--- Created {target} ---", file=sys.stderr)
            print(content[:500] + ("..." if len(content) > 500 else ""), file=sys.stderr)
            return f"✓ Created {target}"
        else:
            return f"✗ Failed to create {target}"
    
    def _action_delete(self, target: str, content: str) -> str:
        """Delete a file."""
        file_path = self.cwd / target
        
        if not file_path.exists():
            return f"Warning: File {target} does not exist."
        
        print(f"Deleting {target}: {content}", file=sys.stderr)
        confirm = input(f"Confirm deletion of {target}? (yes/no): ").strip().lower()
        
        if confirm == 'yes':
            if delete_file(file_path, create_backup=True):
                return f"✓ Deleted {target}"
            else:
                return f"✗ Failed to delete {target}"
        else:
            return f"✗ Deletion cancelled"
    
    def _action_run(self, target: str, content: str) -> str:
        """Run a shell command."""
        command = target
        print(f"\n--- Running: {command} ---", file=sys.stderr)
        print(f"Purpose: {content}", file=sys.stderr)
        
        returncode, stdout, stderr = run_command(command, cwd=self.cwd)
        
        if stdout:
            print(stdout, file=sys.stderr)
        if stderr:
            print(stderr, file=sys.stderr)
        
        if returncode == 0:
            return f"✓ Command succeeded: {command}"
        else:
            return f"✗ Command failed (exit {returncode}): {command}"
    
    def process(self, user_input: str) -> str:
        """Process user input and return response."""
        # Build prompt
        prompt = self.build_prompt(user_input)
        
        # Get model response
        print("Thinking...", file=sys.stderr)
        returncode, stdout, stderr = run_ollama(prompt)
        
        if returncode != 0:
            error_msg = f"Error running Ollama: {stderr}"
            print(error_msg, file=sys.stderr)
            return error_msg
        
        # Parse response
        response_data = self.parse_response(stdout)
        
        if not response_data:
            return "Error: Could not parse model response"
        
        # Execute actions
        actions = response_data.get('actions', [])
        if not actions:
            return "No actions provided in response"
        
        result = self.execute_actions(actions)
        
        # Update conversation history
        self.conversation_history.append({
            'user': user_input,
            'assistant': result
        })
        
        # Reload context if files were modified
        if any(a.get('type') in ['edit', 'create', 'delete'] for a in actions):
            self.load_context()
        
        return result


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Local AI Development Agent')
    parser.add_argument(
        'mode',
        choices=MODES,
        help='Agent mode: code, design, craft, debug, or test'
    )
    parser.add_argument(
        'input',
        nargs='*',
        help='User input (optional, will use interactive mode if not provided)'
    )
    parser.add_argument(
        '--cwd',
        type=str,
        help='Working directory (default: current directory)'
    )
    
    args = parser.parse_args()
    
    # Check Ollama availability
    if not check_ollama_available():
        print("Error: Ollama is not installed or not in PATH.", file=sys.stderr)
        print("Please install Ollama from https://ollama.ai", file=sys.stderr)
        sys.exit(1)
    
    # Create agent
    agent = Agent(args.mode, cwd=args.cwd)
    
    # Handle input
    if args.input:
        # Non-interactive mode
        user_input = ' '.join(args.input)
        result = agent.process(user_input)
        print(result)
    else:
        # Interactive REPL mode (especially for 'code' command)
        if args.mode == 'code':
            print(f"AI Coding Agent (mode: {args.mode})", file=sys.stderr)
            print(f"Working directory: {agent.cwd}", file=sys.stderr)
            print(f"Model: {get_ollama_model()}", file=sys.stderr)
            print("Type 'exit' or 'quit' to exit\n", file=sys.stderr)
            
            try:
                while True:
                    try:
                        user_input = input("agent> ").strip()
                        
                        if not user_input:
                            continue
                        
                        if user_input.lower() in ['exit', 'quit', 'q']:
                            break
                        
                        result = agent.process(user_input)
                        print(result)
                        print()  # Blank line for readability
                    
                    except KeyboardInterrupt:
                        print("\nExiting...", file=sys.stderr)
                        break
                    except EOFError:
                        break
            
            except Exception as e:
                print(f"Error: {e}", file=sys.stderr)
                sys.exit(1)
        else:
            # For other modes, read from stdin or prompt once
            print(f"AI Agent (mode: {args.mode})", file=sys.stderr)
            print(f"Working directory: {agent.cwd}", file=sys.stderr)
            print(f"Model: {get_ollama_model()}", file=sys.stderr)
            print("Enter your request (Ctrl+D to finish):", file=sys.stderr)
            
            try:
                user_input = sys.stdin.read().strip()
                if user_input:
                    result = agent.process(user_input)
                    print(result)
            except KeyboardInterrupt:
                print("\nCancelled.", file=sys.stderr)
                sys.exit(1)


if __name__ == '__main__':
    main()

