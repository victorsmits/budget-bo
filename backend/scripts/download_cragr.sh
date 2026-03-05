#!/bin/bash

set -e

echo "Setting up directories..."
mkdir -p /root/.local/share/woob/modules/3.7/woob_modules

echo "Downloading cragr module directly..."
# Get the modules list to find the URL
cd /tmp
wget -q https://updates.woob.tech/3/main/modules.list -O modules.list

# Find cragr entry
CRAGR_URL=$(grep "^cragr|" modules.list | cut -d'|' -f2)

if [ -n "$CRAGR_URL" ]; then
    echo "Found cragr at: $CRAGR_URL"
    echo "Downloading..."
    wget -q "$CRAGR_URL" -O cragr.tar.bz2
    
    echo "Extracting..."
    cd /root/.local/share/woob/modules/3.7/woob_modules
    tar -xjf /tmp/cragr.tar.bz2
    
    echo "Verifying installation..."
    if [ -d "cragr" ]; then
        echo "cragr module installed successfully!"
        ls -la cragr/
    else
        echo "Failed to extract cragr module"
        exit 1
    fi
else
    echo "cragr not found in modules list"
    exit 1
fi
