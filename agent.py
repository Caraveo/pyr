#!/usr/bin/env python3
"""
Local AI Agent Runtime
A fully local AI development toolchain powered by Ollama.
"""

import sys
import os
import json
import re
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
    find_design_file,
    find_all_design_files
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
    
    def __init__(self, mode: str, cwd: Optional[Path] = None, design_files: Optional[List[Path]] = None):
        self.mode = mode
        self.cwd = Path(cwd) if cwd else Path.cwd()
        self.conversation_history: List[Dict[str, str]] = []
        self.project_context: Dict[str, str] = {}
        self.design_files: List[Path] = design_files or []
        
        # Load prompt
        prompt_file = Path(__file__).parent / 'prompts' / f'{mode}.txt'
        if prompt_file.exists():
            with open(prompt_file, 'r') as f:
                self.base_prompt = f.read()
        else:
            self.base_prompt = f"You are an AI assistant in {mode} mode."
        
        # Load project context
        self.load_context()
        
        # For craft mode, load design files if provided
        if mode == 'craft' and self.design_files:
            self.load_design_files()
    
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
    
    def load_design_files(self):
        """Load design files for craft mode."""
        for design_file in self.design_files:
            if design_file.exists():
                design_content = read_file(design_file)
                if design_content:
                    # Store with filename as key
                    key = f"__design__{design_file.name}"
                    self.project_context[key] = design_content
                    print(f"Loaded design file: {design_file.name}", file=sys.stderr)
    
    def build_prompt(self, user_input: str) -> str:
        """Build the full prompt including context and history."""
        prompt_parts = [self.base_prompt]
        
        # Add project context
        if self.project_context:
            prompt_parts.append("\n\nPROJECT CONTEXT:")
            prompt_parts.append("=" * 80)
            
            # Format context as file listings
            for file_path, content in list(self.project_context.items())[:50]:  # Limit context size
                # Skip design files - they're shown separately
                if not file_path.startswith('__design__'):
                    prompt_parts.append(f"\n--- {file_path} ---")
                    # Truncate very long files
                    if len(content) > 5000:
                        content = content[:5000] + "\n... (truncated)"
                    prompt_parts.append(content)
            
            if len(self.project_context) > 50:
                prompt_parts.append(f"\n... and {len(self.project_context) - 50} more files")
        
        # Add design document(s) if available
        design_keys = [k for k in self.project_context.keys() if k.startswith('__design__')]
        if design_keys:
            if self.mode == 'craft':
                prompt_parts.append("\n\n⚠️  PRIMARY INSTRUCTION: IMPLEMENT THE DESIGN(S) BELOW ⚠️")
                prompt_parts.append("=" * 80)
            else:
                prompt_parts.append("\n\nDESIGN DOCUMENT(S):")
                prompt_parts.append("=" * 80)
            for key in design_keys:
                design_name = key.replace('__design__', '') or 'design document'
                prompt_parts.append(f"\n--- {design_name} ---")
                prompt_parts.append(self.project_context[key])
            if self.mode == 'craft':
                prompt_parts.append("\n" + "=" * 80)
                prompt_parts.append("Use the design document(s) above as your implementation guide.")
                prompt_parts.append("=" * 80)
        
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
        """Parse JSON response from the model with robust error handling."""
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
            
            # Strategy 1: Try parsing as-is first
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass
            
            # Strategy 2: Fix unescaped control characters in string values
            # This function properly escapes control chars within JSON strings
            def fix_json_strings(text):
                result = []
                in_string = False
                escape_next = False
                i = 0
                while i < len(text):
                    char = text[i]
                    
                    if escape_next:
                        result.append(char)
                        escape_next = False
                    elif char == '\\':
                        result.append(char)
                        escape_next = True
                    elif char == '"' and not escape_next:
                        in_string = not in_string
                        result.append(char)
                    elif in_string:
                        # We're inside a string value
                        if ord(char) < 32:  # Control character
                            # Escape common control characters
                            if char == '\n':
                                result.append('\\n')
                            elif char == '\r':
                                result.append('\\r')
                            elif char == '\t':
                                result.append('\\t')
                            # Remove other control characters (0x00-0x1F)
                            # They're not valid in JSON strings
                        else:
                            result.append(char)
                    else:
                        # Outside string - keep as-is
                        result.append(char)
                    i += 1
                return ''.join(result)
            
            json_str_cleaned = fix_json_strings(json_str)
            
            # Try parsing the cleaned version
            try:
                return json.loads(json_str_cleaned)
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON after cleanup: {e}", file=sys.stderr)
                # Show more context around the error
                error_pos = getattr(e, 'pos', None)
                if error_pos:
                    start_pos = max(0, error_pos - 100)
                    end_pos = min(len(json_str_cleaned), error_pos + 100)
                    print(f"Context around error (pos {error_pos}):", file=sys.stderr)
                    print(json_str_cleaned[start_pos:end_pos], file=sys.stderr)
                else:
                    print(f"Problematic JSON (first 1000 chars): {json_str_cleaned[:1000]}", file=sys.stderr)
                return None
        
        except Exception as e:
            print(f"Unexpected error parsing JSON: {e}", file=sys.stderr)
            print(f"Response was: {response[:500]}", file=sys.stderr)
            return None
    
    def execute_actions(self, actions: List[Dict[str, Any]], auto_debug: bool = True) -> str:
        """Execute a list of actions and return a summary."""
        results = []
        failed_commands = []
        
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
                
                # Check if command failed and capture error info
                if result.startswith('✗'):
                    failed_commands.append({
                        'command': target,
                        'purpose': content,
                        'error': result
                    })
            
            elif action_type == 'message':
                result = f"Message: {content}"
                results.append(result)
                print(content)
            
            else:
                results.append(f"Unknown action type: {action_type}")
        
        # Auto-debug if commands failed and auto_debug is enabled
        if failed_commands and auto_debug and self.mode in ['craft', 'code']:
            print("\n" + "="*80, file=sys.stderr)
            print("⚠️  ERRORS DETECTED - Entering iterative debug mode", file=sys.stderr)
            print("="*80, file=sys.stderr)
            
            debug_result = self._iterative_debug(failed_commands)
            results.append("\n--- Debug Session ---")
            results.append(debug_result)
        
        return "\n".join(results)
    
    def _iterative_debug(self, failed_commands: List[Dict[str, Any]], max_iterations: int = 5) -> str:
        """Iteratively debug and fix command failures."""
        debug_agent = Agent('debug', cwd=self.cwd)
        debug_agent.project_context = self.project_context.copy()
        debug_agent.conversation_history = self.conversation_history.copy()
        
        iteration = 0
        all_fixed = False
        
        while iteration < max_iterations and not all_fixed:
            iteration += 1
            print(f"\n🔧 Debug iteration {iteration}/{max_iterations}", file=sys.stderr)
            
            # Build debug prompt with all failed commands
            error_summary = []
            for cmd_info in failed_commands:
                error_summary.append(f"Command: {cmd_info['command']}")
                error_summary.append(f"Purpose: {cmd_info['purpose']}")
                error_summary.append(f"Error: {cmd_info['error']}")
                error_summary.append("")
            
            debug_prompt = f"""The following commands failed. Analyze the errors and fix them:

{chr(10).join(error_summary)}

Examine the project structure, identify what's missing or incorrect, and fix it.
Then re-run the failed commands to verify the fix works."""
            
            # Process with debug agent
            debug_result = debug_agent.process(debug_prompt)
            
            # Check if debug agent ran any commands
            # Extract new failed commands from the result
            if "✗ Command failed" in debug_result:
                # Debug agent tried to fix but command still failed
                # Update failed_commands with new error info
                print(f"⚠️  Issue persists after iteration {iteration}", file=sys.stderr)
                
                # Check if we made progress (created/fixed files)
                if any(keyword in debug_result for keyword in ["✓ Created", "✓ Edited", "✓ Command succeeded"]):
                    print("Progress made, continuing...", file=sys.stderr)
                    # Re-check the original commands
                    new_failed = []
                    for cmd_info in failed_commands:
                        returncode, stdout, stderr = run_command(cmd_info['command'], cwd=self.cwd)
                        if returncode != 0:
                            new_failed.append({
                                'command': cmd_info['command'],
                                'purpose': cmd_info['purpose'],
                                'error': f"✗ Command failed (exit {returncode}): {cmd_info['command']}\n{stdout}\n{stderr}"
                            })
                    failed_commands = new_failed
                    if not new_failed:
                        all_fixed = True
                        print("✓ All issues resolved!", file=sys.stderr)
                else:
                    print("No progress made, may need manual intervention", file=sys.stderr)
                    break
            else:
                # No command failures in debug result - might be fixed
                # Verify by re-running original commands
                new_failed = []
                for cmd_info in failed_commands:
                    returncode, stdout, stderr = run_command(cmd_info['command'], cwd=self.cwd)
                    if returncode != 0:
                        new_failed.append({
                            'command': cmd_info['command'],
                            'purpose': cmd_info['purpose'],
                            'error': f"✗ Command failed (exit {returncode}): {cmd_info['command']}\n{stdout}\n{stderr}"
                        })
                    else:
                        print(f"✓ Verified fix: {cmd_info['command']}", file=sys.stderr)
                
                failed_commands = new_failed
                if not new_failed:
                    all_fixed = True
                    print("✓ All issues resolved!", file=sys.stderr)
                    break
            
            # Update our context with debug agent's changes
            self.project_context.update(debug_agent.project_context)
            self.conversation_history.extend(debug_agent.conversation_history[-1:])  # Add last debug exchange
            
            # Reload context to pick up any file changes
            self.load_context()
        
        if all_fixed:
            return f"✓ Debug complete: All issues resolved after {iteration} iteration(s)"
        else:
            return f"⚠️  Debug incomplete: Some issues may remain after {iteration} iteration(s). Manual intervention may be needed."
    
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
            error_output = f"{stdout}\n{stderr}".strip()
            return f"✗ Command failed (exit {returncode}): {command}\n{error_output}"
    
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
        
        # Execute with auto-debug enabled for craft and code modes
        auto_debug = self.mode in ['craft', 'code']
        result = self.execute_actions(actions, auto_debug=auto_debug)
        
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
    
    # Handle craft mode special cases
    design_files = None
    user_input = None
    cwd = Path(args.cwd) if args.cwd else Path.cwd()
    
    if args.mode == 'craft':
        if not args.input:
            # craft by itself - find all .design files
            design_files = find_all_design_files(cwd)
            if design_files:
                print(f"Found {len(design_files)} design file(s):", file=sys.stderr)
                for df in design_files:
                    print(f"  - {df.name}", file=sys.stderr)
                user_input = "Implement the design(s) from the loaded design files."
            else:
                print("No .design files found in current directory.", file=sys.stderr)
                print("Usage:", file=sys.stderr)
                print("  craft                    # Use all .design files in current directory", file=sys.stderr)
                print("  craft project.design      # Use specific design file", file=sys.stderr)
                print('  craft "your prompt"       # Use prompt to craft code', file=sys.stderr)
                sys.exit(1)
        else:
            # Check if first argument is a .design file
            first_arg = args.input[0]
            potential_design_file = cwd / first_arg
            
            if potential_design_file.exists() and potential_design_file.suffix == '.design':
                # craft project.design - use that specific design file
                design_files = [potential_design_file]
                print(f"Using design file: {potential_design_file.name}", file=sys.stderr)
                # Check if there's additional input
                if len(args.input) > 1:
                    user_input = ' '.join(args.input[1:])
                else:
                    user_input = "Implement the design from the loaded design file."
            else:
                # craft "prompt" - use the prompt
                user_input = ' '.join(args.input)
    else:
        # For other modes, use input as-is
        if args.input:
            user_input = ' '.join(args.input)
    
    # Create agent
    agent = Agent(args.mode, cwd=args.cwd, design_files=design_files)
    
    # Handle input
    if user_input:
        # Non-interactive mode
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

