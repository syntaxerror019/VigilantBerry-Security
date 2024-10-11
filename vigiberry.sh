#!/bin/bash

if ! source venv/bin/activate; then
	echo "Failed to activate virtual environment. Have you run the installer script?"
	exit 1
fi

python3 main.py

deactivate