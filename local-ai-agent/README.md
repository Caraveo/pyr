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
local-ai-agent/
├── agent.py              # Core runtime with Ollama integration
├── installer.sh          # System-wide installation script
├── README.md             # This file
├── prompts/
│   ├── code.txt          # Code agent prompt
│   ├── design.txt        # Design agent prompt
│   ├── craft.txt         # Craft agent prompt
│   ├── debug.txt         # Debug agent prompt
│   └── test.txt          # Test agent prompt
└── tools/
    ├── fs.py             # File system helpers
    ├── shell.py          # Shell execution helpers
    └── diff.py           # Diff generation
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

**Built for macOS Terminal • Powered by Ollama • Fully Local**
