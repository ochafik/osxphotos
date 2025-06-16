#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== Jpegli Build and Test Script ===${NC}"

# Set up environment
export PATH="/usr/local/opt/llvm/bin:$PATH"
export CMAKE_PREFIX_PATH=$(brew --prefix giflib):$(brew --prefix jpeg-turbo):$(brew --prefix libpng):$(brew --prefix zlib)
export CC=clang
export CXX=clang++

# Check if we're in the right directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Step 1: Build jpegli
echo -e "\n${YELLOW}Step 1: Building jpegli...${NC}"
if [ ! -d "jpegli" ]; then
    echo "jpegli directory not found. Please clone it first."
    exit 1
fi

cd jpegli

# Clean previous builds
if [ -d "build" ]; then
    echo "Cleaning previous build..."
    rm -rf build
fi

# Build using ci.sh with minimal tests to speed up
echo "Building jpegli..."
SKIP_TEST=1 ./ci.sh release

# Check if build succeeded
if [ ! -f "build/tools/cjpegli" ] || [ ! -f "build/tools/djpegli" ]; then
    echo -e "${RED}Build failed! Encoder/decoder binaries not found.${NC}"
    exit 1
fi

echo -e "${GREEN}Build successful!${NC}"

# Step 2: Create test image
echo -e "\n${YELLOW}Step 2: Creating test image...${NC}"
cd "$SCRIPT_DIR"

# Create a simple test image using ImageMagick if available, otherwise use a placeholder
if command -v convert &> /dev/null; then
    echo "Creating test image with ImageMagick..."
    convert -size 800x600 \
        gradient:blue-yellow \
        -swirl 180 \
        -font Arial -pointsize 72 -gravity center \
        -annotate +0+0 'Jpegli Test' \
        test_original.png
else
    echo "ImageMagick not found. Creating test image with Python..."
    python3 << 'EOF'
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# Create gradient image
width, height = 800, 600
img = Image.new('RGB', (width, height))
pixels = img.load()

for y in range(height):
    for x in range(width):
        r = int((x / width) * 255)
        g = int((y / height) * 255)
        b = int((1 - x / width) * (1 - y / height) * 255)
        pixels[x, y] = (r, g, b)

# Add text
draw = ImageDraw.Draw(img)
text = "Jpegli Test"
# Use default font if system font not available
try:
    font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 60)
except:
    font = ImageFont.load_default()
    
# Get text bbox for centering
bbox = draw.textbbox((0, 0), text, font=font)
text_width = bbox[2] - bbox[0]
text_height = bbox[3] - bbox[1]
x = (width - text_width) // 2
y = (height - text_height) // 2
draw.text((x, y), text, fill=(255, 255, 255), font=font)

img.save('test_original.png')
print("Test image created successfully")
EOF
fi

# Step 3: Test compression
echo -e "\n${YELLOW}Step 3: Testing jpegli compression...${NC}"

# Define quality levels to test
QUALITIES=(75 85 95)

echo -e "\nOriginal PNG size:"
ls -lh test_original.png

for Q in "${QUALITIES[@]}"; do
    echo -e "\n${GREEN}Testing quality $Q:${NC}"
    
    # Encode with jpegli
    ./jpegli/build/tools/cjpegli test_original.png test_jpegli_q${Q}.jpg -q $Q
    
    # Encode with standard JPEG for comparison (using cjpeg from jpeg-turbo)
    if command -v cjpeg &> /dev/null; then
        cjpeg -quality $Q -outfile test_standard_q${Q}.jpg test_original.png
    fi
    
    # Show file sizes
    echo "Jpegli output:"
    ls -lh test_jpegli_q${Q}.jpg
    
    if [ -f "test_standard_q${Q}.jpg" ]; then
        echo "Standard JPEG output:"
        ls -lh test_standard_q${Q}.jpg
        
        # Calculate size difference
        JPEGLI_SIZE=$(stat -f%z test_jpegli_q${Q}.jpg)
        STANDARD_SIZE=$(stat -f%z test_standard_q${Q}.jpg)
        REDUCTION=$(echo "scale=2; 100 - ($JPEGLI_SIZE * 100 / $STANDARD_SIZE)" | bc)
        echo -e "${GREEN}Size reduction: ${REDUCTION}%${NC}"
    fi
    
    # Decode with jpegli to verify
    ./jpegli/build/tools/djpegli test_jpegli_q${Q}.jpg test_decoded_q${Q}.png
    echo "Decoded successfully to test_decoded_q${Q}.png"
done

# Step 4: Create comparison report
echo -e "\n${YELLOW}Step 4: Creating comparison report...${NC}"

cat > compression_report.txt << 'EOF'
# Jpegli Compression Test Results

## Test Setup
- Test image: 800x600 gradient with text
- Tested quality levels: 75, 85, 95
- Compared against standard JPEG (jpeg-turbo)

## Results Summary
EOF

echo "" >> compression_report.txt
echo "| Quality | Jpegli Size | Standard Size | Reduction |" >> compression_report.txt
echo "|---------|-------------|---------------|-----------|" >> compression_report.txt

for Q in "${QUALITIES[@]}"; do
    if [ -f "test_jpegli_q${Q}.jpg" ] && [ -f "test_standard_q${Q}.jpg" ]; then
        JPEGLI_SIZE=$(stat -f%z test_jpegli_q${Q}.jpg)
        STANDARD_SIZE=$(stat -f%z test_standard_q${Q}.jpg)
        REDUCTION=$(echo "scale=2; 100 - ($JPEGLI_SIZE * 100 / $STANDARD_SIZE)" | bc)
        
        JPEGLI_SIZE_H=$(ls -lh test_jpegli_q${Q}.jpg | awk '{print $5}')
        STANDARD_SIZE_H=$(ls -lh test_standard_q${Q}.jpg | awk '{print $5}')
        
        echo "| $Q | $JPEGLI_SIZE_H | $STANDARD_SIZE_H | ${REDUCTION}% |" >> compression_report.txt
    fi
done

echo -e "\n${GREEN}Test completed! Check compression_report.txt for results.${NC}"

# Step 5: Integration considerations
cat >> compression_report.txt << 'EOF'

## Integration Considerations for osxphotos

1. **Library Integration Options:**
   - Use as drop-in replacement for libjpeg
   - Link statically to avoid runtime dependencies
   - Create Python bindings using ctypes or cython

2. **Performance Benefits:**
   - Up to 35% file size reduction at high quality
   - Maintains full JPEG compatibility
   - Better handling of gradients and smooth areas

3. **Potential Challenges:**
   - macOS has "best effort" support
   - May need custom build flags for universal binaries
   - Consider bundling pre-built binaries

4. **Recommended Implementation:**
   - Create a Python wrapper module
   - Offer jpegli as an optional compression backend
   - Provide quality presets optimized for photos
EOF

echo -e "\n${GREEN}All tests completed successfully!${NC}"