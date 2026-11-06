"""Opens a file with the system's default application."""


import os
import subprocess
import sys

import input_output_manager
from .config import XLSX_FILE


def open_file(filename=XLSX_FILE):
    """Opens a file with the system's default application."""
    if not os.path.exists(filename):
        input_output_manager.print_output(
            f"'{filename}' not found. Type 'export xlsx' first to create it.")
        return False
    try:
        if sys.platform.startswith("win"):
            os.startfile(filename)
        elif sys.platform == "darwin":
            subprocess.run(["open", filename], check=True)
        else:
            subprocess.run(["xdg-open", filename], check=True)
    except (OSError, subprocess.CalledProcessError) as e:
        input_output_manager.print_output(f"Could not open '{filename}': {e}")
        return False
    input_output_manager.print_output(f"Opening '{filename}'...")
    return True
