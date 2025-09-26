#!/bin/bash

# Run all code quality tools in sequence
echo "🚀 Running comprehensive code quality checks..."

echo "📋 Step 1: Formatting code..."
./scripts/format.sh

echo "📋 Step 2: Running linting and type checks..."
./scripts/lint.sh

echo "📋 Step 3: Running tests..."
cd backend && uv run pytest tests/ && cd ..

echo "🎉 All quality checks complete!"