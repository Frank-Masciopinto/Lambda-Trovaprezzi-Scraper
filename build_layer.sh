#!/bin/bash

# Create the directory structure
mkdir -p dependencies/python/lib/python3.8/site-packages

# Install dependencies into the layer directory
pip install -r requirements.txt -t dependencies/python/lib/python3.8/site-packages/

# Clean up unnecessary files
find dependencies/python/lib/python3.8/site-packages/ -type d -name "__pycache__" -exec rm -rf {} +
find dependencies/python/lib/python3.8/site-packages/ -type f -name "*.pyc" -delete 