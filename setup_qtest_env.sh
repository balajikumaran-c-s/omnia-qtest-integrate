#!/bin/bash
# Copyright 2026 Dell Inc. or its subsidiaries. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

# setup_qtest_env.sh - Set up qtest CLI tool
# Usage: ./setup_qtest_env.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

echo ""
echo "============================================"
echo "  qtest CLI - Setup"
echo "============================================"
echo ""

# Check Python
if ! command -v python3 &>/dev/null; then
    echo "Error: python3 not found. Install Python 3.8+ first."
    exit 1
fi

PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "  Python version : $PYTHON_VERSION"
echo "  Project dir    : $SCRIPT_DIR"
echo ""

# Create venv
if [ -d "$VENV_DIR" ]; then
    echo "[1/3] Virtual environment already exists"
else
    echo "[1/3] Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# Activate and install
echo "[2/3] Installing dependencies..."
source "$VENV_DIR/bin/activate"
pip install --quiet --upgrade pip
pip install --quiet -e "$SCRIPT_DIR"

# Create wrapper script at /usr/local/bin/qtest (Linux/macOS only)
if [ -d "/usr/local/bin" ]; then
        echo "[3/4] Creating 'qtest' command at /usr/local/bin/qtest..."
    WRAPPER="/usr/local/bin/qtest"
    cat > "$WRAPPER" << 'WRAPPER_EOF'
#!/bin/bash
VENV_PYTHON="VENV_DIR_PLACEHOLDER/.venv/bin/python"
exec "$VENV_PYTHON" -m qtest_cli.main "$@"
WRAPPER_EOF
sed -i "s|VENV_DIR_PLACEHOLDER|$SCRIPT_DIR|g" "$WRAPPER"
chmod +x "$WRAPPER"

    echo "[4/4] Setting up tab completion..."
    COMPLETION_SCRIPT="$SCRIPT_DIR/.qtest-complete.bash"
cat > "$COMPLETION_SCRIPT" << 'COMP_EOF'
_qtest_completion() {
    local cur prev commands
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    commands="ls list add-tc download show-config"

    case "$prev" in
        qtest)
            COMPREPLY=( $(compgen -W "$commands --help --config" -- "$cur") )
            ;;
        ls|list)
            COMPREPLY=( $(compgen -W "-al --help" -- "$cur") )
            ;;
        add-tc)
            COMPREPLY=( $(compgen -W "--dry-run --template --parent-id --help -t -p -d" -- "$cur") )
            ;;
        download)
            COMPREPLY=( $(compgen -W "--output --help -o" -- "$cur") )
            ;;
        -t|--template)
            COMPREPLY=( $(compgen -f -X '!*.yaml' -- "$cur") $(compgen -f -X '!*.yml' -- "$cur") )
            ;;
        -c|--config)
            COMPREPLY=( $(compgen -f -X '!*.yaml' -- "$cur") $(compgen -f -X '!*.yml' -- "$cur") )
            ;;
        *)
            COMPREPLY=()
            ;;
    esac
}
complete -F _qtest_completion qtest
COMP_EOF

    # Add completion to bashrc if not already there
    BASHRC="$HOME/.bashrc"
    COMP_LINE="source $COMPLETION_SCRIPT"
    if ! grep -qF "$COMP_LINE" "$BASHRC" 2>/dev/null; then
        echo "" >> "$BASHRC"
        echo "# qtest CLI tab completion" >> "$BASHRC"
        echo "$COMP_LINE" >> "$BASHRC"
    fi

    # Source completion for current session
    source "$COMPLETION_SCRIPT"
else
    echo "[3/4] Skipping system wrapper (not Linux/macOS)"
    echo "       Use: source .venv/bin/activate && qtest"
fi

echo ""
echo "============================================"
echo "  Setup complete!"
echo "============================================"
echo ""
echo "  Virtual env: $VENV_DIR"
echo ""
echo "  To activate the virtual environment:"
echo "    source $VENV_DIR/bin/activate"
echo ""
echo "  To deactivate:"
echo "    deactivate"
echo ""
echo "  The 'qtest' command is also available without"
echo "  activating the venv (wrapper installed at /usr/local/bin/qtest)."
echo "  Tab completion is enabled."
echo ""
echo "  Next steps:"
echo ""
echo "  1. Edit config.yaml with your qTest details:"
echo "     vi $SCRIPT_DIR/config.yaml"
echo ""
echo "  2. Test the connection:"
echo "     qtest ls"
echo ""
echo "  3. Browse folders:"
echo "     qtest ls \"Omnia-2.X\""
echo "     qtest ls -al \"Omnia-2.X/Slurm Cluster\""
echo ""
echo "  4. Add test cases:"
echo "     qtest add-tc --dry-run      (preview)"
echo "     qtest add-tc                (push to qTest)"
echo ""
