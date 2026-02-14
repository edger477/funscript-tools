#!/bin/bash
# Setup script for Restim Funscript Processor - macOS and Linux
# Creates a virtual environment and installs dependencies

echo "============================================"
echo " Restim Funscript Processor - Setup"
echo "============================================"
echo ""

# Detect OS
OS="$(uname -s)"
case "${OS}" in
    Linux*)     PLATFORM="Linux";;
    Darwin*)    PLATFORM="macOS";;
    *)          PLATFORM="Unknown";;
esac

echo "Detected platform: ${PLATFORM}"
echo ""

# Find Python 3
PYTHON_CMD=""
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    # Check if python is Python 3
    if python --version 2>&1 | grep -q "Python 3"; then
        PYTHON_CMD="python"
    fi
fi

if [ -z "$PYTHON_CMD" ]; then
    echo "ERROR: Python 3 is not installed or not in PATH."
    if [ "$PLATFORM" = "macOS" ]; then
        echo "Install Python using Homebrew: brew install python3"
        echo "Or download from: https://www.python.org/downloads/"
    else
        echo "Install Python using your package manager:"
        echo "  Ubuntu/Debian: sudo apt install python3 python3-venv python3-pip"
        echo "  Fedora: sudo dnf install python3 python3-pip"
        echo "  Arch: sudo pacman -S python python-pip"
    fi
    exit 1
fi

echo "Found Python: $($PYTHON_CMD --version)"
echo ""

# Check Python version (need 3.8+)
PYTHON_VERSION=$($PYTHON_CMD -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PYTHON_MAJOR=$($PYTHON_CMD -c 'import sys; print(sys.version_info.major)')
PYTHON_MINOR=$($PYTHON_CMD -c 'import sys; print(sys.version_info.minor)')

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 8 ]); then
    echo "ERROR: Python 3.8 or later is required. Found Python ${PYTHON_VERSION}"
    exit 1
fi

# Check for tkinter (required for GUI)
if ! $PYTHON_CMD -c "import tkinter" 2>/dev/null; then
    echo "WARNING: tkinter is not installed."
    if [ "$PLATFORM" = "macOS" ]; then
        echo "tkinter should be included with Python from python.org"
        echo "If using Homebrew Python, try: brew install python-tk"
    else
        echo "Install tkinter using your package manager:"
        echo "  Ubuntu/Debian: sudo apt install python3-tk"
        echo "  Fedora: sudo dnf install python3-tkinter"
        echo "  Arch: sudo pacman -S tk"
    fi
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo ""
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    $PYTHON_CMD -m venv venv
    if [ $? -ne 0 ]; then
        echo "ERROR: Failed to create virtual environment."
        echo "You may need to install python3-venv:"
        echo "  Ubuntu/Debian: sudo apt install python3-venv"
        exit 1
    fi
    echo "Virtual environment created."
else
    echo "Virtual environment already exists."
fi
echo ""

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to activate virtual environment."
    exit 1
fi

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip
echo ""

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo "ERROR: Failed to install dependencies."
    exit 1
fi
echo ""

echo "============================================"
echo " Setup Complete!"
echo "============================================"
echo ""
echo "To run the application:"
echo "  1. Activate the environment: source venv/bin/activate"
echo "  2. Run the app: python main.py"
echo ""
echo "Or use the run.sh script (creating now)..."

# Create a run script
cat > run.sh << 'EOF'
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"
source venv/bin/activate
python main.py
EOF

chmod +x run.sh

echo ""
echo "Created run.sh - execute it to start the application!"
echo "  ./run.sh"
echo ""
