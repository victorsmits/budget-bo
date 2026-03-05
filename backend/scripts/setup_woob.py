#!/usr/bin/env python3
"""
Setup script to install required woob modules
"""

from woob.core import Woob
import sys

def main():
    print("Setting up Woob modules...")
    
    # Create woob instance
    w = Woob()
    
    # Update repositories
    print("Updating repositories...")
    w.repositories.update()
    
    # Install required modules
    modules_to_install = ['cragr']
    
    for module in modules_to_install:
        print(f"Installing {module}...")
        try:
            w.repositories.install(module)
            print(f"✓ {module} installed successfully")
        except Exception as e:
            print(f"✗ Failed to install {module}: {e}")
            sys.exit(1)
    
    print("All modules installed successfully!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
