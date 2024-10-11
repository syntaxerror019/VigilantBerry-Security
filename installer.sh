#!/bin/bash

# Function to print messages
print_message() {
    echo -e "\n\033[1;32m$1\033[0m"
}

print_message "--- START OF INSTALLER.SH ---"

# Check for sudo privileges
if [ "$(id -u)" -ne 0 ]; then
    echo -e "\033[1;31mThis script must be run with sudo privileges.\033[0m"
    exit 1
fi

print_message "Installing required dependencies..."
apt-get install -y python3 python3-pip git

# Install rich for Python
print_message "Installing the rich library..."
pip3 install rich

# Run the installer.py script
print_message "Running installer.py..."
python3 installer.py

print_message "--- END OF INSTALLER.SH ---"
