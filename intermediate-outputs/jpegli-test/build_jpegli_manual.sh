#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Manual Jpegli Build Script ===${NC}"

# Set up environment
export PATH="/usr/local/opt/llvm/bin:$PATH"
export CMAKE_PREFIX_PATH=$(brew --prefix giflib):$(brew --prefix jpeg-turbo):$(brew --prefix libpng):$(brew --prefix zlib)
export CC=clang
export CXX=clang++

cd /Users/ochafik/github/osxphotos/intermediate-outputs/jpegli-test/jpegli

# Clean build directory
if [ -d "build" ]; then
    rm -rf build
fi
mkdir build
cd build

echo -e "${YELLOW}Configuring with CMake...${NC}"
# Use simpler CMake configuration to avoid the policy errors
cmake .. \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_C_COMPILER=clang \
    -DCMAKE_CXX_COMPILER=clang++ \
    -DJPEGXL_ENABLE_FUZZERS=OFF \
    -DJPEGXL_ENABLE_VIEWERS=OFF \
    -DJPEGXL_ENABLE_BENCHMARK=OFF \
    -DJPEGXL_ENABLE_PLUGINS=OFF \
    -DJPEGXL_ENABLE_DEVTOOLS=OFF \
    -DJPEGXL_WARNINGS_AS_ERRORS=OFF \
    -DBUILD_TESTING=OFF \
    -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
    -GNinja

echo -e "${YELLOW}Building jpegli...${NC}"
ninja cjpegli djpegli

echo -e "${GREEN}Build completed!${NC}"
echo "Binaries location:"
ls -la tools/cjpegli tools/djpegli

# Copy binaries to parent directory for easier access
cp tools/cjpegli ../cjpegli
cp tools/djpegli ../djpegli

echo -e "${GREEN}Binaries copied to jpegli directory${NC}"