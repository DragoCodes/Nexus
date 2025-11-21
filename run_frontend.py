#!/usr/bin/env python3
"""Run the Streamlit frontend for Nexus."""

import subprocess
import sys
from pathlib import Path

if __name__ == "__main__":
    frontend_path = Path(__file__).parent / "frontend" / "app.py"
    
    if not frontend_path.exists():
        print(f"Error: Frontend file not found at {frontend_path}")
        sys.exit(1)
    
    # Run streamlit
    subprocess.run([
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(frontend_path)
    ])

