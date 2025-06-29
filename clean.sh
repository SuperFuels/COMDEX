#!/bin/bash
echo "🧹 Cleaning up disk space..."

rm -rf venv
rm -rf frontend/node_modules
rm -rf frontend/out
find . -name "__pycache__" -exec rm -rf {} +
find . -name "*.pyc" -delete
rm -f *.log *.json *.txt

echo "✅ Cleanup complete!"
