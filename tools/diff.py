#!/usr/bin/env python3
"""
Diff generation utilities for the AI agent.
Helps visualize changes before applying them.
"""

import difflib
from typing import List, Optional


def generate_unified_diff(
    old_content: str,
    new_content: str,
    file_path: str,
    context_lines: int = 3
) -> str:
    """
    Generate a unified diff between old and new content.
    
    Args:
        old_content: Original file content
        new_content: New file content
        file_path: Path to the file (for diff header)
        context_lines: Number of context lines to show
    
    Returns:
        Unified diff string
    """
    old_lines = old_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)
    
    diff = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile=file_path,
        tofile=file_path,
        lineterm='',
        n=context_lines
    )
    
    return ''.join(diff)


def generate_inline_diff(
    old_content: str,
    new_content: str
) -> str:
    """
    Generate an inline diff showing changes character by character.
    Useful for small changes.
    """
    old_lines = old_content.splitlines()
    new_lines = new_content.splitlines()
    
    diff_lines = []
    
    for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(
        None, old_lines, new_lines
    ).get_opcodes():
        if tag == 'equal':
            diff_lines.extend(old_lines[i1:i2])
        elif tag == 'delete':
            for line in old_lines[i1:i2]:
                diff_lines.append(f"- {line}")
        elif tag == 'insert':
            for line in new_lines[j1:j2]:
                diff_lines.append(f"+ {line}")
        elif tag == 'replace':
            for line in old_lines[i1:i2]:
                diff_lines.append(f"- {line}")
            for line in new_lines[j1:j2]:
                diff_lines.append(f"+ {line}")
    
    return '\n'.join(diff_lines)


def format_diff_summary(old_content: str, new_content: str) -> str:
    """
    Generate a summary of changes between old and new content.
    """
    old_lines = old_content.splitlines()
    new_lines = new_content.splitlines()
    
    matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
    
    added = sum(1 for tag, _, _, _, _ in matcher.get_opcodes() if tag == 'insert')
    removed = sum(1 for tag, _, _, _, _ in matcher.get_opcodes() if tag == 'delete')
    modified = sum(1 for tag, _, _, _, _ in matcher.get_opcodes() if tag == 'replace')
    
    summary = f"Changes: {added} lines added, {removed} lines removed"
    if modified > 0:
        summary += f", {modified} sections modified"
    
    return summary

