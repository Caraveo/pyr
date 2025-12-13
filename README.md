# Pyr

## *This is not the End of Prometheus.*

**Prometheus!** is an open AI creation tool built on a single idea:

> **Fire belongs to everyone.**

**Pyr** is the core engine — a Promethean forge that lets you **run AI models, write code, and build systems without price, permission, or gates**. No subscriptions. No usage tolls. No divine intermediaries.

This is creation **as it was meant to be**.

---

## 🔥 What Is Pyr?

**Pyr** is an AI-powered creation environment designed to feel less like a product and more like a **forge**.

It allows you to:

* Run **AI models locally or freely**
* Generate, modify, and reason through **code**
* Shape logic the way matter is shaped — **with heat and intent**
* Build without limits imposed by cost, platforms, or closed systems

Pyr treats **code as clay** — formed from mud and water, hardened by fire.

---

## ⚒️ Why Prometheus?

Prometheus did not ask permission.
He **acted with foresight**.

He defied Zeus not for power, but for **progress** — believing humanity deserved the tools to shape its own future.

**Prometheus!** carries that defiance forward.

This project exists because:

* Innovation should not be **metered**
* Intelligence should not be **rented**
* Creation should not require **wealth**
* Progress should not be locked behind gods, corporations, or kings

Pyr is a **tool of foresight**.
A **weapon against stagnation**.
A forge built for those who refuse to wait.

---

## 🧠 What You Can Do With Prometheus!

* Run and experiment with **AI models without paywalls**
* Use AI as a **co-creator**, not a service
* Build software, simulations, worlds, and tools
* Prototype ideas at the speed of thought
* Learn, explore, and invent **without fear of cost**

This is AI **as infrastructure**, not a product.

---

## ⚔️ A Tool of Creation — and War

Pyr is not violent — but it **is confrontational**.

It stands against:

* Closed ecosystems
* Artificial scarcity
* Subscription-locked intelligence
* Innovation throttled by profit

Creation is the battlefield.
Stagnation is the enemy.

---

## 🌍 This Is Not the End of Prometheus

Prometheus was chained for giving humanity fire.

But fire spreads.

**Prometheus!** is not the end of that myth —
it is the **continuation**.

The forge is lit again.
The hammer is raised.
The fire is yours.

---

## 🚀 Get Started

> **Take the fire. Build without limits.**

### Installation

1. **Install Ollama** - Download from [https://ollama.ai](https://ollama.ai)

2. **Pull the recommended model:**
   ```bash
   ollama pull qwen2.5-coder:14b
   ```

3. **Install Pyr:**
   ```bash
   cd local-ai-agent
   ./installer.sh
   ```

4. **Start using the commands:**
   ```bash
   code                    # Interactive coding agent
   design "your request"   # Design document agent
   craft "your request"    # Implementation agent
   debug                   # Debugging agent
   test                    # Testing agent
   ```

### Commands

- **`code`** - Interactive AI coding agent with REPL
- **`design`** - Design-first agent for architecture and planning
- **`craft`** - Execution-focused agent for implementation
- **`debug`** - Diagnostic agent for finding and fixing bugs
- **`test`** - Testing agent for generating and running tests

### Configuration

Override the default model using the `LOCAL_AI_MODEL` environment variable:

```bash
export LOCAL_AI_MODEL="llama3.2:3b"
code
```

Default model: `qwen2.5-coder:14b`

### Workflow

The commands work together in a professional development workflow:

```
design → code → craft → debug → test
```

1. **Design** - Create or update design documents
2. **Code** - Refactor and modify existing code
3. **Craft** - Implement new features and scaffolding
4. **Debug** - Fix errors and issues
5. **Test** - Generate and run tests

---

## 🔧 Technical Details

### Project Structure

```
pyr/
├── agent.py              # Core runtime with Ollama integration
├── installer.sh          # System-wide installation script
├── README.md             # This file
├── prompts/
│   ├── code.txt          # Code agent prompt
│   ├── design.txt        # Design agent prompt
│   ├── craft.txt         # Craft agent prompt
│   ├── debug.txt         # Debug agent prompt
│   └── test.txt          # Test agent prompt
├── structures/           # Project structure templates
│   ├── swift_swiftui.json
│   ├── javascript_nodejs.json
│   ├── python.json
│   ├── rust.json
│   └── go.json
└── tools/
    ├── fs.py             # File system helpers
    ├── shell.py          # Shell execution helpers
    ├── diff.py           # Diff generation
    └── structures.py     # Structure detection
```

### Safety Features

- **Automatic Backups** - Files are backed up with `.backup` extension before modification
- **Confirmation Prompts** - Destructive actions require confirmation
- **Command Blocking** - Dangerous commands are blocked
- **Context Limits** - Large files (>300KB) are skipped

### Requirements

- macOS (Terminal)
- Python 3.7+
- Ollama installed and running
- Model: `qwen2.5-coder:14b` (or set `LOCAL_AI_MODEL`)

---

## 🏗️ Structures

Pyr automatically detects project types and makes intelligent assumptions about the technology stack, file structure, and build commands.

### How It Works

When you use the `design` command, Pyr analyzes your request and existing files to detect the appropriate project structure:

- **Swift/SwiftUI**: Detects macOS/iOS apps, assumes Swift Package Manager structure
- **JavaScript/Node.js**: Detects web/Node projects, assumes npm/package.json structure
- **Python**: Detects Python projects, assumes requirements.txt structure
- **Rust**: Detects Rust projects, assumes Cargo structure
- **Go**: Detects Go projects, assumes go.mod structure

### Example

```bash
design "design a simple to-do app for macOS"
```

Pyr will:
1. Detect "macOS" keyword → assumes Swift/SwiftUI structure
2. Extract project name (or use directory name)
3. Include structure assumptions in the design document:
   - Language: Swift
   - Framework: SwiftUI
   - Platform: macOS
   - Package Manager: Swift Package Manager
   - Build: `swift build`
   - Run: `swift run`
   - Required files: `Package.swift`, `Sources/{Project}/App.swift`, etc.

### Customizing Structures

Structures are defined in JSON files in the `structures/` directory. Each structure includes:

- **Detection rules**: Keywords and file patterns to identify the structure
- **Assumptions**: Technology stack, build commands, file structure
- **Templates**: File templates for required files
- **Prompt template**: Instructions for the AI agent

You can:
- **Modify existing structures**: Edit the JSON files in `structures/`
- **Create new structures**: Add new JSON files following the same format
- **Override assumptions**: The design document can specify different choices

### Available Structures

- `swift_swiftui.json` - Swift/SwiftUI macOS/iOS apps
- `javascript_nodejs.json` - JavaScript/Node.js projects
- `python.json` - Python projects
- `rust.json` - Rust projects
- `go.json` - Go projects

### Structure Format

Each structure JSON file contains:

```json
{
  "name": "Structure Name",
  "detection": {
    "keywords": ["keyword1", "keyword2"],
    "files": ["file.pattern", "*.ext"]
  },
  "assumptions": {
    "language": "Language",
    "framework": "Framework",
    "package_manager": "Package Manager",
    "build_command": "build command",
    "run_command": "run command",
    "structure": {
      "file/path": {
        "required": true,
        "template": "file template with {PLACEHOLDERS}",
        "description": "file description"
      }
    }
  },
  "prompt_template": "Instructions for the AI agent"
}
```

**Note**: Structures make assumptions to speed up development. You can always override these in your design document or modify the structure files to match your preferences.

---

**Built for macOS Terminal • Powered by Ollama • Fully Local**
