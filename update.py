import subprocess
import argparse

def fetch_updates():
    """Fetch updates from the remote repository."""
    subprocess.run(["git", "fetch", "origin", "main"], check=True)

def get_changelog():
    """Get the changelog of new commits."""
    result = subprocess.run(
        ["git", "log", "HEAD..origin/main", "--pretty=format:%h - %s (%an, %ar)"],
        capture_output=True,
        text=True,
        check=True
    )
    return result.stdout if result.stdout else "No new updates available."

def save_changelog_to_file(changelog):
    """Save the changelog to a file."""
    with open("changelog.txt", "w") as file:
        file.write(changelog)

def apply_updates():
    """Apply the updates by resetting the local branch."""
    subprocess.run(["git", "reset", "--hard", "origin/main"], check=True)

def main(apply):
    fetch_updates()
    changelog = get_changelog()

    print("Changelog:")
    print(changelog)

    if changelog != "No new updates available.":
        save_changelog_to_file(changelog)
        if apply:
            apply_updates()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Update script")
    parser.add_argument('--apply', action='store_true', help='Apply the updates')
    args = parser.parse_args()
    print("HEY!")
    main(args.apply)
