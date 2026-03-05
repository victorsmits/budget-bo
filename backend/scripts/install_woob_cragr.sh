#!/bin/bash

# Create expected directories
mkdir -p /root/.local/share/woob/modules/3.7

# Try to force module installation
echo "Attempting to install cragr module..."

# Method 1: Use expect to handle interactive prompts (if available)
if command -v expect >/dev/null 2>&1; then
    expect -c "
    spawn woob config add cragr
    expect \"?\"
    send \"\r\"
    expect eof
    "
else
    # Method 2: Try with empty input
    echo "" | woob config add cragr 2>/dev/null || true
    
    # Method 3: Try with specific parameters
    woob config add cragr dummy_backend --params="" 2>/dev/null || true
fi

# Check if module was downloaded
echo "Checking for cragr module..."
find /root -name "cragr" -type d 2>/dev/null

# List modules directory
echo "Contents of modules directory:"
ls -la /root/.local/share/woob/modules/3.7/ 2>/dev/null || echo "Directory not found"
