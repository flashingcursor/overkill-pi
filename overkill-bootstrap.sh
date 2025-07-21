#!/usr/bin/env bash
# OVERKILL Bootstrap Script - Minimal installer for Python-based configurator
# Version: 3.0.0-PYTHON
# This script sets up the Python environment and launches the main configurator

set -o errexit -o nounset -o pipefail

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

# Temp directory (will be set in main)
TEMP_DIR=""

# Cleanup function
cleanup() {
    local exit_code=$?
    
    # Kill any remaining spinner
    if [[ ${SPINNER_PID} -gt 0 ]]; then
        kill ${SPINNER_PID} &>/dev/null
        wait ${SPINNER_PID} &>/dev/null
        tput cnorm || true # Show cursor
    fi
    
    if [[ -n "${TEMP_DIR:-}" ]] && [[ -d "${TEMP_DIR}" ]]; then
        log "Cleaning up temporary files..."
        rm -rf "${TEMP_DIR}"
    fi
    
    exit ${exit_code}
}

# Set up trap for cleanup
trap cleanup EXIT INT TERM

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

# --- Professional Task Runner ---
LOG_DIR="/var/log/overkill"
LOG_FILE="${LOG_DIR}/bootstrap_$(date +%Y%m%d_%H%M%S).log"
SPINNER_PID=0

# Ensure log directory exists
mkdir -p "${LOG_DIR}"

# Starts a spinner animation for a background process
start_spinner() {
    {
        tput civis || true # Hide cursor
        while true; do
            for s in / - \\ \|; do
                printf "\r${CYAN}  [%s]${NC} %s..." "$s" "$1"
                sleep 0.1
            done
        done
    } &
    SPINNER_PID=$!
    disown $SPINNER_PID  # Disown the process so it won't trigger EXIT trap
}

# Stops the spinner and displays the final result
stop_spinner() {
    local exit_code=$1
    local desc="$2"
    
    if [[ ${SPINNER_PID} -gt 0 ]]; then
        # Use SIGTERM which is gentler
        kill -TERM ${SPINNER_PID} 2>/dev/null || true
        SPINNER_PID=0
    fi
    
    tput cnorm || true # Show cursor
    printf "\r\033[K" # Clear the line

    if [[ ${exit_code} -eq 0 ]]; then
        printf "${GREEN}  [✓]${NC} %s... Done\n" "$desc"
    else
        printf "${RED}  [✗]${NC} %s... FAILED\n" "$desc"
        echo -e "${RED}    Error details are in the log file: ${LOG_FILE}${NC}"
    fi
}

# The main function to run a command with professional output
run_task() {
    local desc="$1"
    local cmd="$2"
    local exit_code=0
    
    start_spinner "$desc"
    
    # Run the command and capture exit code
    if eval "$cmd" >> "${LOG_FILE}" 2>&1; then
        exit_code=0
    else
        exit_code=$?
    fi
    
    stop_spinner ${exit_code} "$desc"

    if [[ ${exit_code} -ne 0 ]]; then
        return 1
    fi
    
    return 0
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
    
    # Check for Pi 5 using cpuinfo
    local is_pi5=false
    if grep -q "Raspberry Pi 5" /proc/cpuinfo 2>/dev/null; then
        is_pi5=true
    fi
    
    if [[ "${is_pi5}" != "true" ]]; then
        warn "This is optimized for Raspberry Pi 5"
        local model=$(grep "Model" /proc/cpuinfo 2>/dev/null | cut -d: -f2 | xargs || echo "Unknown device")
        if [[ -z "${model}" ]]; then
            model="Unknown device"
        fi
        warn "Detected: ${model}"
        local REPLY
        read -p "Continue anyway? (y/N): " -n 1 -r REPLY </dev/tty
        echo
        if [[ ! ${REPLY} =~ ^[Yy]$ ]]; then
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
    echo -e "  (Full details will be logged to ${YELLOW}$LOG_FILE${NC})"
    export DEBIAN_FRONTEND=noninteractive
    
    run_task "Updating package lists" "apt-get update"
    run_task "Installing required packages" "apt-get install -y python3 python3-pip python3-venv python3-dev git dialog build-essential libffi-dev libssl-dev stress-ng lm-sensors nvme-cli curl wget"
}

setup_python_environment() {
    log "Setting up Python virtual environment..."
    
    # Create overkill directory
    run_task "Creating overkill directory" "mkdir -p '$OVERKILL_HOME'"
    
    # Create virtual environment
    run_task "Creating Python virtual environment" "python3 -m venv '$OVERKILL_HOME/venv'"
    
    # Activate virtual environment
    source "$OVERKILL_HOME/venv/bin/activate"
    
    # Upgrade pip
    run_task "Upgrading pip and setuptools" "source '$OVERKILL_HOME/venv/bin/activate' && pip install --upgrade pip wheel setuptools"
}

install_overkill() {
    log "Installing OVERKILL Python application..."
    
    # Activate virtual environment for installation
    source "${OVERKILL_HOME}/venv/bin/activate"
    
    # For development, install from current directory
    if [[ -f "./setup.py" ]] && [[ -d "./overkill" ]]; then
        log "Installing from local directory..."
        run_task "Installing OVERKILL package" "source '${OVERKILL_HOME}/venv/bin/activate' && pip install --use-pep517 --force-reinstall -e ."
    else
        # For production, clone from repository
        log "Cloning from repository..."
        run_task "Cloning OVERKILL repository" "git clone -b '${OVERKILL_BRANCH}' '${OVERKILL_REPO}' '${TEMP_DIR}'"
        cd "${TEMP_DIR}"
        
        # Install the package using PEP 517
        run_task "Installing OVERKILL package" "source '${OVERKILL_HOME}/venv/bin/activate' && pip install --use-pep517 --force-reinstall ."
        
        # Copy any additional files needed
        if [[ -d "kodi-addon" ]]; then
            run_task "Copying Kodi addon files" "cp -r 'kodi-addon' '${OVERKILL_HOME}/'"
        fi
        
        # Return to original directory
        cd - >/dev/null
    fi
}

create_launcher() {
    log "Creating launcher script..."
    
    # Create the launcher script
    run_task "Creating launcher script" "cat > /usr/local/bin/overkill << 'EOF'
#!/usr/bin/env bash
# OVERKILL Launcher

set -o errexit -o nounset -o pipefail

OVERKILL_HOME=\"/opt/overkill\"

# Activate virtual environment
source \"\${OVERKILL_HOME}/venv/bin/activate\"

# Set TTY font early for TV viewing
if [ -t 0 ] && [[ \$(tty) =~ ^/dev/tty[0-9]+\$ ]]; then
    setfont /usr/share/consolefonts/Lat15-TerminusBold28x14.psf.gz 2>/dev/null || \\
    setfont /usr/share/consolefonts/Lat15-TerminusBold20x10.psf.gz 2>/dev/null || \\
    setfont /usr/share/consolefonts/Lat15-Fixed16.psf.gz 2>/dev/null || true
fi

# Find the overkill package location
OVERKILL_PKG=\$(python -c \"import overkill; import os; print(os.path.dirname(overkill.__file__))\" 2>/dev/null)

if [ -z \"\${OVERKILL_PKG}\" ]; then
    echo \"Error: OVERKILL package not found in virtual environment\"
    exit 1
fi

# Check if first run (no config exists)
if [ ! -f \"/etc/overkill/config.json\" ]; then
    # First run - run installer
    exec python \"\${OVERKILL_PKG}/run_installer.py\" \"\$@\"
else
    # Config exists - run configurator
    exec python \"\${OVERKILL_PKG}/run_configurator.py\" \"\$@\"
fi
EOF"
    
    run_task "Setting launcher permissions" "chmod +x /usr/local/bin/overkill"
}

main() {
    # Create temp directory
    TEMP_DIR=$(mktemp -d /tmp/overkill-install.XXXXXX)
    
    clear
    show_banner
    
    # Run pre-flight checks
    check_root
    check_system
    
    # Confirm with the user
    echo -e "${CYAN}Ready to install OVERKILL Python Configurator?${NC}"
    local REPLY
    read -p "Continue? (y/N): " -n 1 -r REPLY </dev/tty
    echo
    if [[ ! ${REPLY} =~ ^[Yy]$ ]]; then
        error "Installation cancelled"
    fi
    
    # --- Execute the installation as a chain ---
    # The script will stop automatically if any step fails.
    install_dependencies && \
    setup_python_environment && \
    install_overkill && \
    create_launcher
    
    # This success message only runs if the entire chain completes
    echo -e "\n${GREEN}✓ OVERKILL Bootstrap Complete!${NC}"
    echo -e "${CYAN}Run 'sudo overkill' to launch the configuration tool${NC}"
    
    # Launch installer automatically
    echo
    echo -e "${CYAN}Launching OVERKILL installer...${NC}"
    /usr/local/bin/overkill
}

# Run main function
main "$@"