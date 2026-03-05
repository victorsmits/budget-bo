#!/usr/bin/env python3
"""Script to download woob modules without interactive configuration"""

from woob.core import Woob
import os
import subprocess
import sys

# Create woob instance
w = Woob()

# Update repositories
print("Updating repositories...")
w.repositories.update()

# Try to ensure cragr is available
print("Ensuring cragr module is available...")

# Method 1: Check if already downloaded
modules_path = '/root/.local/share/woob/modules/3.7/woob_modules'
cragr_path = os.path.join(modules_path, 'cragr')

if not os.path.exists(cragr_path):
    print("cragr not found, attempting to download...")
    # Method 2: Try using woob command with a here document
    try:
        subprocess.run(['bash', '-c', 'echo -e "\n\n\n\n\n" | woob config add cragr'], 
                      check=False, capture_output=True)
    except:
        pass

# Verify installation
if os.path.exists(modules_path):
    print(f"Modules available at: {modules_path}")
    if os.path.exists(cragr_path):
        print("cragr module found!")
        sys.exit(0)
    else:
        print("cragr module not found")
        # List what's available
        try:
            modules = os.listdir(modules_path)
            print(f"Available modules: {modules[:5]}...")  # Show first 5
        except:
            pass
        sys.exit(1)
else:
    print("Modules not found")
    sys.exit(1)
