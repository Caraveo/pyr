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
cp "$SCRIPT_DIR/tools/edit.py" "$INSTALL_DIR/tools/" 2>/dev/null || true
cp "$SCRIPT_DIR/tools/syntax.py" "$INSTALL_DIR/tools/" 2>/dev/null || true
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
    # Install json5 (REQUIRED for parsing AI responses)
    if python3 -c "import json5" 2>/dev/null; then
        echo "  ✓ json5 already installed"
    else
        echo "  Installing json5 (REQUIRED for parsing AI responses)..."
        # Try multiple installation methods for compatibility
        if python3 -m pip install --user json5 >/dev/null 2>&1; then
            echo "    ✓ Installed json5 (user install)"
        elif python3 -m pip install --break-system-packages json5 >/dev/null 2>&1; then
            echo "    ✓ Installed json5 (system install)"
        elif pip3 install --user json5 >/dev/null 2>&1; then
            echo "    ✓ Installed json5 (user install via pip3)"
        elif pip3 install --break-system-packages json5 >/dev/null 2>&1; then
            echo "    ✓ Installed json5 (system install via pip3)"
        else
            echo "    ✗ ERROR: Could not install json5 automatically"
            echo "       json5 is REQUIRED. Please install manually:"
            echo "       pip3 install --user json5"
            echo "       Or: pip3 install --break-system-packages json5"
            exit 1
        fi
    fi
    
    # Install ddgs (for web search in debug mode)
    if python3 -c "import ddgs" 2>/dev/null || python3 -c "import duckduckgo_search" 2>/dev/null; then
        echo "  ✓ ddgs (or duckduckgo_search) already installed"
    else
        echo "  Installing ddgs (for web search in debug mode)..."
        # Try multiple installation methods for compatibility
        if python3 -m pip install --user ddgs >/dev/null 2>&1; then
            echo "    ✓ Installed ddgs (user install)"
        elif python3 -m pip install --break-system-packages ddgs >/dev/null 2>&1; then
            echo "    ✓ Installed ddgs (system install)"
        elif pip3 install --user ddgs >/dev/null 2>&1; then
            echo "    ✓ Installed ddgs (user install via pip3)"
        elif pip3 install --break-system-packages ddgs >/dev/null 2>&1; then
            echo "    ✓ Installed ddgs (system install via pip3)"
        else
            echo "    ⚠️  Warning: Could not install ddgs automatically"
            echo "       Web search in debug mode will not work. Install manually:"
            echo "       pip3 install --user ddgs"
            echo "       Or: pip3 install --break-system-packages ddgs"
        fi
    fi
    
    # Install tree-sitter (for syntax validation)
    if python3 -c "import tree_sitter" 2>/dev/null; then
        echo "  ✓ tree-sitter already installed"
    else
        echo "  Installing tree-sitter (for syntax validation)..."
        # Try multiple installation methods for compatibility
        if python3 -m pip install --user tree-sitter >/dev/null 2>&1; then
            echo "    ✓ Installed tree-sitter (user install)"
        elif python3 -m pip install --break-system-packages tree-sitter >/dev/null 2>&1; then
            echo "    ✓ Installed tree-sitter (system install)"
        elif pip3 install --user tree-sitter >/dev/null 2>&1; then
            echo "    ✓ Installed tree-sitter (user install via pip3)"
        elif pip3 install --break-system-packages tree-sitter >/dev/null 2>&1; then
            echo "    ✓ Installed tree-sitter (system install via pip3)"
        else
            echo "    ⚠️  Warning: Could not install tree-sitter automatically"
            echo "       Syntax validation will be skipped. Install manually:"
            echo "       pip3 install --user tree-sitter"
            echo "       Or: pip3 install --break-system-packages tree-sitter"
        fi
    fi
    
    # Install common tree-sitter language parsers
    if python3 -c "import tree_sitter" 2>/dev/null; then
        echo "  Installing tree-sitter language parsers (for syntax validation)..."
        
        # List of common language parsers to install
        parsers=(
            "tree-sitter-python"
            "tree-sitter-javascript"
            "tree-sitter-typescript"
            "tree-sitter-java"
            "tree-sitter-c"
            "tree-sitter-cpp"
            "tree-sitter-rust"
            "tree-sitter-go"
            "tree-sitter-ruby"
            "tree-sitter-php"
            "tree-sitter-bash"
            "tree-sitter-yaml"
            "tree-sitter-json"
            "tree-sitter-html"
            "tree-sitter-css"
            "tree-sitter-sql"
        )
        
        for parser in "${parsers[@]}"; do
            parser_name=$(echo "$parser" | sed 's/tree-sitter-//')
            if python3 -c "import tree_sitter_${parser_name}" 2>/dev/null; then
                echo "    ✓ $parser_name parser already installed"
            else
                # Try to install (silently, don't fail if it doesn't work)
                if python3 -m pip install --user "$parser" >/dev/null 2>&1 || \
                   python3 -m pip install --break-system-packages "$parser" >/dev/null 2>&1 || \
                   pip3 install --user "$parser" >/dev/null 2>&1 || \
                   pip3 install --break-system-packages "$parser" >/dev/null 2>&1; then
                    echo "    ✓ Installed $parser_name parser"
                else
                    echo "    ⚠️  Could not install $parser_name parser (optional)"
                fi
            fi
        done
        
        # Optional parsers (Swift, Kotlin, etc.) - try to install but don't warn if they fail
        optional_parsers=(
            "tree-sitter-swift"
            "tree-sitter-kotlin"
            "tree-sitter-lua"
            "tree-sitter-r"
            "tree-sitter-toml"
            "tree-sitter-xml"
        )
        
        for parser in "${optional_parsers[@]}"; do
            parser_name=$(echo "$parser" | sed 's/tree-sitter-//')
            if ! python3 -c "import tree_sitter_${parser_name}" 2>/dev/null; then
                # Try to install silently (don't show output)
                python3 -m pip install --user "$parser" >/dev/null 2>&1 || \
                python3 -m pip install --break-system-packages "$parser" >/dev/null 2>&1 || \
                pip3 install --user "$parser" >/dev/null 2>&1 || \
                pip3 install --break-system-packages "$parser" >/dev/null 2>&1 || true
            fi
        done
    fi
    
fi

echo ""
echo "To uninstall, run:"
echo "  sudo rm $BIN_DIR/{code,design,craft,debug,check}"
echo "  rm -rf $INSTALL_DIR"
echo ""

