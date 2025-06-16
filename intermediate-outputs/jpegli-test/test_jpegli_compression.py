#!/usr/bin/env python3
"""
Test script to demonstrate jpegli compression improvements
"""

import os
import subprocess
import tempfile
from PIL import Image
import numpy as np

def create_test_image(filename, size=(800, 600)):
    """Create a test image with gradients and text"""
    width, height = size
    
    # Create gradient image
    img = Image.new('RGB', (width, height))
    pixels = img.load()
    
    for y in range(height):
        for x in range(width):
            r = int((x / width) * 255)
            g = int((y / height) * 255)
            b = int((1 - x / width) * (1 - y / height) * 255)
            pixels[x, y] = (r, g, b)
    
    # Save as PNG
    img.save(filename, 'PNG')
    return filename

def get_file_size(filepath):
    """Get file size in bytes"""
    return os.path.getsize(filepath)

def compress_with_jpegli(input_path, output_path, quality=85):
    """Compress image using jpegli"""
    cmd = ['./jpegli/cjpegli', input_path, output_path, '-q', str(quality)]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"jpegli error: {result.stderr}")
        return False
    return True

def compress_with_standard_jpeg(input_path, output_path, quality=85):
    """Compress image using standard JPEG (via Pillow)"""
    img = Image.open(input_path)
    img.save(output_path, 'JPEG', quality=quality, optimize=True)
    return True

def main():
    """Run compression tests"""
    # Create test directory
    test_dir = "/Users/ochafik/github/osxphotos/intermediate-outputs/jpegli-test"
    os.chdir(test_dir)
    
    # Create test image
    print("Creating test image...")
    test_png = "test_image.png"
    create_test_image(test_png)
    png_size = get_file_size(test_png)
    print(f"Original PNG size: {png_size:,} bytes")
    
    # Test different quality levels
    quality_levels = [75, 85, 95]
    results = []
    
    print("\nTesting compression at different quality levels:")
    print("-" * 60)
    print(f"{'Quality':<10} {'Standard JPEG':<20} {'Jpegli':<20} {'Reduction':<10}")
    print("-" * 60)
    
    for quality in quality_levels:
        # Standard JPEG
        standard_jpg = f"test_standard_q{quality}.jpg"
        compress_with_standard_jpeg(test_png, standard_jpg, quality)
        standard_size = get_file_size(standard_jpg)
        
        # Jpegli
        jpegli_jpg = f"test_jpegli_q{quality}.jpg"
        if compress_with_jpegli(test_png, jpegli_jpg, quality):
            jpegli_size = get_file_size(jpegli_jpg)
            
            # Calculate reduction
            reduction = ((standard_size - jpegli_size) / standard_size) * 100
            
            print(f"{quality:<10} {standard_size:>15,} B {jpegli_size:>15,} B {reduction:>8.1f}%")
            
            results.append({
                'quality': quality,
                'standard_size': standard_size,
                'jpegli_size': jpegli_size,
                'reduction': reduction
            })
    
    print("-" * 60)
    
    # Write detailed report
    with open('compression_results.txt', 'w') as f:
        f.write("# Jpegli Compression Test Results\n\n")
        f.write("## Test Setup\n")
        f.write(f"- Test image: {test_png} (800x600 gradient)\n")
        f.write(f"- Original PNG size: {png_size:,} bytes\n")
        f.write(f"- Quality levels tested: {', '.join(map(str, quality_levels))}\n\n")
        
        f.write("## Results\n\n")
        f.write("| Quality | Standard JPEG (bytes) | Jpegli (bytes) | Size Reduction |\n")
        f.write("|---------|----------------------|----------------|----------------|\n")
        
        for r in results:
            f.write(f"| {r['quality']} | {r['standard_size']:,} | {r['jpegli_size']:,} | {r['reduction']:.1f}% |\n")
        
        avg_reduction = sum(r['reduction'] for r in results) / len(results)
        f.write(f"\n**Average size reduction: {avg_reduction:.1f}%**\n")
        
        f.write("\n## Integration Recommendations for osxphotos\n\n")
        f.write("1. **Build Configuration**:\n")
        f.write("   - Use static linking to avoid runtime dependencies\n")
        f.write("   - Consider building universal binary for Intel/ARM support\n")
        f.write("   - Bundle pre-built binaries with osxphotos\n\n")
        
        f.write("2. **Python Integration Options**:\n")
        f.write("   - Option 1: Use subprocess to call jpegli binaries\n")
        f.write("   - Option 2: Create Python bindings using ctypes\n")
        f.write("   - Option 3: Use cython to wrap the C++ library\n\n")
        
        f.write("3. **Recommended Implementation**:\n")
        f.write("   ```python\n")
        f.write("   def export_with_jpegli(image_path, output_path, quality=85):\n")
        f.write("       \"\"\"Export image using jpegli for better compression\"\"\"\n")
        f.write("       cmd = ['cjpegli', image_path, output_path, '-q', str(quality)]\n")
        f.write("       subprocess.run(cmd, check=True)\n")
        f.write("   ```\n\n")
        
        f.write("4. **Quality Presets**:\n")
        f.write("   - High quality (archival): 95\n")
        f.write("   - Standard quality: 85\n")
        f.write("   - Web/sharing: 75\n")
    
    print(f"\nDetailed report saved to: compression_results.txt")

if __name__ == "__main__":
    main()