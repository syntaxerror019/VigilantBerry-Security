#!/bin/bash

SERVICE_NAME="vigiberry.service"
SCRIPT_DIR=$(dirname "$(realpath "$0")")
SCRIPT_PATH="$SCRIPT_DIR/vigiberry.sh"  # Path to your script
USER_NAME=$(whoami)

# ensure the shell script is executable
chmod +x "$SCRIPT_PATH"

# create the systemd service file
echo "[Unit]
Description=Your AIO CCTV Security Camera System!
After=network.target

[Service]
ExecStart=sudo $SCRIPT_PATH
User=$USER_NAME

[Install]
WantedBy=multi-user.target" | sudo tee /etc/systemd/system/$SERVICE_NAME > /dev/null

sudo systemctl daemon-reload
sudo systemctl enable $SERVICE_NAME
sudo systemctl start $SERVICE_NAME

sudo systemctl status $SERVICE_NAME