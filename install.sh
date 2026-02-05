#!/bin/bash

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}"
echo "  _     _                  ____           _ "
echo " | |   (_)_ __  _   ___  _|  _ \ __ _  __| |"
echo " | |   | | '_ \| | | \ \/ / |_) / _\` |/ _\` |"
echo " | |___| | | | | |_| |>  <|  __/ (_| | (_| |"
echo " |_____|_|_| |_|\__,_/_/\_\_|   \__,_|\__,_|"
echo -e "${NC}"
echo -e "${GREEN}=== LinuxPad Installer by Ohixx (Dawun) ===${NC}"
echo ""

if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}Error: Don't run as root! Run as normal user.${NC}"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ ! -f "$SCRIPT_DIR/linuxpad.py" ]; then
    echo -e "${RED}Error: linuxpad.py not found in $SCRIPT_DIR${NC}"
    exit 1
fi

install_arch() {
    echo -e "${YELLOW}Installing dependencies for Arch Linux...${NC}"
    sudo pacman -S --needed --noconfirm python python-pyqt6 pipewire pipewire-pulse

    echo -e "${YELLOW}Installing pynput for global hotkeys...${NC}"
    if command -v yay &> /dev/null; then
        yay -S --needed --noconfirm python-pynput 2>/dev/null || pip install --user pynput
    elif command -v paru &> /dev/null; then
        paru -S --needed --noconfirm python-pynput 2>/dev/null || pip install --user pynput
    else
        pip install --user pynput
    fi
}

install_debian() {
    echo -e "${YELLOW}Installing dependencies for Debian/Ubuntu...${NC}"
    sudo apt update
    sudo apt install -y python3 python3-pyqt6 pipewire pipewire-pulse python3-pip
    pip3 install --user pynput --break-system-packages 2>/dev/null || pip3 install --user pynput
}

install_fedora() {
    echo -e "${YELLOW}Installing dependencies for Fedora...${NC}"
    sudo dnf install -y python3 python3-qt6 pipewire pipewire-pulseaudio python3-pip
    pip3 install --user pynput
}

install_opensuse() {
    echo -e "${YELLOW}Installing dependencies for openSUSE...${NC}"
    sudo zypper install -y python3 python3-qt6 pipewire pipewire-pulseaudio python3-pip
    pip3 install --user pynput
}

echo -e "${GREEN}[1/3] Installing dependencies...${NC}"

if command -v pacman &> /dev/null; then
    install_arch
elif command -v apt &> /dev/null; then
    install_debian
elif command -v dnf &> /dev/null; then
    install_fedora
elif command -v zypper &> /dev/null; then
    install_opensuse
else
    echo -e "${RED}Unknown package manager!${NC}"
    echo "Please install manually:"
    echo "  - python3"
    echo "  - python-pyqt6"
    echo "  - pipewire"
    echo "  - python-pynput"
    exit 1
fi

echo ""
echo -e "${GREEN}[2/3] Installing LinuxPad...${NC}"

sudo install -Dm755 "$SCRIPT_DIR/linuxpad.py" /usr/local/bin/linuxpad

sudo tee /usr/share/applications/linuxpad.desktop > /dev/null << 'EOF'
[Desktop Entry]
Name=LinuxPad
Comment=Simple soundboard for Linux
Exec=linuxpad
Icon=audio-card
Terminal=false
Type=Application
Categories=Audio;AudioVideo;
Keywords=sound;soundboard;audio;
EOF

echo ""
echo -e "${GREEN}[3/3] Installation complete!${NC}"
echo ""
echo -e "${BLUE}================================================${NC}"
echo -e "  Run LinuxPad:  ${GREEN}linuxpad${NC}"
echo -e "  Or find it in your application menu"
echo -e "${BLUE}================================================${NC}"
echo ""
echo -e "${YELLOW}IMPORTANT: Virtual Microphone Setup${NC}"
echo ""
echo "To use LinuxPad as a soundboard in Discord/OBS/etc:"
echo ""
echo "1. Run the virtual mic setup script:"
echo -e "   ${GREEN}./setup-virtual-mic.sh${NC}"
echo ""
echo "2. In LinuxPad, click 'Select Device' and choose the virtual sink"
echo ""
echo "3. In Discord/OBS, set your microphone to 'Monitor of LinuxPad Mic'"
echo ""
