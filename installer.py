import subprocess
import time
import sys
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
import os

# Set up the console
console = Console()


def update_apt():
    # Start the apt update process
    process = subprocess.Popen(
        ["sudo", "apt-get", "update"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        universal_newlines=True
    )

    # Create a progress bar
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold green]Updating packages...[/bold green]"),
        BarColumn(),
    ) as progress:
        task = progress.add_task("Running...", total=100)

        while True:
            # Read output line by line
            output = process.stdout.readline()
            if output == "" and process.poll() is not None:
                break
            if output:
                # Update the progress bar based on the output
                console.log(output.strip())  # Print the output
                progress.update(task, advance=1)

            time.sleep(0.1)  # Simulate some delay for the progress bar

    # Capture any errors
    _, errors = process.communicate()
    if errors:
        console.print(f"[bold red]Error:[/bold red] {errors.strip()}")

def upgrade_apt():
    # Start the apt update process
    process = subprocess.Popen(
        ["sudo", "apt-get", "upgrade", "-y"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        universal_newlines=True
    )

    # Create a progress bar
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold green]Updating packages...[/bold green]"),
        BarColumn(),
    ) as progress:
        task = progress.add_task("Running...", total=100)

        while True:
            # Read output line by line
            output = process.stdout.readline()
            if output == "" and process.poll() is not None:
                break
            if output:
                # Update the progress bar based on the output
                console.log(output.strip())  # Print the output
                progress.update(task, advance=1)

            time.sleep(0.1)  # Simulate some delay for the progress bar

    # Capture any errors
    _, errors = process.communicate()
    if errors:
        console.print(f"[bold red]Error:[/bold red] {errors.strip()}")

def run_command(command, progress_message, total=100):
    """Run a command with a progress bar."""
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        universal_newlines=True
    )

    # Create a progress bar
    with Progress(
        SpinnerColumn(),
        TextColumn(progress_message),
        BarColumn(),
    ) as progress:
        task = progress.add_task("Running...", total=total)

        while True:
            output = process.stdout.readline()
            if output == "" and process.poll() is not None:
                break
            if output:
                console.log(output.strip())
                progress.update(task, advance=1)

            time.sleep(0.1)

    _, errors = process.communicate()
    if errors:
        console.print(f"[bold red]Error:[/bold red] {errors.strip()}")

def check_python_installed():
    """Check if Python is installed."""
    try:
        subprocess.run(["python3", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return True
    except subprocess.CalledProcessError:
        return False

def install_dependencies():
    """Install necessary dependencies."""
    dependencies = [
        "build-essential",
        "cmake",
        "git",
        "libgtk2.0-dev",
        "pkg-config",
        "libavcodec-dev",
        "libavformat-dev",
        "libswscale-dev",
        "python3-dev",
        "python3-pip"
    ]
    command = ["sudo", "apt-get", "install", "-y"] + dependencies
    run_command(command, "Installing dependencies...")

def create_virtualenv():
    """Create a virtual environment."""
    if not os.path.exists('venv'):
        run_command(["python3", "-m", "venv", "venv"], "Creating virtual environment...")
        console.print("[bold green]Virtual environment created![/bold green]")

def install_python_packages():
    """Install necessary Python packages."""
    packages = [
        "numpy",
        "opencv-python-headless"
    ]
    run_command(["venv/bin/pip", "install"] + packages, "Installing Python packages...")

def test_opencv():
    """Test if OpenCV is working correctly."""
    test_script = """
import cv2
import numpy as np

# Create a black image
image = np.zeros((512, 512, 3), np.uint8)

# Draw a white circle
cv2.circle(image, (256, 256), 100, (255, 255, 255), -1)

# Save the image
cv2.imwrite('test_image.png', image)

print("OpenCV is working! Check 'test_image.png'.")
"""
    # Run the test script
    with open("test_opencv.py", "w") as f:
        f.write(test_script)
    
    result = subprocess.run(["venv/bin/python", "test_opencv.py"], capture_output=True, text=True)
    console.print(result.stdout)
    console.print(f"[bold green]OpenCV test script executed! Image saved as 'test_image.png'.[/bold green]")

# Clear the console
console.clear()

console.print("[white][bold]VigilantBerry[/bold] - v3 - 2024[/white], [yellow]Miles Hilliard[/yellow], All Rights Reserved | [cyan][underline]https://mileshilliard.com[/underline][/cyan]", style="")
console.print()
console.print("Installing your software... Please wait...", style="bold")
console.print()

# Check for sudo privileges
if os.geteuid() != 0:
    console.print("[bold red]This script must be run with sudo privileges.[/bold red]")
    sys.exit(1)

# Check if Python is installed
if not check_python_installed():
    console.print("[bold red]Python is not installed. Please install Python 3 and try again.[/bold red]")
    sys.exit(1)

# Run apt update and upgrade with progress bars
console.print("Updating apt...", style="bold")
update_apt()

console.print("\n[bold]Apt update complete![/bold]\n")
console.print("Upgrading packages...", style="bold")
upgrade_apt()

console.print("\n[bold]Apt upgrade complete![/bold]\n")
console.print("Installing Dependencies...", style="bold")
install_dependencies()

console.print("\n[bold]Dependencies installation complete![/bold]\n")
console.print("Creating virtual environment...", style="bold")
create_virtualenv()

console.print("\n[bold]Virtual environment setup complete![/bold]\n")
console.print("Installing Python packages...", style="bold")
install_python_packages()

console.print("\n[bold]Python packages installation complete![/bold]\n")
console.print("Testing OpenCV installation...", style="bold")
test_opencv()

console.print("\n### All installations complete! ###", style="bold green")
