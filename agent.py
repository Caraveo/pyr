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
    find_all_design_files,
    find_test_files
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
        
        # Detect structure (especially for design and test modes)
        if mode in ['design', 'test'] and user_input:
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
        
        # For design mode, add explicit reminder with example
        if self.mode == 'design':
            prompt_parts.append("\n" + "=" * 80)
            prompt_parts.append("⚠️  CRITICAL REMINDER: YOU ARE IN DESIGN MODE ⚠️")
            prompt_parts.append("=" * 80)
            prompt_parts.append(f"Create or edit ONLY: {self.project_name}.design")
            prompt_parts.append("")
            prompt_parts.append("Write a DESIGN DOCUMENT (markdown text), NOT code files.")
            prompt_parts.append("Describe the architecture, file structure, and components.")
            prompt_parts.append("")
            prompt_parts.append("EXAMPLE: If creating Dice.design, write markdown like:")
            prompt_parts.append("  # Dice Design")
            prompt_parts.append("  ## File Structure")
            prompt_parts.append("  - Package.swift: Swift Package Manager manifest")
            prompt_parts.append("  - Sources/Dice/App.swift: Main app entry point")
            prompt_parts.append("")
            prompt_parts.append("DO NOT create Package.swift, *.swift, or any code files!")
            prompt_parts.append("ONLY create the .design file with text descriptions!")
            prompt_parts.append("=" * 80)
        
        # For test mode, add explicit reminder with example
        if self.mode == 'test':
            prompt_parts.append("\n" + "=" * 80)
            prompt_parts.append("⚠️  CRITICAL REMINDER: YOU ARE IN TEST MODE ⚠️")
            prompt_parts.append("=" * 80)
            prompt_parts.append(f"Create or edit ONLY: {self.project_name}.test")
            prompt_parts.append("")
            prompt_parts.append("Write a TEST DESIGN DOCUMENT (markdown text), NOT test code files.")
            prompt_parts.append("Describe the test strategy, test cases, and testing approach.")
            prompt_parts.append("")
            prompt_parts.append("EXAMPLE: If creating Dice.test, write markdown like:")
            prompt_parts.append("  # Dice Test Design")
            prompt_parts.append("  ## Unit Tests")
            prompt_parts.append("  - Test: Create todo item with title")
            prompt_parts.append("  - Test: Toggle completion status")
            prompt_parts.append("")
            prompt_parts.append("DO NOT create test_*.py, *Test.swift, or any test code files!")
            prompt_parts.append("ONLY create the .test file with test design descriptions!")
            prompt_parts.append("=" * 80)
        
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
            
            # Find JSON object in response - try to find complete objects
            # Look for the main actions object
            actions_start = response.find('"actions"')
            if actions_start != -1:
                # Find the opening brace before "actions"
                start = response.rfind('{', 0, actions_start)
                if start == -1:
            start = response.find('{')
                
                # Find matching closing brace
                if start != -1:
                    depth = 0
                    end = -1
                    for i in range(start, len(response)):
                        if response[i] == '{':
                            depth += 1
                        elif response[i] == '}':
                            depth -= 1
                            if depth == 0:
                                end = i + 1
                                break
                    
                    if end == -1:
                        # Incomplete JSON - try to find last closing brace
            end = response.rfind('}') + 1
            else:
                # No "actions" found, try to find any JSON object
                start = response.find('{')
                if start != -1:
                    end = response.rfind('}') + 1
                else:
                    end = -1
            
            if start == -1 or end == 0:
                print(f"Error: No JSON found in response", file=sys.stderr)
                return None
            
            json_str = response[start:end]
            
            # Strategy 1: Try standard JSON parser (fast path)
            try:
                parsed = json.loads(json_str)
                # Normalize field names if needed (path -> target)
                if isinstance(parsed, dict) and 'actions' in parsed:
                    for action in parsed.get('actions', []):
                        if isinstance(action, dict):
                            if 'path' in action and 'target' not in action:
                                action['target'] = action.pop('path')
                            if 'file_path' in action and 'target' not in action:
                                action['target'] = action.pop('file_path')
                return parsed
        except json.JSONDecodeError as e:
                # If JSON is incomplete, try to fix it
                if 'Expecting' in str(e) or 'Unterminated' in str(e):
                    # Try to complete the JSON by adding missing closing braces
                    open_braces = json_str.count('{')
                    close_braces = json_str.count('}')
                    missing = open_braces - close_braces
                    if missing > 0:
                        # Also check for incomplete strings
                        json_str_fixed = json_str
                        # Count unclosed quotes in strings
                        in_string = False
                        escape_next = False
                        for char in json_str:
                            if escape_next:
                                escape_next = False
                            elif char == '\\':
                                escape_next = True
                            elif char == '"' and not escape_next:
                                in_string = not in_string
                        
                        # If string is unclosed, close it
                        if in_string:
                            json_str_fixed = json_str_fixed.rstrip() + '"'
                        
                        json_str_fixed += '}' * missing
                        try:
                            parsed = json.loads(json_str_fixed)
                            # Normalize field names
                            if isinstance(parsed, dict) and 'actions' in parsed:
                                for action in parsed.get('actions', []):
                                    if isinstance(action, dict):
                                        if 'path' in action and 'target' not in action:
                                            action['target'] = action.pop('path')
                                        if 'file_path' in action and 'target' not in action:
                                            action['target'] = action.pop('file_path')
                            return parsed
                        except:
                            pass
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
                            target = (parsed.get('file_path') or parsed.get('target') or 
                                     parsed.get('path') or parsed.get('file') or 
                                     parsed.get('file_name') or '').strip()
                            content = parsed.get('content') or parsed.get('code') or parsed.get('data') or ''
                            
                            # Only add if target is not empty
                            if target:
                                actions.append({
                                    "type": action_type,
                                    "target": target,
                                    "content": content
                                })
                            else:
                                # Try to infer target from other fields
                                project_name = parsed.get('project_name', '')
                                if project_name and action_type == 'create':
                                    # Might be creating a project structure
                                    target = f"{project_name}.design"
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
                    target = (parsed.get('file_path') or parsed.get('target') or 
                             parsed.get('path') or parsed.get('file') or '').strip()
                    content = parsed.get('content') or parsed.get('code') or ''
                    
                    if target:  # Only return if target is not empty
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
            # Try multiple field names for target
            target = (action.get('target') or action.get('path') or 
                     action.get('file_path') or action.get('file') or '').strip()
            content = action.get('content', '')
            
            # Validate target is not empty for file operations
            if action_type in ['edit', 'create', 'delete'] and not target:
                results.append(f"✗ Error: Action type '{action_type}' requires a 'target' field (file path), but target is empty or missing.")
                results.append(f"   Action data: {action}")
                continue
            
            # For design mode, enforce .design file restriction
            if self.mode == 'design' and action_type in ['create', 'edit']:
                if not target.endswith('.design'):
                    results.append(f"✗ Error: Design mode can ONLY create/edit .design files. Attempted to {action_type}: {target}")
                    results.append(f"   Please use a .design file as the target (e.g., '{self.project_name}.design')")
                    continue
            
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
            target = action.get('target', '').strip()
            content = action.get('content', '')
            
            # Validate target is not empty for file operations
            if action_type in ['edit', 'create', 'delete'] and not target:
                results.append(f"✗ Error: Action type '{action_type}' requires a 'target' field (file path), but target is empty or missing.")
                results.append(f"   Action data: {action}")
                progress.complete_subtask(i)
                continue
            
            # For design mode, enforce .design file restriction
            if self.mode == 'design' and action_type in ['create', 'edit']:
                if not target.endswith('.design'):
                    results.append(f"✗ Error: Design mode can ONLY create/edit .design files. Attempted to {action_type}: {target}")
                    results.append(f"   Please use a .design file as the target (e.g., '{self.project_name}.design')")
                    progress.complete_subtask(i)
                    continue
            
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
    
    def _debug_command(self, command: str, max_iterations: int = 5) -> str:
        """Debug a specific command by running it, analyzing failures, and fixing iteratively.
        
        Stops when command succeeds or max_iterations reached (whichever comes first).
        """
        print(f"\n🔍 Debugging command: {command}", file=sys.stderr)
        print("="*80, file=sys.stderr)
        
        # First, run the command to see if it fails
        print(f"\n--- Running: {command} ---", file=sys.stderr)
        returncode, stdout, stderr = run_command(command, cwd=self.cwd)
        
        if returncode == 0:
            print(f"✓ Command succeeded on first try!", file=sys.stderr)
            return f"✓ Command '{command}' succeeded.\n{stdout}"
        
        # Command failed - enter debug loop
        print(f"✗ Command failed (exit {returncode})", file=sys.stderr)
        print(f"Error output:\n{stderr}\n{stdout}", file=sys.stderr)
        print(f"\nWill iterate until command succeeds (max {max_iterations} attempts)", file=sys.stderr)
        
        iteration = 0
        last_error = stderr + "\n" + stdout
        previous_file_count = len(list(self.cwd.rglob('*'))) if self.cwd.exists() else 0
        
        while iteration < max_iterations:
            iteration += 1
            print(f"\n🔧 Debug iteration {iteration} (will stop when command succeeds)", file=sys.stderr)
            print("="*80, file=sys.stderr)
            
            # Track files before this iteration
            files_before = set(self.project_context.keys())
            
            # Build debug prompt with project context
            context_summary = ""
            if self.project_context:
                context_summary = "\n\nPROJECT CONTEXT (available files):\n"
                file_list = [f for f in self.project_context.keys() if not f.startswith('__design__')]
                context_summary += f"Found {len(file_list)} file(s) in project:\n"
                for file_path in sorted(file_list)[:20]:  # Show first 20 files
                    context_summary += f"  - {file_path}\n"
                if len(file_list) > 20:
                    context_summary += f"  ... and {len(file_list) - 20} more files\n"
            
            # Build debug prompt
            debug_prompt = f"""The following command failed:

Command: {command}
Exit code: {returncode}
Error output:
{last_error}
{context_summary}

YOUR TASK:
1. FIRST: Analyze and summarize the error in a "message" action
   - What went wrong?
   - What is the specific issue?
   - What was the command trying to do?

2. SECOND: Examine the project context above
   - What files exist?
   - What files are missing?
   - What needs to be created or fixed?

3. THIRD: Apply a minimal fix
   - Create missing files
   - Fix incorrect code or configuration
   - Make targeted changes

4. FOURTH: Verify the fix
   - Include a "run" action to re-execute: {command}
   - This verifies your fix works

Remember: Start with analysis, use project context, then fix and verify."""
            
            # Add structure information if available
            if self.detected_structure:
                assumptions = self.detected_structure.get('assumptions', {})
                structure_info = f"\n\nIMPORTANT - PROJECT STRUCTURE REQUIREMENTS:\n"
                structure_info += f"Language: {assumptions.get('language', 'Unknown')}\n"
                structure_info += f"Package Manager: {assumptions.get('package_manager', 'Unknown')}\n"
                
                structure_def = assumptions.get('structure', {})
                if structure_def:
                    structure_info += f"\nCRITICAL FILE LOCATIONS:\n"
                    for file_path, file_info in structure_def.items():
                        if file_info.get('required', False):
                            if '/' not in file_path and '\\' not in file_path:
                                structure_info += f"  - {file_path}: MUST be at project root\n"
                            else:
                                structure_info += f"  - {file_path}: {file_info.get('description', '')}\n"
                
                debug_prompt += structure_info
            
            # Process with debug agent
            debug_agent = Agent('debug', cwd=self.cwd, user_input="")
            debug_agent.project_context = self.project_context.copy()
            debug_agent.conversation_history = self.conversation_history.copy()
            
            debug_result = debug_agent.process(debug_prompt)
            
            # Check if any changes were made
            self.load_context()  # Reload to get latest file state
            files_after = set(self.project_context.keys())
            files_changed = files_after - files_before
            files_removed = files_before - files_after
            
            # Check if any file modifications were made
            has_changes = len(files_changed) > 0 or len(files_removed) > 0
            has_actions = any(keyword in debug_result for keyword in ["✓ Created", "✓ Edited", "✓ Deleted", "--- Created", "--- Edited", "--- Deleted"])
            
            if not has_changes and not has_actions:
                print(f"⚠️  WARNING: No changes detected in iteration {iteration}!", file=sys.stderr)
                print(f"   Debug agent did not create, edit, or delete any files.", file=sys.stderr)
                print(f"   This may indicate the agent needs more context or a different approach.", file=sys.stderr)
                # Still continue to next iteration, but warn the user
            
            if has_changes:
                print(f"✓ Changes detected: {len(files_changed)} file(s) added, {len(files_removed)} file(s) removed", file=sys.stderr)
                if files_changed:
                    for f in list(files_changed)[:5]:  # Show first 5
                        print(f"   + {f}", file=sys.stderr)
                if files_removed:
                    for f in list(files_removed)[:5]:  # Show first 5
                        print(f"   - {f}", file=sys.stderr)
            
            # Update our context
            self.project_context.update(debug_agent.project_context)
            self.conversation_history.extend(debug_agent.conversation_history[-1:])
            
            # Check if debug agent ran the command again and it succeeded
            if f"✓ Command succeeded" in debug_result or f"✓ Command '{command}'" in debug_result:
                # Success! Command was re-run and succeeded
                print(f"\n✓ Command fixed and verified after {iteration} iteration(s)!", file=sys.stderr)
                print(f"Stopping debug loop - command now succeeds.", file=sys.stderr)
                return f"✓ Debug complete: Command '{command}' now works after {iteration} iteration(s).\n\n{debug_result}"
            
            # Re-run the original command to check if it works now
            print(f"\n--- Re-running: {command} ---", file=sys.stderr)
            returncode, stdout, stderr = run_command(command, cwd=self.cwd)
            
            if returncode == 0:
                # Success! Stop immediately
                print(f"✓ Command fixed and verified!", file=sys.stderr)
                print(f"Stopping debug loop - command now succeeds.", file=sys.stderr)
                return f"✓ Debug complete: Command '{command}' now works after {iteration} iteration(s).\n{stdout}"
            
            # Still failing - update error for next iteration
            last_error = stderr + "\n" + stdout
            print(f"⚠️  Command still failing after iteration {iteration}", file=sys.stderr)
            print(f"Continuing to next iteration...", file=sys.stderr)
            print(f"New error:\n{last_error}", file=sys.stderr)
        
        # Max iterations reached (safety limit)
        print(f"\n⚠️  Reached maximum iterations ({max_iterations})", file=sys.stderr)
        return f"⚠️  Debug incomplete: Command '{command}' still failing after {max_iterations} iteration(s).\nLast error: {last_error}\n\nDebug attempts:\n{debug_result}"
    
    def _iterative_debug(self, failed_commands: List[Dict[str, Any]], max_iterations: int = 5) -> str:
        """Iteratively debug and fix command failures."""
        debug_agent = Agent('debug', cwd=self.cwd, user_input="")
        debug_agent.project_context = self.project_context.copy()
        debug_agent.conversation_history = self.conversation_history.copy()
        
        iteration = 0
        all_fixed = False
        
        print(f"Will iterate until all commands succeed (max {max_iterations} attempts)", file=sys.stderr)
        
        while iteration < max_iterations and not all_fixed:
            iteration += 1
            print(f"\n🔧 Debug iteration {iteration} (will stop when all commands succeed)", file=sys.stderr)
            
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
            
            # Check if any changes were made
            self.load_context()  # Reload to get latest file state
            files_after = set(self.project_context.keys())
            files_changed = files_after - files_before
            files_removed = files_before - files_after
            
            # Check if any file modifications were made
            has_changes = len(files_changed) > 0 or len(files_removed) > 0
            has_actions = any(keyword in debug_result for keyword in ["✓ Created", "✓ Edited", "✓ Deleted", "--- Created", "--- Edited", "--- Deleted"])
            
            if not has_changes and not has_actions:
                print(f"⚠️  WARNING: No changes detected in iteration {iteration}!", file=sys.stderr)
                print(f"   Debug agent did not create, edit, or delete any files.", file=sys.stderr)
                print(f"   This may indicate the agent needs more context or a different approach.", file=sys.stderr)
                # Still continue to next iteration, but warn the user
            
            if has_changes:
                print(f"✓ Changes detected: {len(files_changed)} file(s) added, {len(files_removed)} file(s) removed", file=sys.stderr)
                if files_changed:
                    for f in list(files_changed)[:5]:  # Show first 5
                        print(f"   + {f}", file=sys.stderr)
                if files_removed:
                    for f in list(files_removed)[:5]:  # Show first 5
                        print(f"   - {f}", file=sys.stderr)
            
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
                    print("Stopping debug loop - all commands now succeed.", file=sys.stderr)
                    break
            
            # Check if any changes were made
            self.load_context()  # Reload to get latest file state
            files_after = set(self.project_context.keys())
            files_changed = files_after - files_before
            files_removed = files_before - files_after
            
            # Check if any file modifications were made
            has_changes = len(files_changed) > 0 or len(files_removed) > 0
            has_actions = any(keyword in debug_result for keyword in ["✓ Created", "✓ Edited", "✓ Deleted", "--- Created", "--- Edited", "--- Deleted"])
            
            if not has_changes and not has_actions:
                print(f"⚠️  WARNING: No changes detected in iteration {iteration}!", file=sys.stderr)
                print(f"   Debug agent did not create, edit, or delete any files.", file=sys.stderr)
                print(f"   This may indicate the agent needs more context or a different approach.", file=sys.stderr)
                # Still continue to next iteration, but warn the user
            
            if has_changes:
                print(f"✓ Changes detected: {len(files_changed)} file(s) added, {len(files_removed)} file(s) removed", file=sys.stderr)
                if files_changed:
                    for f in list(files_changed)[:5]:  # Show first 5
                        print(f"   + {f}", file=sys.stderr)
                if files_removed:
                    for f in list(files_removed)[:5]:  # Show first 5
                        print(f"   - {f}", file=sys.stderr)
            
            # Update our context with debug agent's changes
            self.project_context.update(debug_agent.project_context)
            self.conversation_history.extend(debug_agent.conversation_history[-1:])  # Add last debug exchange
        
        if all_fixed:
            return f"✓ Debug complete: All issues resolved after {iteration} iteration(s)"
        else:
            print(f"\n⚠️  Reached maximum iterations ({max_iterations})", file=sys.stderr)
            return f"⚠️  Debug incomplete: Some issues may remain after {max_iterations} iteration(s). Manual intervention may be needed."
    
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
        
        # For design mode, filter out any non-.design file actions BEFORE execution
        if self.mode == 'design':
                filtered_actions = []
                rejected_actions = []
                for action in actions:
                    target = (action.get('target') or action.get('path') or 
                             action.get('file_path') or action.get('file') or '').strip()
                    action_type = action.get('type', '').lower()
                    
                    # Only allow .design files or message actions
                    if action_type == 'message':
                        filtered_actions.append(action)
                    elif target.endswith('.design'):
                        filtered_actions.append(action)
                    else:
                        rejected_actions.append(f"{action_type}: {target}")
                
                if rejected_actions:
                    print(f"\n⚠️  FILTERED OUT {len(rejected_actions)} non-design actions:", file=sys.stderr)
                    for rejected in rejected_actions:
                        print(f"   - {rejected}", file=sys.stderr)
                    print(f"   Design mode only works with .design files.\n", file=sys.stderr)
                
                if not filtered_actions:
                    return f"Error: All actions were filtered out. Design mode can only create/edit .design files.\nRejected actions: {', '.join(rejected_actions)}"
                
                actions = filtered_actions
            
        # For test mode, filter out any non-.test file actions BEFORE execution
        if self.mode == 'test':
            filtered_actions = []
            rejected_actions = []
            for action in actions:
                target = (action.get('target') or action.get('path') or 
                         action.get('file_path') or action.get('file') or '').strip()
                action_type = action.get('type', '').lower()
                
                # Only allow .test files or message actions
                if action_type == 'message':
                    filtered_actions.append(action)
                elif target.endswith('.test'):
                    filtered_actions.append(action)
                else:
                    rejected_actions.append(f"{action_type}: {target}")
            
            if rejected_actions:
                print(f"\n⚠️  FILTERED OUT {len(rejected_actions)} non-design actions:", file=sys.stderr)
                for rejected in rejected_actions:
                    print(f"   - {rejected}", file=sys.stderr)
                print(f"   Design mode only works with .design files.\n", file=sys.stderr)
            
            if not filtered_actions:
                return f"Error: All actions were filtered out. Design mode can only create/edit .design files.\nRejected actions: {', '.join(rejected_actions)}"
            
            actions = filtered_actions
        
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
        # Special handling for debug mode with command-like input
        if args.mode == 'debug' and user_input.strip():
            # Check if input looks like a command (not a question/description)
            # Commands typically don't start with question words and may contain shell operators
            command_indicators = [' ', '&&', '|', ';', '>', '<', '`']
            is_likely_command = any(indicator in user_input for indicator in command_indicators) or \
                               not any(user_input.strip().lower().startswith(q) for q in ['what', 'why', 'how', 'when', 'where', 'explain', 'analyze', 'help'])
            
            if is_likely_command and not user_input.strip().startswith('"') and not user_input.strip().startswith("'"):
                # Treat as a command to debug
                result = agent._debug_command(user_input.strip())
            else:
                # Treat as a regular debug prompt
                result = agent.process(user_input)
        else:
            # For non-debug modes, process normally
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

