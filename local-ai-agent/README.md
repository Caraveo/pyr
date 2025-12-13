# Local AI Agent Toolchain

A complete local AI development toolchain that runs fully on macOS Terminal. This toolchain provides five system-wide commands powered by local Ollama models for professional software development workflows.

## Overview

This toolchain installs five AI-powered commands that operate on your current working directory:

- **`code`** - Interactive coding agent for refactoring, writing, and modifying code
- **`design`** - Design-first agent that creates and evolves design documents
- **`craft`** - Execution-focused agent for building and implementing code
- **`debug`** - Diagnostic agent for finding and fixing bugs
- **`test`** - Testing agent for generating and running tests

## Core Principles

- ✅ **Fully local** - No cloud APIs, everything runs on your machine
- ✅ **Terminal-native** - Designed for macOS Terminal workflows
- ✅ **Ollama-powered** - Uses local Ollama models via subprocess
- ✅ **Context-aware** - Automatically loads project files, errors, and logs
- ✅ **Safe by default** - Creates backups before modifying files
- ✅ **Professional-grade** - Built for iterative software development

## Installation

### Prerequisites

1. **Ollama** - Install from [https://ollama.ai](https://ollama.ai)
2. **Python 3.7+** - Should be pre-installed on macOS
3. **Model** - Pull the recommended model:
   ```bash
   ollama pull qwen2.5-coder:14b
   ```

### Install the Toolchain

1. Navigate to the project directory:
   ```bash
   cd local-ai-agent
   ```

2. Run the installer:
   ```bash
   ./installer.sh
   ```

   The installer will:
   - Copy files to `~/.local-ai-agent/`
   - Create system-wide symlinks in `/usr/local/bin/`
   - Make all commands executable

3. Verify installation:
   ```bash
   which code design craft debug test
   ```

## Usage

### Command: `code`

Primary interactive AI coding agent. Launches an interactive REPL.

```bash
code
agent> refactor auth.py to use async/await
agent> add logging to all files in server/
agent> create a new API endpoint for user profiles
```

**Features:**
- Interactive REPL with `agent>` prompt
- Loads full project context recursively
- Skips: `.git`, `node_modules`, `dist`, `build`
- Skips files > 300KB
- Maintains conversation history
- Accepts natural language instructions

**Capabilities:**
- Read files
- Create files
- Modify files
- Delete files (with confirmation)
- Run shell commands
- Update multiple files in one request
- Generate diffs
- Apply edits safely with `.backup` files

### Command: `design`

Design-first AI agent that creates and evolves a living design document.

```bash
design "design a SwiftUI interface for user onboarding"
design "update architecture to support offline mode"
```

**Behavior:**
- Loads project context + existing design document
- Writes **ONLY** to `[project-name].design`
- Iterates on the design document instead of modifying source code
- Enhances prompts for future coding actions

**Design Document Includes:**
- Architecture overview
- Data models and schemas
- UI/UX descriptions
- API contracts and endpoints
- Component hierarchies
- Design decisions and tradeoffs
- Implementation phases

**Note:** This command does NOT edit code. It prepares structured design intent for `code` and `craft`.

### Command: `craft`

Execution-focused agent that builds, runs, and assembles code artifacts.

```bash
craft "implement the onboarding UI from the design doc"
craft "generate database schema and migrations"
```

**Behavior:**
- Executes code generation or build steps
- Can run compilers, package managers, scripts
- Uses design document + codebase as input
- Applies changes directly to files
- Suitable for scaffolding and implementation

### Command: `debug`

Error-focused diagnostic agent.

```bash
debug
debug "why is app crashing on launch?"
```

**Behavior:**
- Reads stack traces, logs, error output
- Can re-run failing commands
- Suggests fixes and optionally applies them
- Focuses on minimal, targeted edits

### Command: `test`

Testing and validation agent.

```bash
test
test "add unit tests for auth module"
```

**Behavior:**
- Generates tests
- Runs existing tests
- Analyzes failures
- Improves coverage
- Works with common frameworks (pytest, jest, swift test, etc.)

## Workflow

The commands are designed to work together in a professional development workflow:

```
design → code → craft → debug → test
```

1. **Design** - Create or update design documents
2. **Code** - Refactor and modify existing code
3. **Craft** - Implement new features and scaffolding
4. **Debug** - Fix errors and issues
5. **Test** - Generate and run tests

## Configuration

### Model Selection

Override the default model using the `LOCAL_AI_MODEL` environment variable:

```bash
export LOCAL_AI_MODEL="llama3.2:3b"
code
```

Default model: `qwen2.5-coder:14b`

### Working Directory

All commands operate on the current working directory. Change directories before running commands:

```bash
cd /path/to/your/project
code
```

## Safety Features

- **Automatic Backups** - Files are backed up with `.backup` extension before modification
- **Confirmation Prompts** - Destructive actions (like file deletion) require confirmation
- **Command Blocking** - Dangerous commands (like `rm -rf`) are blocked
- **Context Limits** - Large files (>300KB) are skipped to prevent context overflow

## Project Structure

```
local-ai-agent/
├── agent.py              # Shared agent runtime
├── installer.sh          # Installation script
├── README.md             # This file
├── prompts/
│   ├── code.txt          # Code agent prompt
│   ├── design.txt        # Design agent prompt
│   ├── craft.txt         # Craft agent prompt
│   ├── debug.txt         # Debug agent prompt
│   └── test.txt          # Test agent prompt
└── tools/
    ├── __init__.py
    ├── fs.py             # File system helpers
    ├── shell.py          # Shell execution helpers
    └── diff.py           # Diff generation
```

## Model Response Format

The AI model responds in JSON format:

```json
{
  "actions": [
    {
      "type": "edit|create|delete|run|message",
      "target": "file path or command",
      "content": "new content or command output"
    }
  ]
}
```

**Action Types:**
- `edit` - Modify an existing file (provide full content)
- `create` - Create a new file (provide full content)
- `delete` - Delete a file (with confirmation)
- `run` - Execute a shell command
- `message` - Send a message to the user

## Troubleshooting

### Ollama Not Found

```bash
# Check if Ollama is installed
ollama --version

# If not installed, download from https://ollama.ai
```

### Command Not Found

```bash
# Check if commands are in PATH
which code

# If not found, re-run installer
cd local-ai-agent
./installer.sh
```

### Permission Denied

The installer requires `sudo` to create symlinks in `/usr/local/bin/`. If you prefer not to use sudo, you can manually create symlinks or add `~/.local-ai-agent` to your PATH.

### Model Not Found

```bash
# Pull the recommended model
ollama pull qwen2.5-coder:14b

# Or use a different model
export LOCAL_AI_MODEL="your-model-name"
```

## Uninstallation

To remove the toolchain:

```bash
# Remove system-wide commands
sudo rm /usr/local/bin/{code,design,craft,debug,test}

# Remove installation directory
rm -rf ~/.local-ai-agent
```

## License

This project is provided as-is for local development use.

## Contributing

This is a local development tool. Feel free to modify and adapt it to your needs.

---

**Built for macOS Terminal • Powered by Ollama • Fully Local**

