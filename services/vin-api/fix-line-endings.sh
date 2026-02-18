#!/bin/bash
# Fix line endings for Windows users
# Run this if you get "not found" errors when running shell scripts

echo "Fixing line endings in shell scripts..."

# Fix all .sh files
find . -name "*.sh" -type f -exec sed -i 's/\r$//' {} \;

echo "✓ Line endings fixed!"
echo "You can now run: docker-compose up -d"
