# Tool Organization System

This document describes how file editing tools are organized by task type for optimal performance.

## Tool Selection Matrix

| Task | Best Tool | Function | Use Case |
|------|-----------|----------|----------|
| Append one line | `echo >>` | `append_line()` | Adding a single line to a file |
| Append block | `cat <<EOF` | `append_block()` | Adding multiple lines or a block of text |
| Insert at line | `sed` | `insert_at_line()` | Inserting content at a specific line number |
| Replace line | `sed` | `replace_line()` | Replacing a specific line |
| Delete line | `sed` | `delete_line()` | Removing a specific line |
| Full file write | `write_file()` | `write_file()` | Creating new files or complete rewrites |

## Tool Details

### `append_line(file_path, line)`
- **Tool**: `echo >>`
- **Best for**: Adding a single line to the end of a file
- **Example**: Appending a new import statement, adding a configuration value
- **Advantages**: Fast, simple, atomic operation

### `append_block(file_path, content)`
- **Tool**: `cat <<EOF` (heredoc)
- **Best for**: Adding multiple lines or a block of text
- **Example**: Adding a new function, appending documentation, adding a configuration section
- **Advantages**: Handles multiline content, preserves formatting

### `insert_at_line(file_path, line_number, content)`
- **Tool**: `sed` (with Python fallback for complex cases)
- **Best for**: Inserting content at a specific position
- **Example**: Adding a function in the middle of a file, inserting imports at the top
- **Advantages**: Precise positioning, maintains file structure

### `replace_line(file_path, line_number, new_content)`
- **Tool**: `sed`
- **Best for**: Modifying a specific line
- **Example**: Updating a variable value, fixing a typo on one line
- **Advantages**: Minimal change, fast operation

### `delete_line(file_path, line_number)`
- **Tool**: `sed`
- **Best for**: Removing a specific line
- **Example**: Removing an unused import, deleting a deprecated function call
- **Advantages**: Precise deletion, maintains file integrity

## Automatic Tool Selection

The `get_best_tool(task)` function automatically selects the best tool based on task description:

```python
from tools.edit import get_best_tool

tool = get_best_tool("append one line")  # Returns "echo"
tool = get_best_tool("append block")     # Returns "cat"
tool = get_best_tool("insert at line 5") # Returns "sed"
```

## When to Use Each Tool

### Use `append_line()` when:
- Adding a single line
- The line is simple (no special characters that need escaping)
- You want the fastest operation

### Use `append_block()` when:
- Adding multiple lines
- The content is a complete block (function, class, section)
- You want to preserve formatting

### Use `insert_at_line()` when:
- You need to insert at a specific position
- The insertion point is known (line number)
- You want to maintain file structure

### Use `replace_line()` when:
- Modifying an existing line
- You know the exact line number
- The change is small and localized

### Use `delete_line()` when:
- Removing a specific line
- You know the exact line number
- You want minimal file modification

### Use `write_file()` (fallback) when:
- Creating a new file
- Making extensive changes across the file
- The above tools don't fit the use case

## Implementation Notes

- All tools create backups automatically when modifying existing files
- Tools handle encoding (UTF-8) and line endings properly
- Error handling is consistent across all tools
- Tools are shell-based for performance and compatibility

