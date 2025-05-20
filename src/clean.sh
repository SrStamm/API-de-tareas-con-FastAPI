#! /bin/bash
find . -type d -name "__pycache__" -exec rm -r {} + && rm -rf .pytest_cache
echo "Eliminado cache de tests"