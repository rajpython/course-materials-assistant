#!/bin/bash

# Format Python code using black and isort
echo "🔧 Formatting Python code with black..."
uv run black .

echo "🔧 Sorting imports with isort..."
uv run isort .

echo "✅ Code formatting complete!"