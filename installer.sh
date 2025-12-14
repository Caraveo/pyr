#!/bin/bash
# Installer for Local AI Agent Toolchain
# Installs system-wide commands: code, design, craft, debug, test

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="$HOME/.local-ai-agent"
BIN_DIR="/usr/local/bin"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Local AI Agent Toolchain Installer"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Check if running on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "Warning: This installer is designed for macOS."
    echo "Continuing anyway..."
    echo ""
fi

# Create installation directory
echo "Creating installation directory: $INSTALL_DIR"
mkdir -p "$INSTALL_DIR"
mkdir -p "$INSTALL_DIR/tools"
mkdir -p "$INSTALL_DIR/prompts"
mkdir -p "$INSTALL_DIR/structures"

# Copy files
echo "Copying agent files..."
cp "$SCRIPT_DIR/agent.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/tools/fs.py" "$INSTALL_DIR/tools/"
cp "$SCRIPT_DIR/tools/shell.py" "$INSTALL_DIR/tools/"
cp "$SCRIPT_DIR/tools/diff.py" "$INSTALL_DIR/tools/"
cp "$SCRIPT_DIR/tools/structures.py" "$INSTALL_DIR/tools/" 2>/dev/null || true
cp "$SCRIPT_DIR/tools/progress.py" "$INSTALL_DIR/tools/" 2>/dev/null || true
cp "$SCRIPT_DIR/tools/web.py" "$INSTALL_DIR/tools/" 2>/dev/null || true
cp "$SCRIPT_DIR/tools/__init__.py" "$INSTALL_DIR/tools/" 2>/dev/null || touch "$INSTALL_DIR/tools/__init__.py"
cp "$SCRIPT_DIR/prompts/"*.txt "$INSTALL_DIR/prompts/"
cp "$SCRIPT_DIR/structures/"*.json "$INSTALL_DIR/structures/" 2>/dev/null || true

# Make agent.py executable
chmod +x "$INSTALL_DIR/agent.py"

# Create wrapper scripts for each command
echo ""
echo "Creating system-wide commands..."

# Function to create a command wrapper
create_command() {
    local cmd_name=$1
    local wrapper_path="$INSTALL_DIR/${cmd_name}_wrapper.sh"
    
    cat > "$wrapper_path" << EOF
#!/bin/bash
# Wrapper for $cmd_name command
exec python3 "$INSTALL_DIR/agent.py" $cmd_name "\$@"
EOF
    
    chmod +x "$wrapper_path"
    
    # Special handling for 'test' command - install as 'check' to avoid shell built-in conflict
    if [ "$cmd_name" = "test" ]; then
        if sudo ln -sf "$wrapper_path" "$BIN_DIR/check" 2>/dev/null; then
            echo "  ✓ Installed: check (use 'check' to run tests, avoids shell built-in 'test')"
            echo "    Note: 'test' is a shell built-in. Use 'check' or '$wrapper_path'"
        else
            echo "  ✗ Failed to install check command (may need sudo)"
            echo "    Run manually: sudo ln -sf $wrapper_path $BIN_DIR/check"
        fi
    else
        if sudo ln -sf "$wrapper_path" "$BIN_DIR/$cmd_name" 2>/dev/null; then
            echo "  ✓ Installed: $cmd_name"
        else
            echo "  ✗ Failed to install $cmd_name (may need sudo)"
            echo "    Run manually: sudo ln -sf $wrapper_path $BIN_DIR/$cmd_name"
        fi
    fi
}

# Install all commands
create_command "code"
create_command "design"
create_command "craft"
create_command "debug"
create_command "test"

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "Installation complete!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Installed commands:"
echo "  - code    (interactive coding agent)"
echo "  - design  (design document agent)"
echo "  - craft   (implementation agent)"
echo "  - debug   (debugging agent)"
echo "  - check   (testing agent - runs tests or creates .test files)"
echo ""
echo "Usage:"
echo "  code                    # Interactive mode"
echo "  design \"your request\"   # Design mode"
echo "  craft \"your request\"    # Implementation mode"
echo ""
echo "Requirements:"
echo "  - Ollama must be installed (https://ollama.ai)"
echo "  - Model: qwen2.5-coder:14b (or set LOCAL_AI_MODEL env var)"
echo ""
echo "Installing Python dependencies..."
echo ""

# Check if pip3 is available
if ! command -v pip3 &> /dev/null; then
    echo "  ⚠️  Warning: pip3 not found. Please install Python 3 with pip to use optional features."
    echo "     Install manually: pip3 install json5 duckduckgo-search"
else
    # Install json5 for better JSON parsing
    if python3 -c "import json5" 2>/dev/null; then
        echo "  ✓ json5 already installed"
    else
        echo "  Installing json5 (for better JSON parsing)..."
        pip3 install --quiet json5 2>/dev/null && echo "    ✓ Installed json5" || echo "    ✗ Failed to install json5 (run manually: pip3 install json5)"
    fi
    
    # Install duckduckgo-search for web search in debug mode
    if python3 -c "import duckduckgo_search" 2>/dev/null; then
        echo "  ✓ duckduckgo-search already installed"
    else
        echo "  Installing duckduckgo-search (for web search in debug mode)..."
        pip3 install --quiet duckduckgo-search 2>/dev/null && echo "    ✓ Installed duckduckgo-search" || echo "    ✗ Failed to install duckduckgo-search (run manually: pip3 install duckduckgo-search)"
    fi
fi

echo ""
echo "To uninstall, run:"
echo "  sudo rm $BIN_DIR/{code,design,craft,debug,check}"
echo "  rm -rf $INSTALL_DIR"
echo ""

