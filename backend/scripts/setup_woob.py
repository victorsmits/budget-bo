#!/usr/bin/env python3
"""
Setup script to install required woob modules
"""

from woob.core import Woob
import sys
import os

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
    
    # Verify modules are accessible
    print("Verifying module installation...")
    try:
        # Check if we can import the module
        from woob_modules.cragr.module import CreditAgricoleModule
        print("✓ CreditAgricoleModule is accessible")
    except ImportError as e:
        print(f"✗ Cannot import CreditAgricoleModule: {e}")
        # Try alternative import paths
        try:
            # Check woob modules directory
            woob_modules_path = "/root/.local/share/woob/modules/3.7"
            if os.path.exists(woob_modules_path):
                sys.path.insert(0, woob_modules_path)
                from woob_modules.cragr.module import CreditAgricoleModule
                print("✓ CreditAgricoleModule is accessible after path adjustment")
            else:
                print(f"✗ Woob modules directory not found: {woob_modules_path}")
                sys.exit(1)
        except ImportError as e2:
            print(f"✗ Still cannot import CreditAgricoleModule: {e2}")
            sys.exit(1)
    
    print("All modules installed successfully!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
