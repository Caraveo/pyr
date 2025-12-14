#!/usr/bin/env python3
"""
Syntax validation using Tree-sitter for multiple programming languages.
Validates code syntax before writing files to ensure they're ready to run.
"""

import sys
from pathlib import Path
from typing import Optional, Tuple, Dict, Any

# Language mapping: file extension -> tree-sitter language name
LANGUAGE_MAP = {
    '.py': 'python',
    '.swift': 'swift',
    '.js': 'javascript',
    '.jsx': 'javascript',
    '.ts': 'typescript',
    '.tsx': 'typescript',
    '.java': 'java',
    '.c': 'c',
    '.cpp': 'cpp',
    '.cc': 'cpp',
    '.cxx': 'cpp',
    '.h': 'c',
    '.hpp': 'cpp',
    '.rs': 'rust',
    '.go': 'go',
    '.rb': 'ruby',
    '.php': 'php',
    '.sh': 'bash',
    '.bash': 'bash',
    '.zsh': 'bash',
    '.yaml': 'yaml',
    '.yml': 'yaml',
    '.json': 'json',
    '.toml': 'toml',
    '.xml': 'xml',
    '.html': 'html',
    '.css': 'css',
    '.scss': 'scss',
    '.sql': 'sql',
    '.lua': 'lua',
    '.r': 'r',
    '.m': 'objective_c',  # Objective-C
    '.mm': 'objective_cpp',  # Objective-C++
    '.kt': 'kotlin',
    '.scala': 'scala',
    '.dart': 'dart',
    '.vue': 'vue',
    '.svelte': 'svelte',
}

# Optional languages that may not be installed
OPTIONAL_LANGUAGES = {
    'swift', 'rust', 'go', 'ruby', 'php', 'kotlin', 'scala', 'dart', 
    'vue', 'svelte', 'objective_c', 'objective_cpp'
}


def detect_language(file_path: Path) -> Optional[str]:
    """
    Detect the programming language from file extension.
    
    Args:
        file_path: Path to the file
        
    Returns:
        Language name for tree-sitter, or None if not supported
    """
    suffix = file_path.suffix.lower()
    return LANGUAGE_MAP.get(suffix)


def validate_syntax(content: str, language: str) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    """
    Validate syntax using tree-sitter.
    
    Args:
        content: Code content to validate
        language: Language name (e.g., 'python', 'javascript')
        
    Returns:
        (is_valid, error_message, error_details)
        - is_valid: True if syntax is valid
        - error_message: Human-readable error message if invalid
        - error_details: Dict with line, column, and error type if invalid
    """
    try:
        import tree_sitter
        from tree_sitter import Language, Parser
    except ImportError:
        # Tree-sitter not installed - skip validation
        return (True, None, None)
    
    # Try to load the language parser
    try:
        lang_module = _load_language_parser(language)
        if lang_module is None:
            # Language parser not available - skip validation
            return (True, None, None)
        
        parser = Parser()
        parser.set_language(lang_module)
        
        # Parse the content
        tree = parser.parse(bytes(content, 'utf8'))
        
        # Check for syntax errors
        root_node = tree.root_node
        
        # If there are errors, tree-sitter will have an ERROR node
        if root_node.has_error:
            # Find the first error
            error_node = _find_first_error(root_node)
            if error_node:
                start_line = error_node.start_point[0] + 1
                start_col = error_node.start_point[1] + 1
                end_line = error_node.end_point[0] + 1
                end_col = error_node.end_point[1] + 1
                
                # Extract surrounding context
                lines = content.split('\n')
                error_line = lines[start_line - 1] if start_line <= len(lines) else ""
                
                error_msg = (
                    f"Syntax error at line {start_line}, column {start_col}: "
                    f"Unexpected {error_node.type}"
                )
                
                error_details = {
                    'line': start_line,
                    'column': start_col,
                    'end_line': end_line,
                    'end_column': end_col,
                    'type': error_node.type,
                    'error_line': error_line.strip()
                }
                
                return (False, error_msg, error_details)
        
        # Syntax is valid
        return (True, None, None)
        
    except Exception as e:
        # If validation fails for any reason, log but don't block
        # (better to allow the file to be written than to block on validation errors)
        print(f"Warning: Syntax validation failed for {language}: {e}", file=sys.stderr)
        return (True, None, None)


def _load_language_parser(language: str) -> Optional[Any]:
    """
    Load a tree-sitter language parser.
    
    Args:
        language: Language name
        
    Returns:
        Language parser object, or None if not available
    """
    try:
        # Try to import the language-specific parser
        # Common pattern: tree_sitter_{language}
        module_name = f"tree_sitter_{language}"
        
        try:
            lang_module = __import__(module_name)
            # Get the Language class from the module
            if hasattr(lang_module, 'language'):
                return lang_module.language
            elif hasattr(lang_module, 'Language'):
                return lang_module.Language
            else:
                # Try to find Language in submodules
                for attr_name in dir(lang_module):
                    attr = getattr(lang_module, attr_name)
                    if hasattr(attr, 'language'):
                        return attr.language
        except ImportError:
            # Try alternative import patterns
            if language == 'python':
                try:
                    import tree_sitter_python as ts_python
                    return ts_python.language()
                except ImportError:
                    pass
            elif language == 'javascript':
                try:
                    import tree_sitter_javascript as ts_js
                    return ts_js.language()
                except ImportError:
                    pass
            elif language == 'typescript':
                try:
                    import tree_sitter_typescript as ts_ts
                    # TypeScript parser has both tsx and typescript
                    if hasattr(ts_ts, 'language_typescript'):
                        return ts_ts.language_typescript()
                    elif hasattr(ts_ts, 'language'):
                        return ts_ts.language()
                except ImportError:
                    pass
            elif language == 'swift':
                try:
                    import tree_sitter_swift as ts_swift
                    return ts_swift.language()
                except ImportError:
                    pass
            elif language == 'rust':
                try:
                    import tree_sitter_rust as ts_rust
                    return ts_rust.language()
                except ImportError:
                    pass
            elif language == 'go':
                try:
                    import tree_sitter_go as ts_go
                    return ts_go.language()
                except ImportError:
                    pass
            elif language == 'java':
                try:
                    import tree_sitter_java as ts_java
                    return ts_java.language()
                except ImportError:
                    pass
            elif language == 'cpp':
                try:
                    import tree_sitter_cpp as ts_cpp
                    return ts_cpp.language()
                except ImportError:
                    pass
            elif language == 'c':
                try:
                    import tree_sitter_c as ts_c
                    return ts_c.language()
                except ImportError:
                    pass
            elif language == 'ruby':
                try:
                    import tree_sitter_ruby as ts_ruby
                    return ts_ruby.language()
                except ImportError:
                    pass
            elif language == 'php':
                try:
                    import tree_sitter_php as ts_php
                    return ts_php.language()
                except ImportError:
                    pass
            elif language == 'bash':
                try:
                    import tree_sitter_bash as ts_bash
                    return ts_bash.language()
                except ImportError:
                    pass
            elif language == 'yaml':
                try:
                    import tree_sitter_yaml as ts_yaml
                    return ts_yaml.language()
                except ImportError:
                    pass
            elif language == 'json':
                try:
                    import tree_sitter_json as ts_json
                    return ts_json.language()
                except ImportError:
                    pass
            elif language == 'html':
                try:
                    import tree_sitter_html as ts_html
                    return ts_html.language()
                except ImportError:
                    pass
            elif language == 'css':
                try:
                    import tree_sitter_css as ts_css
                    return ts_css.language()
                except ImportError:
                    pass
            elif language == 'sql':
                try:
                    import tree_sitter_sql as ts_sql
                    return ts_sql.language()
                except ImportError:
                    pass
            elif language == 'lua':
                try:
                    import tree_sitter_lua as ts_lua
                    return ts_lua.language()
                except ImportError:
                    pass
            elif language == 'r':
                try:
                    import tree_sitter_r as ts_r
                    return ts_r.language()
                except ImportError:
                    pass
            elif language == 'kotlin':
                try:
                    import tree_sitter_kotlin as ts_kotlin
                    return ts_kotlin.language()
                except ImportError:
                    pass
            elif language == 'toml':
                try:
                    import tree_sitter_toml as ts_toml
                    return ts_toml.language()
                except ImportError:
                    pass
            elif language == 'xml':
                try:
                    import tree_sitter_xml as ts_xml
                    return ts_xml.language()
                except ImportError:
                    pass
            
            # Language parser not installed
            if language not in OPTIONAL_LANGUAGES:
                print(f"Warning: tree-sitter parser for {language} not found. Install with: pip3 install tree-sitter-{language}", file=sys.stderr)
            return None
            
    except Exception as e:
        print(f"Warning: Failed to load tree-sitter parser for {language}: {e}", file=sys.stderr)
        return None


def _find_first_error(node: Any) -> Optional[Any]:
    """
    Recursively find the first ERROR node in the syntax tree.
    
    Args:
        node: Tree-sitter node
        
    Returns:
        First ERROR node found, or None
    """
    if node.type == 'ERROR':
        return node
    
    for child in node.children:
        error = _find_first_error(child)
        if error:
            return error
    
    return None


def validate_file_syntax(file_path: Path, content: str) -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    """
    Validate syntax for a file based on its extension.
    
    Args:
        file_path: Path to the file
        content: File content to validate
        
    Returns:
        (is_valid, error_message, error_details)
    """
    language = detect_language(file_path)
    
    if language is None:
        # File type not supported for validation - allow it
        return (True, None, None)
    
    return validate_syntax(content, language)

