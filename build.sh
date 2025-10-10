#!/bin/bash

# Render.com build script for OCR dependencies

echo "🔧 Installing Tesseract OCR dependencies..."

# Update package list
apt-get update

# Install Tesseract OCR with language packs
apt-get install -y tesseract-ocr tesseract-ocr-chi-sim tesseract-ocr-eng

# Verify installation
echo "📋 Tesseract version:"
tesseract --version

echo "🌍 Available languages:"
tesseract --list-langs

# Install Python dependencies
echo "🐍 Installing Python dependencies..."
pip install -r requirements.txt

echo "✅ Build completed successfully!"