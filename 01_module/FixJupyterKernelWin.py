import shutil
import sys
from pathlib import Path


def find_kernelapp(venv_dir=".venv"):
    """Locate the kernelapp.py file within the virtual environment."""
    kernelapp_path = Path(venv_dir) / "Lib" / "site-packages" / "ipykernel" / "kernelapp.py"
    if kernelapp_path.exists():
        return kernelapp_path
    else:
        print(f"❌ kernelapp.py not found at: {kernelapp_path}")
        sys.exit(1)


def comment_out_line(file_path, match_phrase):
    """Comment out the line containing the match_phrase in the file."""
    with file_path.open("r", encoding="utf-8") as f:
        content = f.readlines()

    for i, line in enumerate(content):
        if match_phrase in line and not line.strip().startswith("#"):
            content[i] = "# " + line
            with file_path.open("w", encoding="utf-8") as f:
                f.writelines(content)
            print(f"✅ Commented out the line: {line.strip()}")
            return

    print(f"ℹ The line containing '{match_phrase}' is already commented out or not found.")


def main():
    venv_dir = ".venv"
    match_phrase = "asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy"

    kernelapp_path = find_kernelapp(venv_dir)
    print(f"✅ Found kernelapp.py at: {kernelapp_path}")

    # Backup the original file
    backup_path = kernelapp_path.with_suffix(".bak")
    shutil.copy(kernelapp_path, backup_path)
    print(f"🛡 Created backup: {backup_path}")

    comment_out_line(kernelapp_path, match_phrase)


if __name__ == "__main__":
    main()
