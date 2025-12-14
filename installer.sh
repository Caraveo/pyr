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
    
    # Special handling for 'test' command to avoid shell built-in conflict
    if [ "$cmd_name" = "test" ]; then
        cat > "$wrapper_path" << 'EOF'
#!/bin/bash
# Wrapper for test command (avoiding shell built-in)
exec python3 "$HOME/.local-ai-agent/agent.py" test "$@"
EOF
    else
        cat > "$wrapper_path" << EOF
#!/bin/bash
# Wrapper for $cmd_name command
exec python3 "$INSTALL_DIR/agent.py" $cmd_name "\$@"
EOF
    fi
    
    chmod +x "$wrapper_path"
    
    # Create symlink (requires sudo)
    # For 'test', use a different approach to override shell built-in
    if [ "$cmd_name" = "test" ]; then
        # Create an alias or function in shell config, or use full path
        if sudo ln -sf "$wrapper_path" "$BIN_DIR/ai-test" 2>/dev/null; then
            echo "  ✓ Installed: ai-test (use 'ai-test' or full path to avoid shell built-in)"
            echo "    Note: 'test' is a shell built-in. Use 'ai-test' or '$wrapper_path'"
        else
            echo "  ✗ Failed to install test command (may need sudo)"
            echo "    Run manually: sudo ln -sf $wrapper_path $BIN_DIR/ai-test"
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
echo "  - test    (testing agent)"
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
echo "Optional (recommended for better JSON parsing):"
echo "  - json5: pip3 install json5"
echo ""
echo "To uninstall, run:"
echo "  sudo rm $BIN_DIR/{code,design,craft,debug,test}"
echo "  rm -rf $INSTALL_DIR"
echo ""

