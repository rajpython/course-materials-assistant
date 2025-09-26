#!/bin/bash

# Run code quality checks
echo "🔍 Running flake8 linting..."
uv run flake8 .

echo "🔍 Running mypy type checking..."
uv run mypy .

echo "✅ Code quality checks complete!"