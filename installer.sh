#!/bin/bash

# Function to print messages
print_message() {
    echo -e "\n\033[1;32m$1\033[0m"
}

# Check for sudo privileges
if [ "$(id -u)" -ne 0 ]; then
    echo -e "\033[1;31mThis script must be run with sudo privileges.\033[0m"
    exit 1
fi

print_message "Installing required dependencies..."
apt-get install -y python3 python3-pip git rich

# Install rich for Python
print_message "Installing the rich library..."
pip3 install rich

# Download the installer.py script from GitHub
INSTALLER_URL="https://raw.githubusercontent.com/YOUR_USERNAME/YOUR_REPOSITORY/main/installer.py"  # Replace with your GitHub URL
INSTALLER_FILE="installer.py"

print_message "Downloading installer.py..."
if curl -s -o "$INSTALLER_FILE" "$INSTALLER_URL"; then
    print_message "Downloaded installer.py successfully."
else
    echo -e "\033[1;31mFailed to download installer.py.\033[0m"
    exit 1
fi

# Run the installer.py script
print_message "Running installer.py..."
python3 "$INSTALLER_FILE"

print_message "Installation process completed!"
