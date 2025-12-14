#!/usr/bin/env python3
"""
File system helper utilities for the AI agent.
Handles file operations, context loading, and backups.
"""

import os
import shutil
from pathlib import Path
from typing import List, Set, Optional


# Directories to skip when loading context
SKIP_DIRS = {'.git', 'node_modules', 'dist', 'build', '__pycache__', '.pytest_cache', '.venv', 'venv', 'env'}

# Maximum file size to load (300KB)
MAX_FILE_SIZE = 300 * 1024


def should_skip_path(path: Path) -> bool:
    """Check if a path should be skipped."""
    parts = path.parts
    return any(part in SKIP_DIRS for part in parts)


def load_project_context(root_dir: Path) -> dict:
    """
    Recursively load project files for context.
    Returns a dictionary mapping file paths to their contents.
    """
    context = {}
    root_dir = Path(root_dir).resolve()
    
    if not root_dir.exists() or not root_dir.is_dir():
        return context
    
    for root, dirs, files in os.walk(root_dir):
        # Filter out skipped directories
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        
        root_path = Path(root)
        if should_skip_path(root_path):
            continue
        
        for file in files:
            file_path = root_path / file
            
            if should_skip_path(file_path):
                continue
            
            # Skip hidden files (except .design and .test files)
            if file.startswith('.') and not (file.endswith('.design') or file.endswith('.test')):
                continue
            
            # Check file size
            try:
                if file_path.stat().st_size > MAX_FILE_SIZE:
                    continue
            except (OSError, PermissionError):
                continue
            
            # Read file content
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    # Store relative path
                    rel_path = file_path.relative_to(root_dir)
                    context[str(rel_path)] = content
            except (UnicodeDecodeError, PermissionError, OSError):
                # Skip binary files or files we can't read
                continue
    
    return context


def backup_file(file_path: Path) -> Optional[Path]:
    """
    Create a backup of a file before modification.
    Returns the backup path if successful, None otherwise.
    """
    file_path = Path(file_path).resolve()
    
    if not file_path.exists():
        return None
    
    backup_path = file_path.with_suffix(file_path.suffix + '.backup')
    
    try:
        shutil.copy2(file_path, backup_path)
        return backup_path
    except (OSError, PermissionError) as e:
        print(f"Warning: Could not create backup: {e}")
        return None


def read_file(file_path: Path) -> Optional[str]:
    """Read a file and return its content."""
    file_path = Path(file_path).resolve()
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return f.read()
    except (FileNotFoundError, PermissionError, UnicodeDecodeError) as e:
        print(f"Error reading file {file_path}: {e}")
        return None


def write_file(file_path: Path, content: str, create_backup: bool = True) -> bool:
    """
    Write content to a file, optionally creating a backup first.
    Returns True if successful, False otherwise.
    """
    file_path = Path(file_path).resolve()
    
    # Create backup if file exists and backup requested
    if file_path.exists() and create_backup:
        backup_path = backup_file(file_path)
        if backup_path:
            print(f"Backup created: {backup_path}")
    
    # Ensure parent directory exists
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    except (OSError, PermissionError) as e:
        print(f"Error writing file {file_path}: {e}")
        return False


def delete_file(file_path: Path, create_backup: bool = True) -> bool:
    """
    Delete a file, optionally creating a backup first.
    Returns True if successful, False otherwise.
    """
    file_path = Path(file_path).resolve()
    
    if not file_path.exists():
        return False
    
    # Create backup if requested
    if create_backup:
        backup_path = backup_file(file_path)
        if backup_path:
            print(f"Backup created: {backup_path}")
    
    try:
        file_path.unlink()
        return True
    except (OSError, PermissionError) as e:
        print(f"Error deleting file {file_path}: {e}")
        return False


def find_design_file(root_dir: Path) -> Optional[Path]:
    """Find the design file for the project."""
    root_dir = Path(root_dir).resolve()
    project_name = root_dir.name
    
    # Look for [project-name].design
    design_file = root_dir / f"{project_name}.design"
    
    if design_file.exists():
        return design_file
    
    # Also check for .design files
    for design_file in root_dir.glob("*.design"):
        return design_file
    
    return None


def find_all_design_files(root_dir: Path) -> List[Path]:
    """Find all .design files in the root directory."""
    root_dir = Path(root_dir).resolve()
    design_files = list(root_dir.glob("*.design"))
    return sorted(design_files)


def find_test_files(root_dir: Path) -> List[Path]:
    """
    Find test files in common test locations.
    Looks for:
    - test/[test-name]/ directories
    - Tests/ directory (Swift)
    - tests/ directory (Python, Node.js)
    - *_test.py, *.test.swift, *.spec.js files
    """
    root_dir = Path(root_dir).resolve()
    test_files = []
    
    # Common test directory patterns
    test_dirs = [
        root_dir / 'test',
        root_dir / 'tests',
        root_dir / 'Tests',  # Swift
        root_dir / '__tests__',  # JavaScript
    ]
    
    # Look for test directories
    for test_dir in test_dirs:
        if test_dir.exists() and test_dir.is_dir():
            # Find all test files in subdirectories
            for test_file in test_dir.rglob('*'):
                if test_file.is_file():
                    # Check if it's a test file by extension or name
                    if (test_file.suffix in ['.py', '.swift', '.js', '.ts', '.java', '.go'] or
                        'test' in test_file.name.lower() or
                        'spec' in test_file.name.lower()):
                        test_files.append(test_file)
    
    # Also look for test files at root level
    test_patterns = [
        '*_test.py',
        '*Test.swift',
        '*.test.swift',
        '*.spec.js',
        '*.spec.ts',
        '*_test.go',
        '*Test.java',
    ]
    
    for pattern in test_patterns:
        test_files.extend(root_dir.glob(pattern))
    
    # Look for test/[test-name]/ pattern
    test_dir = root_dir / 'test'
    if test_dir.exists():
        for test_subdir in test_dir.iterdir():
            if test_subdir.is_dir():
                # Find test files in this subdirectory
                for test_file in test_subdir.rglob('*'):
                    if test_file.is_file() and test_file.suffix in ['.py', '.swift', '.js', '.ts', '.java', '.go']:
                        test_files.append(test_file)
    
    return sorted(set(test_files))  # Remove duplicates and sort
