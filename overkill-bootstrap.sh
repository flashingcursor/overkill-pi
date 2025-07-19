#!/bin/bash
# OVERKILL Bootstrap Script - Minimal installer for Python-based configurator
# Version: 3.0.0-PYTHON
# This script sets up the Python environment and launches the main configurator

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# Configuration
OVERKILL_HOME="/opt/overkill"
OVERKILL_REPO="https://github.com/flashingcursor/overkill-pi"
OVERKILL_BRANCH="master"

log() {
    echo -e "${GREEN}[OVERKILL]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
    exit 1
}

warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

show_banner() {
    echo -e "${RED}"
    cat << 'EOF'
        ....            _                                       ..         .          ..       .. 
    .x~X88888Hx.       u                                  < .z@8"`        @88>  x .d88"  x .d88"  
   H8X 888888888h.    88Nu.   u.                .u    .    !@88E          %8P    5888R    5888R   
  8888:`*888888888:  '88888.o888c      .u     .d88B :@8c   '888E   u       .     '888R    '888R   
  88888:        `%8   ^8888  8888   ud8888.  ="8888f8888r   888E u@8NL   .@88u    888R     888R   
. `88888          ?>   8888  8888 :888'8888.   4888>'88"    888E`"88*"  ''888E`   888R     888R   
`. ?888%           X   8888  8888 d888 '88%"   4888> '      888E .dN.     888E    888R     888R   
  ~*??.            >   8888  8888 8888.+"      4888>        888E~8888     888E    888R     888R   
 .x88888h.        <   .8888b.888P 8888L       .d888L .+     888E '888&    888E    888R     888R   
:"""8888888x..  .x     ^Y8888*""  '8888c. .+  ^"8888*"      888E  9888.   888&   .888B .  .888B . 
`    `*888888888"        `Y"       "88888%       "Y"      '"888*" 4888"   R888"  ^*888%   ^*888%  
        ""***""                      "YP'                    ""    ""      ""      "%       "%    
EOF
    echo -e "${NC}"
    echo -e "${CYAN}    Version 3.0.0 - Python-Powered Media Center Configuration${NC}"
    echo -e "${YELLOW}    Professional configuration for UNLIMITED POWER${NC}\n"
}

check_root() {
    if [[ $EUID -ne 0 ]]; then
        error "This script must be run as root (use sudo)"
    fi
}

check_system() {
    log "Checking system compatibility..."
    
    # Check for Pi 5
    local model=$(tr -d '\0' < /proc/device-tree/model 2>/dev/null || echo "Unknown")
    if [[ ! "$model" =~ "Raspberry Pi 5" ]]; then
        warn "This is optimized for Raspberry Pi 5"
        warn "Detected: $model"
        read -p "Continue anyway? (y/N): " -n 1 -r </dev/tty
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            error "Installation cancelled"
        fi
    fi
    
    # Check for NVMe
    if ! lsblk -d -o NAME | grep -q '^nvme'; then
        warn "No NVMe storage detected - performance will be limited"
    fi
}

install_dependencies() {
    log "Installing Python and system dependencies..."
    
    apt-get update
    apt-get install -y \
        python3 \
        python3-pip \
        python3-venv \
        python3-dev \
        git \
        dialog \
        build-essential \
        libffi-dev \
        libssl-dev \
        stress-ng \
        lm-sensors \
        nvme-cli \
        curl \
        wget
}

setup_python_environment() {
    log "Setting up Python virtual environment..."
    
    # Create overkill directory
    mkdir -p "$OVERKILL_HOME"
    
    # Create virtual environment
    python3 -m venv "$OVERKILL_HOME/venv"
    
    # Activate virtual environment
    source "$OVERKILL_HOME/venv/bin/activate"
    
    # Upgrade pip
    pip install --upgrade pip wheel setuptools
}

install_overkill() {
    log "Installing OVERKILL Python application..."
    
    # Activate virtual environment for installation
    source "$OVERKILL_HOME/venv/bin/activate"
    
    # For development, install from current directory
    if [[ -f "./setup.py" ]] && [[ -d "./overkill" ]]; then
        log "Installing from local directory..."
        pip install -e .
    else
        # For production, clone from repository
        log "Cloning from repository..."
        local temp_dir="/tmp/overkill-install-$$"
        git clone -b "$OVERKILL_BRANCH" "$OVERKILL_REPO" "$temp_dir"
        cd "$temp_dir"
        
        # Install the package
        pip install .
        
        # Copy any additional files needed
        if [[ -d "kodi-addon" ]]; then
            cp -r "kodi-addon" "$OVERKILL_HOME/"
        fi
        
        # Cleanup
        cd /
        rm -rf "$temp_dir"
    fi
}

create_launcher() {
    log "Creating launcher script..."
    
    cat > /usr/local/bin/overkill << 'EOF'
#!/bin/bash
# OVERKILL Launcher

OVERKILL_HOME="/opt/overkill"

# Activate virtual environment
source "$OVERKILL_HOME/venv/bin/activate"

# Check if first run (no config exists)
if [ ! -f "/etc/overkill/config.json" ]; then
    # First run - launch installer
    exec python -m overkill.installer "$@"
else
    # Config exists - launch configurator
    exec python -m overkill.configurator "$@"
fi
EOF
    
    chmod +x /usr/local/bin/overkill
}

main() {
    clear
    show_banner
    
    check_root
    check_system
    
    echo -e "${CYAN}Ready to install OVERKILL Python Configurator?${NC}"
    read -p "Continue? (y/N): " -n 1 -r </dev/tty
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        error "Installation cancelled"
    fi
    
    install_dependencies
    setup_python_environment
    install_overkill
    create_launcher
    
    echo -e "\n${GREEN}✓ OVERKILL Bootstrap Complete!${NC}"
    echo -e "${CYAN}Run 'sudo overkill' to launch the configuration tool${NC}"
    
    # Launch installer automatically
    echo
    echo -e "${CYAN}Launching OVERKILL installer...${NC}"
    /usr/local/bin/overkill
}

# Run main function
main "$@"