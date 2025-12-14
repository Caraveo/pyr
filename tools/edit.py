#!/usr/bin/env python3
"""
File editing utilities using shell tools for different tasks.
Organized by task type for optimal tool selection.
"""

import subprocess
import shlex
import shutil
import tempfile
from pathlib import Path
from typing import Optional, Tuple, List


def append_line(file_path: Path, line: str) -> Tuple[bool, str]:
    """
    Append one line to a file using echo >>.
    
    Args:
        file_path: Path to the file
        line: Line to append (without newline - will be added automatically)
    
    Returns:
        (success, error_message)
    """
    file_path = Path(file_path).resolve()
    
    # Ensure parent directory exists
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        # Use echo with >> to append one line
        # Escape the line properly for shell
        escaped_line = shlex.quote(line)
        command = f'echo {escaped_line} >> {shlex.quote(str(file_path))}'
        
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            return (True, "")
        else:
            return (False, result.stderr or "Unknown error")
    
    except subprocess.TimeoutExpired:
        return (False, "Command timed out")
    except Exception as e:
        return (False, str(e))


def append_block(file_path: Path, content: str) -> Tuple[bool, str]:
    """
    Append a block of text to a file using cat <<EOF.
    
    Args:
        file_path: Path to the file
        content: Block of text to append (can be multiline)
    
    Returns:
        (success, error_message)
    """
    file_path = Path(file_path).resolve()
    
    # Ensure parent directory exists
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        # Use heredoc to append block
        # Use a unique delimiter to avoid conflicts
        delimiter = "EOF_APPEND_BLOCK"
        
        # Create the heredoc command
        command = f'cat >> {shlex.quote(str(file_path))} << {delimiter}\n{content}\n{delimiter}'
        
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            return (True, "")
        else:
            return (False, result.stderr or "Unknown error")
    
    except subprocess.TimeoutExpired:
        return (False, "Command timed out")
    except Exception as e:
        return (False, str(e))


def insert_at_line(file_path: Path, line_number: int, content: str) -> Tuple[bool, str]:
    """
    Insert content at a specific line number using sed.
    
    Args:
        file_path: Path to the file
        line_number: Line number to insert at (1-indexed)
        content: Content to insert (can be multiline)
    
    Returns:
        (success, error_message)
    """
    file_path = Path(file_path).resolve()
    
    if not file_path.exists():
        return (False, f"File {file_path} does not exist")
    
    try:
        # Read existing content
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Insert content at specified line
        # line_number is 1-indexed, so subtract 1 for 0-indexed list
        insert_pos = line_number - 1
        
        # Split content into lines
        content_lines = content.split('\n')
        
        # Insert the content
        if insert_pos < 0:
            insert_pos = 0
        elif insert_pos > len(lines):
            insert_pos = len(lines)
        
        # Add newlines to content lines (except last if it's empty)
        formatted_lines = []
        for i, line in enumerate(content_lines):
            if i < len(content_lines) - 1 or line:  # Add newline unless it's the last empty line
                formatted_lines.append(line + '\n')
            else:
                formatted_lines.append(line)
        
        # Insert the lines
        lines[insert_pos:insert_pos] = formatted_lines
        
        # Write back using temporary file for atomic operation
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.tmp', dir=file_path.parent, encoding='utf-8') as tmp:
            tmp.writelines(lines)
            tmp_path = tmp.name
        
        # Move temp file to final location (atomic operation)
        shutil.move(tmp_path, file_path)
        
        return (True, "")
    
    except Exception as e:
        return (False, str(e))


def replace_line(file_path: Path, line_number: int, new_content: str) -> Tuple[bool, str]:
    """
    Replace a specific line using sed.
    
    Args:
        file_path: Path to the file
        line_number: Line number to replace (1-indexed)
        new_content: New content for the line
    
    Returns:
        (success, error_message)
    """
    file_path = Path(file_path).resolve()
    
    if not file_path.exists():
        return (False, f"File {file_path} does not exist")
    
    try:
        # Read existing content
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Replace the line (line_number is 1-indexed)
        if line_number < 1 or line_number > len(lines):
            return (False, f"Line number {line_number} is out of range (file has {len(lines)} lines)")
        
        # Replace the line (keep newline if original had one)
        lines[line_number - 1] = new_content + ('\n' if not new_content.endswith('\n') and (line_number == len(lines) or lines[line_number - 1].endswith('\n')) else '')
        
        # Write back
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
        
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            return (True, "")
        else:
            return (False, result.stderr or "Unknown error")
    
    except subprocess.TimeoutExpired:
        return (False, "Command timed out")
    except Exception as e:
        return (False, str(e))


def delete_line(file_path: Path, line_number: int) -> Tuple[bool, str]:
    """
    Delete a specific line using sed.
    
    Args:
        file_path: Path to the file
        line_number: Line number to delete (1-indexed)
    
    Returns:
        (success, error_message)
    """
    file_path = Path(file_path).resolve()
    
    if not file_path.exists():
        return (False, f"File {file_path} does not exist")
    
    try:
        # Read existing content
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Check if line number is valid
        if line_number < 1 or line_number > len(lines):
            return (False, f"Line number {line_number} is out of range (file has {len(lines)} lines)")
        
        # Delete the line (line_number is 1-indexed)
        del lines[line_number - 1]
        
        # Write back
        with open(file_path, 'w', encoding='utf-8') as f:
            f.writelines(lines)
    
    except subprocess.TimeoutExpired:
        return (False, "Command timed out")
    except Exception as e:
        return (False, str(e))


def get_best_tool(task: str) -> str:
    """
    Determine the best tool for a given task.
    
    Args:
        task: Description of the task (e.g., "append one line", "append block", "insert at line")
    
    Returns:
        Tool name: "echo", "cat", "sed", or "write" (fallback)
    """
    task_lower = task.lower()
    
    if "append" in task_lower and ("one line" in task_lower or "single line" in task_lower):
        return "echo"
    elif "append" in task_lower and ("block" in task_lower or "multiple" in task_lower):
        return "cat"
    elif "insert" in task_lower and "line" in task_lower:
        return "sed"
    elif "replace" in task_lower and "line" in task_lower:
        return "sed"
    elif "delete" in task_lower and "line" in task_lower:
        return "sed"
    else:
        return "write"  # Fallback to full file write

