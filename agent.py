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

# Try to import json5 for more lenient JSON parsing
# json5 handles trailing commas, comments, and other non-standard JSON
try:
    import json5  # type: ignore
    HAS_JSON5 = True
except ImportError:
    HAS_JSON5 = False
    # json5 not available, will use fallback methods
    # Install with: pip3 install json5

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
from tools.structures import (
    detect_structure,
    get_structure_prompt,
    extract_project_name
)
from tools.shell import (
    run_command,
    check_ollama_available,
    get_ollama_model,
    run_ollama
)
from tools.diff import generate_unified_diff
from tools.progress import ProgressTracker, break_down_tasks, generate_todo_list
from tools.progress import ProgressTracker, break_down_tasks, generate_todo_list


# Agent modes
MODES = ['code', 'design', 'craft', 'debug', 'test']


class Agent:
    """Main agent class that handles AI interactions and actions."""
    
    def __init__(self, mode: str, cwd: Optional[Path] = None, design_files: Optional[List[Path]] = None, user_input: str = ""):
        self.mode = mode
        self.cwd = Path(cwd) if cwd else Path.cwd()
        self.conversation_history: List[Dict[str, str]] = []
        self.project_context: Dict[str, str] = {}
        self.design_files: List[Path] = design_files or []
        self.detected_structure: Optional[Dict[str, Any]] = None
        self.project_name: str = ""
        
        # Load prompt
        prompt_file = Path(__file__).parent / 'prompts' / f'{mode}.txt'
        if prompt_file.exists():
            with open(prompt_file, 'r') as f:
                self.base_prompt = f.read()
        else:
            self.base_prompt = f"You are an AI assistant in {mode} mode."
        
        # Detect structure (especially for design mode)
        if mode == 'design' and user_input:
            self.detected_structure = detect_structure(self.cwd, user_input)
            self.project_name = extract_project_name(user_input, self.cwd)
            if self.detected_structure:
                print(f"Detected structure: {self.detected_structure.get('name', 'Unknown')}", file=sys.stderr)
                print(f"Project name: {self.project_name}", file=sys.stderr)
        
        # Load project context
        self.load_context()
        
        # For craft mode, load design files and detect structure
        if mode == 'craft' and self.design_files:
            self.load_design_files()
            # Try to detect structure from design document or existing files
            design_content = ""
            for design_file in self.design_files:
                if design_file.exists():
                    content = read_file(design_file)
                    if content:
                        design_content += content + " "
            
            # Detect structure from design content or existing files
            self.detected_structure = detect_structure(self.cwd, design_content)
            if not self.detected_structure:
                # Try detecting from existing files
                self.detected_structure = detect_structure(self.cwd, "")
            
            # Extract project name from design file name or directory
            if self.design_files:
                self.project_name = self.design_files[0].stem.replace('.design', '')
            else:
                self.project_name = self.cwd.name
            
            if self.detected_structure:
                print(f"Detected structure: {self.detected_structure.get('name', 'Unknown')}", file=sys.stderr)
                print(f"Project name: {self.project_name}", file=sys.stderr)
    
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
        
        # Add structure information for design mode
        if self.mode == 'design' and self.detected_structure:
            structure_prompt = get_structure_prompt(
                self.detected_structure,
                self.project_name,
                user_input
            )
            prompt_parts.append("\n\n" + "=" * 80)
            prompt_parts.append("⚠️  STRUCTURE ASSUMPTIONS ⚠️")
            prompt_parts.append("=" * 80)
            prompt_parts.append("\nThe following structure assumptions have been made based on your request:")
            prompt_parts.append(structure_prompt)
            prompt_parts.append("\n" + "=" * 80)
            prompt_parts.append("IMPORTANT: Include these assumptions in your design document.")
            prompt_parts.append("Specify the technology stack, file structure, and build/run commands.")
            prompt_parts.append("=" * 80)
        
        # Add structure information for craft mode (before design documents)
        if self.mode == 'craft' and self.detected_structure:
            structure_prompt = get_structure_prompt(
                self.detected_structure,
                self.project_name,
                user_input
            )
            assumptions = self.detected_structure.get('assumptions', {})
            structure_def = assumptions.get('structure', {})
            
            prompt_parts.append("\n\n" + "=" * 80)
            prompt_parts.append("⚠️  PROJECT STRUCTURE REQUIREMENTS ⚠️")
            prompt_parts.append("=" * 80)
            prompt_parts.append(structure_prompt)
            
            # List required files that are missing
            missing_files = []
            for file_path, file_info in structure_def.items():
                if file_info.get('required', False):
                    # Replace {PROJECT_NAME} placeholder
                    actual_path = file_path.replace('{PROJECT_NAME}', self.project_name)
                    file_full_path = self.cwd / actual_path
                    if not file_full_path.exists():
                        missing_files.append((actual_path, file_info))
            
            if missing_files:
                prompt_parts.append("\n" + "=" * 80)
                prompt_parts.append("⚠️  CRITICAL: MISSING REQUIRED FILES ⚠️")
                prompt_parts.append("=" * 80)
                prompt_parts.append("\nThe following required files are MISSING and MUST be created FIRST:")
                for file_path, file_info in missing_files:
                    template = file_info.get('template', '')
                    # Replace placeholders in template
                    template = template.replace('{PROJECT_NAME}', self.project_name)
                    prompt_parts.append(f"\n- {file_path}")
                    prompt_parts.append(f"  Description: {file_info.get('description', '')}")
                    prompt_parts.append(f"  Template:\n{template}")
                prompt_parts.append("\n" + "=" * 80)
                prompt_parts.append("ACTION REQUIRED: Create ALL missing required files BEFORE implementing other features.")
                prompt_parts.append("These files are essential for the project to build and run.")
                prompt_parts.append("=" * 80)
        
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
        """Parse JSON response from the model with robust error handling using multiple strategies."""
        try:
            # Try to extract JSON from response
            response = response.strip()
            
            # Remove markdown code blocks if present
            # Handle ```json ... ``` or ``` ... ```
            if response.startswith('```'):
                # Find the closing ```
                end_marker = response.find('```', 3)
                if end_marker != -1:
                    # Extract content between code blocks
                    response = response[3:end_marker].strip()
                    # Remove language tag if present (e.g., "json")
                    if response.startswith('json'):
                        response = response[4:].strip()
                    if response.startswith('\n'):
                        response = response[1:].strip()
            
            # Find JSON object in response
            start = response.find('{')
            end = response.rfind('}') + 1
            
            if start == -1 or end == 0:
                print(f"Error: No JSON found in response", file=sys.stderr)
                return None
            
            json_str = response[start:end]
            
            # Strategy 1: Try standard JSON parser (fast path)
            try:
                return json.loads(json_str)
            except json.JSONDecodeError:
                pass
            
            # Strategy 2: Try json5 (more lenient, handles trailing commas, comments, etc.)
            if HAS_JSON5:
                try:
                    return json5.loads(json_str)
                except Exception:
                    pass
            
            # Strategy 3: Fix common JSON issues
            json_str_fixed = self._fix_common_json_issues(json_str)
            try:
                return json.loads(json_str_fixed)
            except json.JSONDecodeError:
                pass
            
            # Strategy 4: Try json5 on fixed version
            if HAS_JSON5:
                try:
                    return json5.loads(json_str_fixed)
                except Exception:
                    pass
            
            # Strategy 5: Fix unescaped newlines in content fields specifically
            # This handles cases where the model outputs literal \n instead of \\n
            try:
                # Find all "content": "..." fields and fix newlines
                def fix_content_newlines_in_json(text):
                    result = []
                    i = 0
                    in_content_value = False
                    content_start = -1
                    
                    while i < len(text):
                        # Look for "content": pattern
                        if (i + 10 < len(text) and 
                            text[i:i+10] == '"content":'):
                            # Skip to the opening quote
                            j = i + 10
                            while j < len(text) and text[j] in ' \t\n\r:':
                                j += 1
                            if j < len(text) and text[j] == '"':
                                in_content_value = True
                                content_start = j
                                result.append(text[i:j+1])
                                i = j + 1
                                continue
                        
                        if in_content_value:
                            # We're inside a content string value
                            if text[i] == '\\':
                                # Escaped character
                                if i + 1 < len(text):
                                    result.append(text[i:i+2])
                                    i += 2
                                else:
                                    result.append(text[i])
                                    i += 1
                            elif text[i] == '"':
                                # Check if this closes the content string
                                # Look ahead to see if we have a comma or closing brace
                                j = i + 1
                                while j < len(text) and text[j] in ' \t\n\r':
                                    j += 1
                                if j >= len(text) or text[j] in ',}]':
                                    # This closes the content string
                                    in_content_value = False
                                    result.append(text[i])
                                    i += 1
                                else:
                                    # Escaped quote
                                    result.append('\\"')
                                    i += 1
                            elif text[i] == '\n' and (i == 0 or text[i-1] != '\\'):
                                # Unescaped newline - escape it
                                result.append('\\n')
                                i += 1
                            elif text[i] == '\r' and (i == 0 or text[i-1] != '\\'):
                                # Unescaped carriage return
                                result.append('\\r')
                                i += 1
                            elif text[i] == '\t' and (i == 0 or text[i-1] != '\\'):
                                # Unescaped tab
                                result.append('\\t')
                                i += 1
                            else:
                                result.append(text[i])
                                i += 1
                        else:
                            result.append(text[i])
                            i += 1
                    
                    return ''.join(result)
                
                json_str_content_fixed = fix_content_newlines_in_json(json_str)
                try:
                    return json.loads(json_str_content_fixed)
                except json.JSONDecodeError:
                    # Try with json5 if available
                    if HAS_JSON5:
                        try:
                            return json5.loads(json_str_content_fixed)
                        except:
                            pass
            except Exception:
                pass
            
            # Strategy 6: Try to convert alternative JSON formats to standard format
            # Some models return {"action": "...", "file_path": "...", "content": "..."} instead of {"actions": [...]}
            # Also handle multiple JSON objects separated by newlines
            try:
                # Try to find all JSON objects in the response
                json_objects = []
                i = 0
                while i < len(json_str):
                    if json_str[i] == '{':
                        # Find matching closing brace
                        depth = 0
                        start = i
                        for j in range(i, len(json_str)):
                            if json_str[j] == '{':
                                depth += 1
                            elif json_str[j] == '}':
                                depth -= 1
                                if depth == 0:
                                    # Found complete object
                                    obj_str = json_str[start:j+1]
                                    try:
                                        parsed = json.loads(obj_str)
                                        json_objects.append(parsed)
                                    except:
                                        pass
                                    i = j + 1
                                    break
                        else:
                            i += 1
                    else:
                        i += 1
                
                # Process all found JSON objects
                if json_objects:
                    actions = []
                    for parsed in json_objects:
                        # Check if it's a single action object
                        if isinstance(parsed, dict) and 'action' in parsed:
                            # Convert single action to actions array format
                            action_type_map = {
                                'create_project': 'create',
                                'add_file': 'create',
                                'create_file': 'create',
                                'edit_file': 'edit',
                                'update_file': 'edit',
                                'delete_file': 'delete',
                                'run_command': 'run',
                                'execute': 'run'
                            }
                            action_type = action_type_map.get(parsed.get('action', ''), 'create')
                            target = parsed.get('file_path') or parsed.get('target') or parsed.get('file', '')
                            content = parsed.get('content') or parsed.get('code') or ''
                            
                            actions.append({
                                "type": action_type,
                                "target": target,
                                "content": content
                            })
                        # Check if it's already in the correct format
                        elif isinstance(parsed, dict) and 'actions' in parsed:
                            if isinstance(parsed['actions'], list):
                                actions.extend(parsed['actions'])
                    
                    if actions:
                        return {"actions": actions}
                
                # Try single object parse
                parsed = json.loads(json_str)
                if isinstance(parsed, dict) and 'action' in parsed:
                    action_type_map = {
                        'create_project': 'create',
                        'add_file': 'create',
                        'create_file': 'create',
                        'edit_file': 'edit',
                        'update_file': 'edit',
                        'delete_file': 'delete',
                        'run_command': 'run',
                        'execute': 'run'
                    }
                    action_type = action_type_map.get(parsed.get('action', ''), 'create')
                    target = parsed.get('file_path') or parsed.get('target') or parsed.get('file', '')
                    content = parsed.get('content') or parsed.get('code') or ''
                    
                    return {
                        "actions": [{
                            "type": action_type,
                            "target": target,
                            "content": content
                        }]
                    }
                # Check if it's already in the correct format
                elif isinstance(parsed, dict) and 'actions' in parsed:
                    return parsed
            except:
                pass
            
            # Strategy 7: Extract actions array directly using regex (last resort)
            actions_match = re.search(r'"actions"\s*:\s*\[(.*?)\]', json_str, re.DOTALL)
            if actions_match:
                try:
                    # Try to reconstruct valid JSON
                    actions_str = actions_match.group(1)
                    # Simple extraction - look for action objects
                    action_objects = re.findall(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', actions_str)
                    if action_objects:
                        actions = []
                        for obj_str in action_objects:
                            try:
                                # Try to parse individual action
                                obj_str = '{' + obj_str.strip('{}') + '}'
                                # Fix common issues in action object
                                obj_fixed = self._fix_common_json_issues(obj_str)
                                action = json.loads(obj_fixed)
                                actions.append(action)
                            except:
                                continue
                        if actions:
                            return {"actions": actions}
                except Exception:
                    pass
            
            # If all strategies fail, show error but don't crash
            print(f"Warning: Could not parse JSON response after all strategies", file=sys.stderr)
            print(f"Response preview (first 500 chars): {response[:500]}", file=sys.stderr)
            return None
        
        except Exception as e:
            print(f"Unexpected error parsing JSON: {e}", file=sys.stderr)
            return None
    
    def _fix_common_json_issues(self, json_str: str) -> str:
        """Fix common JSON issues like invalid escape sequences, unescaped control chars, etc."""
        result = []
        in_string = False
        escape_next = False
        i = 0
        
        while i < len(json_str):
            char = json_str[i]
            
            if escape_next:
                # We're processing an escaped character
                if char in ['n', 'r', 't', 'b', 'f', '\\', '"', '/']:
                    # Valid escape sequences
                    result.append('\\' + char)
                elif char == 'u':
                    # Unicode escape - try to preserve it
                    if i + 4 < len(json_str):
                        result.append('\\u' + json_str[i+1:i+5])
                        i += 4
                    else:
                        result.append('\\u0000')  # Invalid, replace with null
                else:
                    # Invalid escape sequence - remove the backslash or replace
                    # Common invalid escapes: \s, \d, etc. - just output the char
                    result.append(char)
                escape_next = False
            elif char == '\\':
                result.append(char)
                escape_next = True
            elif char == '"':
                # Check if this quote is escaped
                if i > 0 and json_str[i-1] == '\\':
                    # Check if the backslash itself is escaped
                    backslash_count = 0
                    j = i - 1
                    while j >= 0 and json_str[j] == '\\':
                        backslash_count += 1
                        j -= 1
                    # If odd number of backslashes, the quote is escaped
                    if backslash_count % 2 == 1:
                        result.append(char)
                    else:
                        in_string = not in_string
                        result.append(char)
                else:
                    in_string = not in_string
                    result.append(char)
            elif in_string:
                # Inside a string value
                if ord(char) < 32:  # Control character
                    # Escape common control characters
                    if char == '\n':
                        result.append('\\n')
                    elif char == '\r':
                        result.append('\\r')
                    elif char == '\t':
                        result.append('\\t')
                    # Remove other control characters
                elif char == '"':
                    # Unescaped quote inside string - escape it
                    result.append('\\"')
                else:
                    result.append(char)
            else:
                # Outside string
                result.append(char)
            i += 1
        
        # Additional pass: fix unescaped newlines that might have been missed
        # Look for patterns like: "content": "...\n..." where \n is not escaped
        fixed = ''.join(result)
        
        # Try to fix unescaped newlines in "content" fields more aggressively
        # This regex finds "content": "..." and fixes newlines inside
        import re
        def fix_content_newlines(match):
            prefix = match.group(1)  # "content": "
            content = match.group(2)  # the content
            suffix = match.group(3)  # closing quote
            
            # Escape newlines, carriage returns, and tabs
            content = content.replace('\n', '\\n')
            content = content.replace('\r', '\\r')
            content = content.replace('\t', '\\t')
            # Escape quotes that aren't already escaped
            content = re.sub(r'(?<!\\)"', '\\"', content)
            
            return prefix + content + suffix
        
        # Match "content": "..." patterns
        fixed = re.sub(
            r'("content"\s*:\s*")(.*?)(")',
            fix_content_newlines,
            fixed,
            flags=re.DOTALL
        )
        
        return fixed
    
    def execute_actions(self, actions: List[Dict[str, Any]], auto_debug: bool = True) -> str:
        """Execute a list of actions and return a summary."""
        results = []
        failed_commands = []
        
        # Normalize action types - handle common variations
        def normalize_action_type(action_type: str) -> str:
            action_type = action_type.lower().strip()
            # Map common variations to standard types
            variations = {
                'createfile': 'create',
                'create_file': 'create',
                'write': 'create',
                'writefile': 'create',
                'editfile': 'edit',
                'edit_file': 'edit',
                'modify': 'edit',
                'update': 'edit',
                'deletefile': 'delete',
                'delete_file': 'delete',
                'remove': 'delete',
                'execute': 'run',
                'exec': 'run',
                'command': 'run',
                'runcommand': 'run',
                'msg': 'message',
                'say': 'message',
                'tell': 'message'
            }
            return variations.get(action_type, action_type)
        
        for action in actions:
            action_type_raw = action.get('type', '').lower()
            action_type = normalize_action_type(action_type_raw)
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
                # If normalization didn't help, show helpful error
                results.append(f"Unknown action type: '{action_type_raw}' (normalized: '{action_type}')")
                results.append(f"Valid action types are: edit, create, delete, run, message")
                # Try to infer intent
                if 'file' in action_type_raw or 'write' in action_type_raw:
                    results.append(f"Hint: Did you mean 'create'? Attempting to create file anyway...")
                    result = self._action_create(target, content)
                    results.append(result)
        
        # Auto-debug if commands failed and auto_debug is enabled
        if failed_commands and auto_debug and self.mode in ['craft', 'code']:
            print("\n" + "="*80, file=sys.stderr)
            print("⚠️  ERRORS DETECTED - Entering iterative debug mode", file=sys.stderr)
            print("="*80, file=sys.stderr)
            
            debug_result = self._iterative_debug(failed_commands)
            results.append("\n--- Debug Session ---")
            results.append(debug_result)
        
        return "\n".join(results)
    
    def execute_actions_with_progress(self, actions: List[Dict[str, Any]], progress: ProgressTracker, auto_debug: bool = True) -> str:
        """Execute actions with progress tracking."""
        results = []
        failed_commands = []
        
        # Normalize action types - handle common variations
        def normalize_action_type(action_type: str) -> str:
            action_type = action_type.lower().strip()
            variations = {
                'createfile': 'create',
                'create_file': 'create',
                'write': 'create',
                'writefile': 'create',
                'editfile': 'edit',
                'edit_file': 'edit',
                'modify': 'edit',
                'update': 'edit',
                'deletefile': 'delete',
                'delete_file': 'delete',
                'remove': 'delete',
                'execute': 'run',
                'exec': 'run',
                'command': 'run',
                'runcommand': 'run',
                'msg': 'message',
                'say': 'message',
                'tell': 'message'
            }
            return variations.get(action_type, action_type)
        
        for i, action in enumerate(actions):
            progress.start_subtask(i)
            
            action_type_raw = action.get('type', '').lower()
            action_type = normalize_action_type(action_type_raw)
            target = action.get('target', '')
            content = action.get('content', '')
            
            # Check if this is a large action that needs breaking down
            if action_type in ['create', 'edit'] and len(content) > 5000:
                # Break down large content
                print(f"\n📦 Breaking down large task: {target}", file=sys.stderr)
                chunks = break_down_tasks(content)
                print(f"   Split into {len(chunks)} chunks", file=sys.stderr)
                
                # Process chunks
                for chunk_idx, chunk in enumerate(chunks):
                    chunk_action = action.copy()
                    chunk_action['content'] = chunk
                    if chunk_idx > 0:
                        # For subsequent chunks, append to file
                        if action_type == 'create':
                            action_type = 'edit'  # Change to edit for appending
                            chunk_action['type'] = 'edit'
                    
                    # Execute chunk
                    if action_type == 'edit':
                        result = self._action_edit(target, chunk_action['content'])
                    elif action_type == 'create':
                        result = self._action_create(target, chunk_action['content'])
                    else:
                        result = f"Skipped chunk {chunk_idx + 1}"
                    results.append(result)
            else:
                # Normal action execution
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
                    # If normalization didn't help, show helpful error
                    results.append(f"Unknown action type: '{action_type_raw}' (normalized: '{action_type}')")
                    results.append(f"Valid action types are: edit, create, delete, run, message")
                    # Try to infer intent
                    if 'file' in action_type_raw or 'write' in action_type_raw:
                        results.append(f"Hint: Did you mean 'create'? Attempting to create file anyway...")
                        result = self._action_create(target, content)
                        results.append(result)
            
            progress.complete_subtask(i)
        
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
        debug_agent = Agent('debug', cwd=self.cwd, user_input="")
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
            
            # Add structure information if available
            structure_info = ""
            if self.detected_structure:
                assumptions = self.detected_structure.get('assumptions', {})
                structure_info = f"\n\nIMPORTANT - PROJECT STRUCTURE REQUIREMENTS:\n"
                structure_info += f"Language: {assumptions.get('language', 'Unknown')}\n"
                structure_info += f"Package Manager: {assumptions.get('package_manager', 'Unknown')}\n"
                
                # Add critical file locations
                structure_def = assumptions.get('structure', {})
                if structure_def:
                    structure_info += f"\nCRITICAL FILE LOCATIONS (must be at project root, not in subdirectories):\n"
                    for file_path, file_info in structure_def.items():
                        if file_info.get('required', False):
                            # Check if this is a root-level file (no directory prefix)
                            if '/' not in file_path and '\\' not in file_path:
                                structure_info += f"  - {file_path}: MUST be at project root (./{file_path}), NOT in Sources/ or subdirectories\n"
                            else:
                                structure_info += f"  - {file_path}: {file_info.get('description', '')}\n"
                
                structure_info += f"\nCommon mistakes to avoid:\n"
                structure_info += f"- Package.swift, package.json, Cargo.toml, go.mod, requirements.txt MUST be at project root\n"
                structure_info += f"- Do NOT create these files in subdirectories like Sources/, src/, etc.\n"
                structure_info += f"- Check the current directory structure before creating files\n"
            
            debug_prompt = f"""The following commands failed. Analyze the errors and fix them:

{chr(10).join(error_summary)}
{structure_info}

CRITICAL: Before creating any files, check where they should be located.
- Manifest files (Package.swift, package.json, Cargo.toml, go.mod, requirements.txt) MUST be at the PROJECT ROOT
- Do NOT create manifest files in subdirectories
- Verify file locations match the project structure requirements above

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
        
        # Generate todo list
        design_content = ""
        for key in self.project_context.keys():
            if key.startswith('__design__'):
                design_content += self.project_context[key] + "\n"
        
        todos = generate_todo_list(actions, design_content)
        if todos:
            print("\n" + "="*80, file=sys.stderr)
            print("📋 TODO LIST", file=sys.stderr)
            print("="*80, file=sys.stderr)
            for i, todo in enumerate(todos, 1):
                print(f"  {i}. {todo}", file=sys.stderr)
            print("="*80 + "\n", file=sys.stderr)
        
        # Check if we need to break down tasks
        large_actions = []
        for action in actions:
            content = action.get('content', '')
            if len(content) > 5000:  # Large content
                large_actions.append(action)
        
        # Execute with progress tracking
        if len(actions) > 1 or large_actions:
            # Use progress tracker for multiple actions
            progress = ProgressTracker(total_tasks=len(actions), task_name="Executing actions")
            result = self.execute_actions_with_progress(actions, progress, auto_debug=self.mode in ['craft', 'code'])
            progress.finish()
        else:
            # Single action, no progress needed
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
    
    # Create agent (pass user_input for structure detection in design mode)
    agent = Agent(args.mode, cwd=args.cwd, design_files=design_files, user_input=user_input or "")
    
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

