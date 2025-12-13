#!/usr/bin/env python3
"""
Progress tracking and todo list utilities for the AI agent.
"""

import sys
from typing import List, Dict, Optional
from datetime import datetime


class ProgressTracker:
    """Tracks progress through a task with subtasks."""
    
    def __init__(self, total_tasks: int = 0, task_name: str = "Task"):
        self.total_tasks = total_tasks
        self.completed_tasks = 0
        self.task_name = task_name
        self.subtasks: List[Dict[str, any]] = []
        self.start_time = datetime.now()
    
    def add_subtask(self, description: str, status: str = "pending"):
        """Add a subtask to track."""
        self.subtasks.append({
            'description': description,
            'status': status,  # pending, in_progress, completed, failed
            'start_time': None,
            'end_time': None
        })
        self.total_tasks = len(self.subtasks)
    
    def start_subtask(self, index: int):
        """Mark a subtask as in progress."""
        if 0 <= index < len(self.subtasks):
            self.subtasks[index]['status'] = 'in_progress'
            self.subtasks[index]['start_time'] = datetime.now()
            self._update_display()
    
    def complete_subtask(self, index: int):
        """Mark a subtask as completed."""
        if 0 <= index < len(self.subtasks):
            self.subtasks[index]['status'] = 'completed'
            self.subtasks[index]['end_time'] = datetime.now()
            self.completed_tasks += 1
            self._update_display()
    
    def fail_subtask(self, index: int):
        """Mark a subtask as failed."""
        if 0 <= index < len(self.subtasks):
            self.subtasks[index]['status'] = 'failed'
            self.subtasks[index]['end_time'] = datetime.now()
            self._update_display()
    
    def _update_display(self):
        """Update the progress display."""
        if self.total_tasks == 0:
            return
        
        percentage = (self.completed_tasks / self.total_tasks) * 100
        bar_length = 40
        filled = int(bar_length * self.completed_tasks / self.total_tasks)
        bar = '█' * filled + '░' * (bar_length - filled)
        
        # Clear line and print progress
        print(f"\r[{bar}] {percentage:.1f}% ({self.completed_tasks}/{self.total_tasks}) {self.task_name}", 
              end='', file=sys.stderr, flush=True)
    
    def finish(self):
        """Finish tracking and print final status."""
        print(file=sys.stderr)  # New line
        elapsed = (datetime.now() - self.start_time).total_seconds()
        print(f"✓ Completed {self.completed_tasks}/{self.total_tasks} tasks in {elapsed:.1f}s", file=sys.stderr)


def break_down_tasks(content: str, max_chunk_size: int = 5000) -> List[str]:
    """
    Break down large content into smaller, manageable tasks.
    
    For design documents, breaks by sections.
    For code, breaks by files or logical units.
    """
    tasks = []
    
    # If content is small, return as single task
    if len(content) < max_chunk_size:
        return [content]
    
    # Try to break by markdown headers (for design documents)
    import re
    header_pattern = r'^#{1,3}\s+.+$'
    lines = content.split('\n')
    current_section = []
    current_size = 0
    
    for line in lines:
        if re.match(header_pattern, line):
            # Found a header - save current section if it has content
            if current_section and current_size > 0:
                tasks.append('\n'.join(current_section))
                current_section = []
                current_size = 0
            current_section.append(line)
            current_size += len(line)
        else:
            current_section.append(line)
            current_size += len(line)
            
            # If section gets too large, split it
            if current_size > max_chunk_size:
                tasks.append('\n'.join(current_section))
                current_section = []
                current_size = 0
    
    # Add remaining content
    if current_section:
        tasks.append('\n'.join(current_section))
    
    # If no headers found or still too large, break by lines
    if not tasks or any(len(task) > max_chunk_size for task in tasks):
        tasks = []
        chunk = []
        chunk_size = 0
        
        for line in lines:
            chunk.append(line)
            chunk_size += len(line)
            
            if chunk_size > max_chunk_size:
                tasks.append('\n'.join(chunk))
                chunk = []
                chunk_size = 0
        
        if chunk:
            tasks.append('\n'.join(chunk))
    
    return tasks if tasks else [content]


def generate_todo_list(actions: List[Dict], design_content: str = "") -> List[str]:
    """
    Generate a todo list from actions and design content.
    """
    todos = []
    
    # Extract todos from design document if available
    if design_content:
        import re
        # Look for todo lists, task lists, or numbered lists
        todo_patterns = [
            r'- \[ \] (.+)',  # Markdown todo
            r'- \[x\] (.+)',  # Completed todo
            r'\d+\.\s+(.+)',  # Numbered list
            r'##?\s+Tasks?:(.+?)(?=##|$)',  # Tasks section
        ]
        
        for pattern in todo_patterns:
            matches = re.findall(pattern, design_content, re.IGNORECASE | re.MULTILINE)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0] if match else ""
                if match.strip():
                    todos.append(match.strip())
    
    # Generate todos from actions
    for i, action in enumerate(actions, 1):
        action_type = action.get('type', '').lower()
        target = action.get('target', '').strip()
        
        if not target:
            # Try alternative field names
            target = action.get('file_path', '').strip() or action.get('file', '').strip()
        
        if action_type == 'create':
            todos.append(f"Create {target}" if target else f"Create file (target missing)")
        elif action_type == 'edit':
            todos.append(f"Edit {target}" if target else f"Edit file (target missing)")
        elif action_type == 'delete':
            todos.append(f"Delete {target}" if target else f"Delete file (target missing)")
        elif action_type == 'run':
            todos.append(f"Run: {target}" if target else f"Run command (target missing)")
    
    return todos

