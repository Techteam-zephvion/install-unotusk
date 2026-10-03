#!/bin/bash
set -e

echo "======================================"
echo " Building Unotusk Flutter Web Client  "
echo "======================================"

# 1. Download Flutter stable
echo "Cloning Flutter..."
git clone https://github.com/flutter/flutter.git -b stable --depth 1

# 2. Add to PATH
export PATH="$PATH:`pwd`/flutter/bin"

# 3. Check flutter
flutter doctor -v

# 4. Build the app
cd app
echo "Enabling Web..."
flutter config --enable-web
echo "Building Web Release..."
flutter build web --release

echo "Build complete! Web artifacts are in app/build/web"
