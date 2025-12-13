#!/usr/bin/env python3
"""
Structure detection and loading utilities.
Detects project type and loads appropriate structure templates.
"""

import json
from pathlib import Path
from typing import Optional, Dict, Any, List


def load_structure(structure_name: str) -> Optional[Dict[str, Any]]:
    """Load a structure definition from JSON file."""
    structures_dir = Path(__file__).parent.parent / 'structures'
    structure_file = structures_dir / f"{structure_name}.json"
    
    if not structure_file.exists():
        return None
    
    try:
        with open(structure_file, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Error loading structure {structure_name}: {e}", file=__import__('sys').stderr)
        return None


def detect_structure(cwd: Path, user_input: str = "") -> Optional[Dict[str, Any]]:
    """
    Detect which structure to use based on:
    1. Existing files in the directory
    2. Keywords in user input
    3. Project name
    
    Returns the best matching structure definition.
    """
    structures_dir = Path(__file__).parent.parent / 'structures'
    
    if not structures_dir.exists():
        return None
    
    # Load all available structures
    available_structures = []
    for structure_file in structures_dir.glob("*.json"):
        structure_name = structure_file.stem
        structure = load_structure(structure_name)
        if structure:
            available_structures.append(structure)
    
    if not available_structures:
        return None
    
    # Score each structure based on detection criteria
    user_input_lower = user_input.lower()
    best_match = None
    best_score = 0
    
    for structure in available_structures:
        score = 0
        detection = structure.get('detection', {})
        
        # Check keywords in user input
        keywords = detection.get('keywords', [])
        for keyword in keywords:
            if keyword.lower() in user_input_lower:
                score += 10
        
        # Check for existing files
        files = detection.get('files', [])
        for file_pattern in files:
            # Simple pattern matching
            if '*' in file_pattern:
                pattern = file_pattern.replace('*', '')
                for existing_file in cwd.rglob('*'):
                    if pattern in existing_file.name:
                        score += 20
                        break
            else:
                if (cwd / file_pattern).exists():
                    score += 20
        
        # Check parent directory for files
        for file_pattern in files:
            if '*' not in file_pattern:
                if (cwd.parent / file_pattern).exists():
                    score += 10
        
        if score > best_score:
            best_score = score
            best_match = structure
    
    # If no strong match, use default based on keywords in input
    if best_score < 5:
        # Check for strong keyword matches
        for structure in available_structures:
            detection = structure.get('detection', {})
            keywords = detection.get('keywords', [])
            for keyword in keywords:
                if keyword.lower() in user_input_lower:
                    # Strong match for specific tech stack mentions
                    if any(kw in user_input_lower for kw in ['swift', 'swiftui', 'macos', 'ios']):
                        if 'swift' in structure.get('name', '').lower():
                            return structure
                    elif any(kw in user_input_lower for kw in ['javascript', 'node', 'npm', 'js']):
                        if 'javascript' in structure.get('name', '').lower() or 'node' in structure.get('name', '').lower():
                            return structure
                    elif any(kw in user_input_lower for kw in ['python', 'py']):
                        if 'python' in structure.get('name', '').lower():
                            return structure
    
    return best_match if best_score > 0 else None


def get_structure_prompt(structure: Dict[str, Any], project_name: str = "", project_description: str = "") -> str:
    """Generate a prompt section from a structure definition."""
    assumptions = structure.get('assumptions', {})
    prompt_template = structure.get('prompt_template', '')
    
    # Replace placeholders
    prompt = prompt_template.replace('{PROJECT_NAME}', project_name)
    prompt = prompt.replace('{PROJECT_DESCRIPTION}', project_description)
    
    # Add structure information
    structure_info = f"\n\nPROJECT STRUCTURE ASSUMPTIONS:\n"
    structure_info += f"Language: {assumptions.get('language', 'Unknown')}\n"
    
    if 'framework' in assumptions:
        structure_info += f"Framework: {assumptions.get('framework')}\n"
    if 'platform' in assumptions:
        structure_info += f"Platform: {assumptions.get('platform')}\n"
    
    structure_info += f"Package Manager: {assumptions.get('package_manager', 'None')}\n"
    structure_info += f"Build Command: {assumptions.get('build_command', 'None')}\n"
    structure_info += f"Run Command: {assumptions.get('run_command', 'None')}\n"
    
    # Add required files
    structure_def = assumptions.get('structure', {})
    if structure_def:
        structure_info += f"\nRequired Files:\n"
        for file_path, file_info in structure_def.items():
            if file_info.get('required', False):
                structure_info += f"  - {file_path}: {file_info.get('description', '')}\n"
    
    return prompt + structure_info


def extract_project_name(user_input: str, cwd: Path) -> str:
    """Extract or infer project name from user input or directory."""
    # Try to extract from user input (look for quoted names or "called X" patterns)
    import re
    
    # Look for "called X" or "named X"
    match = re.search(r'(?:called|named)\s+([A-Za-z][A-Za-z0-9_]*)', user_input, re.IGNORECASE)
    if match:
        return match.group(1)
    
    # Look for quoted project name
    match = re.search(r'["\']([A-Za-z][A-Za-z0-9_]*)["\']', user_input)
    if match:
        return match.group(1)
    
    # Use directory name as fallback
    return cwd.name

