#!/bin/bash
# CertDeliver Installation Script
# Supports both server and client installation

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
INSTALL_PATH="/opt/CertDeliver"
PYTHON_MIN_VERSION="3.10"

echo -e "${GREEN}"
echo "═══════════════════════════════════════════════════════════════"
echo "                    CertDeliver Installer                       "
echo "              SSL Certificate Delivery Service                  "
echo "═══════════════════════════════════════════════════════════════"
echo -e "${NC}"
echo "Project: https://github.com/yuanweize/CertDeliver"
echo ""

# Function to check Python version
check_python() {
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
        echo -e "${GREEN}✓${NC} Python $PYTHON_VERSION found"
        
        # Check version is >= 3.10
        if python3 -c "import sys; exit(0 if sys.version_info >= (3, 10) else 1)"; then
            return 0
        else
            echo -e "${RED}✗${NC} Python 3.10 or higher is required (found $PYTHON_VERSION)"
            return 1
        fi
    else
        echo -e "${RED}✗${NC} Python3 not found"
        return 1
    fi
}

# Function to install Python
install_python() {
    echo -e "${YELLOW}Installing Python 3...${NC}"
    if [ -f /etc/debian_version ]; then
        apt update && apt -y install python3 python3-pip python3-venv
    elif [ -f /etc/redhat-release ]; then
        yum -y install python3 python3-pip
    else
        echo -e "${RED}Cannot detect OS. Please install Python 3.10+ manually.${NC}"
        exit 1
    fi
}

# Function to create virtual environment
setup_venv() {
    echo -e "${YELLOW}Setting up virtual environment...${NC}"
    python3 -m venv "$INSTALL_PATH/venv"
    source "$INSTALL_PATH/venv/bin/activate"
    pip install --upgrade pip
}

# Function to install CertDeliver
install_certdeliver() {
    echo -e "${YELLOW}Installing CertDeliver...${NC}"
    
    # Install from the current directory or git
    if [ -f "pyproject.toml" ]; then
        pip install .
    else
        pip install git+https://github.com/yuanweize/CertDeliver.git
    fi
    
    echo -e "${GREEN}✓${NC} CertDeliver installed successfully"
}

# Function to setup server
setup_server() {
    echo -e "${YELLOW}Setting up CertDeliver Server...${NC}"
    
    # Create directories
    mkdir -p "$INSTALL_PATH/targets"
    mkdir -p /var/log/certdeliver
    
    # Prompt for configuration
    echo ""
    echo "Please enter your configuration:"
    read -p "API Token: " -s API_TOKEN
    echo ""
    read -p "Allowed domains (comma-separated): " DOMAIN_LIST
    
    # Create .env file
    cat > "$INSTALL_PATH/.env" << EOF
CERTDELIVER_TOKEN=$API_TOKEN
CERTDELIVER_DOMAIN_LIST=$DOMAIN_LIST
CERTDELIVER_TARGETS_DIR=$INSTALL_PATH/targets
EOF
    
    chmod 600 "$INSTALL_PATH/.env"
    
    # Create systemd service
    cat > /etc/systemd/system/certdeliver.service << EOF
[Unit]
Description=CertDeliver Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$INSTALL_PATH
Environment="PATH=$INSTALL_PATH/venv/bin"
EnvironmentFile=$INSTALL_PATH/.env
ExecStart=$INSTALL_PATH/venv/bin/certdeliver-server
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
EOF

    # Enable and start service
    systemctl daemon-reload
    systemctl enable certdeliver
    systemctl start certdeliver
    
    echo -e "${GREEN}✓${NC} Server installed and started"
    echo ""
    systemctl status certdeliver --no-pager
}

# Function to setup client
setup_client() {
    echo -e "${YELLOW}Setting up CertDeliver Client...${NC}"
    
    # Create directories
    mkdir -p /var/cache/certdeliver
    mkdir -p /etc/ssl/certs/certdeliver
    
    # Prompt for configuration
    echo ""
    echo "Please enter your configuration:"
    read -p "Server URL (e.g., https://cert.example.com/api/v1/): " SERVER_URL
    read -p "API Token: " -s API_TOKEN
    echo ""
    read -p "Certificate name: " CERT_NAME
    read -p "Destination path: " CERT_DEST_PATH
    read -p "Post-update command (optional, press Enter to skip): " POST_CMD
    
    # Create .env file
    cat > "$INSTALL_PATH/.env" << EOF
CERTDELIVER_CLIENT_SERVER_URL=$SERVER_URL
CERTDELIVER_CLIENT_TOKEN=$API_TOKEN
CERTDELIVER_CLIENT_CERT_NAME=$CERT_NAME
CERTDELIVER_CLIENT_CERT_DEST_PATH=$CERT_DEST_PATH
CERTDELIVER_CLIENT_LOCAL_CACHE_DIR=/var/cache/certdeliver
CERTDELIVER_CLIENT_POST_UPDATE_COMMAND=$POST_CMD
EOF
    
    chmod 600 "$INSTALL_PATH/.env"
    
    # Setup cron job
    CRON_CMD="30 6,18 * * * cd $INSTALL_PATH && source venv/bin/activate && certdeliver-client >> /var/log/certdeliver/client.log 2>&1"
    (crontab -l 2>/dev/null | grep -v certdeliver; echo "$CRON_CMD") | crontab -
    
    echo -e "${GREEN}✓${NC} Client installed"
    echo "Cron job added: Runs at 06:30 and 18:30 daily"
}

# Function to setup certbot hook
setup_hook() {
    echo -e "${YELLOW}Setting up Certbot Hook...${NC}"
    
    # Create symlink for hook
    ln -sf "$INSTALL_PATH/venv/bin/certdeliver-hook" /usr/local/bin/certdeliver-hook
    
    echo ""
    echo "Add this to your certbot renewal command:"
    echo -e "${GREEN}certbot renew --post-hook '/usr/local/bin/certdeliver-hook'${NC}"
    echo ""
    echo "Or add to crontab:"
    echo -e "${GREEN}0 0,12 * * * certbot renew -q --post-hook '/usr/local/bin/certdeliver-hook'${NC}"
}

# Main installation flow
main() {
    # Check if running as root
    if [ "$EUID" -ne 0 ]; then
        echo -e "${RED}Please run as root${NC}"
        exit 1
    fi
    
    # Check Python
    if ! check_python; then
        install_python
    fi
    
    # Create install directory
    mkdir -p "$INSTALL_PATH"
    cd "$INSTALL_PATH"
    
    # Setup virtual environment
    setup_venv
    
    # Install CertDeliver
    install_certdeliver
    
    # Ask what to install
    echo ""
    echo "What would you like to install?"
    echo "  1) Server (certificate distribution server)"
    echo "  2) Client (certificate downloader)"
    echo "  3) Certbot Hook (certificate packager)"
    echo "  4) All components"
    echo ""
    read -p "Enter choice [1-4]: " CHOICE
    
    case $CHOICE in
        1) setup_server ;;
        2) setup_client ;;
        3) setup_hook ;;
        4)
            setup_server
            setup_hook
            ;;
        *)
            echo -e "${RED}Invalid choice${NC}"
            exit 1
            ;;
    esac
    
    echo ""
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}                   Installation Complete!                       ${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo "Installation path: $INSTALL_PATH"
    echo "Configuration: $INSTALL_PATH/.env"
    echo ""
    echo "Commands available:"
    echo "  certdeliver-server  - Start the server"
    echo "  certdeliver-client  - Run the client"
    echo "  certdeliver-hook    - Run certbot hook"
    echo ""
}

main "$@"
