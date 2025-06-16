"""
Jpegli integration module for osxphotos

This module provides functions to compress JPEG images using Google's jpegli
library, which offers significant file size reductions compared to standard JPEG.
"""

import os
import subprocess
import shutil
import tempfile
from pathlib import Path
from typing import Optional, Union


class JpegliCompressor:
    """Wrapper class for jpegli compression functionality"""
    
    def __init__(self, cjpegli_path: Optional[str] = None, djpegli_path: Optional[str] = None):
        """
        Initialize JpegliCompressor
        
        Args:
            cjpegli_path: Path to cjpegli binary (encoder)
            djpegli_path: Path to djpegli binary (decoder)
        """
        # Try to find binaries
        if cjpegli_path:
            self.cjpegli_path = cjpegli_path
        else:
            self.cjpegli_path = self._find_binary('cjpegli')
            
        if djpegli_path:
            self.djpegli_path = djpegli_path
        else:
            self.djpegli_path = self._find_binary('djpegli')
        
        # Verify binaries exist
        if not self.cjpegli_path or not os.path.exists(self.cjpegli_path):
            raise FileNotFoundError("cjpegli binary not found")
        if not self.djpegli_path or not os.path.exists(self.djpegli_path):
            raise FileNotFoundError("djpegli binary not found")
    
    def _find_binary(self, name: str) -> Optional[str]:
        """Try to find binary in common locations"""
        # Check if it's in PATH
        which_result = shutil.which(name)
        if which_result:
            return which_result
        
        # Check common locations
        common_paths = [
            f'./{name}',
            f'./jpegli/{name}',
            f'/usr/local/bin/{name}',
            f'/opt/homebrew/bin/{name}',
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                return os.path.abspath(path)
        
        return None
    
    def compress(self, 
                 input_path: Union[str, Path], 
                 output_path: Union[str, Path],
                 quality: int = 85,
                 progressive: bool = False,
                 optimize: bool = True) -> dict:
        """
        Compress an image using jpegli
        
        Args:
            input_path: Path to input image
            output_path: Path to output JPEG
            quality: JPEG quality (1-100, default 85)
            progressive: Create progressive JPEG
            optimize: Optimize Huffman tables
            
        Returns:
            dict: Compression results including file sizes and reduction percentage
        """
        input_path = Path(input_path)
        output_path = Path(output_path)
        
        if not input_path.exists():
            raise FileNotFoundError(f"Input file not found: {input_path}")
        
        # Build command
        cmd = [self.cjpegli_path, str(input_path), str(output_path)]
        
        # Add quality
        cmd.extend(['-q', str(quality)])
        
        # Add optional flags
        if progressive:
            cmd.extend(['-p', '2'])  # Maximum progressive level
        
        # Run compression
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"jpegli compression failed: {e.stderr}")
        
        # Get file sizes
        input_size = input_path.stat().st_size
        output_size = output_path.stat().st_size
        reduction = ((input_size - output_size) / input_size) * 100 if input_size > 0 else 0
        
        return {
            'input_size': input_size,
            'output_size': output_size,
            'reduction_percent': reduction,
            'quality': quality,
            'command': ' '.join(cmd),
            'stdout': result.stdout,
            'stderr': result.stderr
        }
    
    def decode(self, input_path: Union[str, Path], output_path: Union[str, Path]) -> bool:
        """
        Decode a JPEG using djpegli
        
        Args:
            input_path: Path to input JPEG
            output_path: Path to output image
            
        Returns:
            bool: True if successful
        """
        cmd = [self.djpegli_path, str(input_path), str(output_path)]
        
        try:
            subprocess.run(cmd, capture_output=True, check=True)
            return True
        except subprocess.CalledProcessError:
            return False
    
    def compare_with_standard(self, 
                            input_path: Union[str, Path],
                            quality: int = 85) -> dict:
        """
        Compare jpegli compression with standard JPEG
        
        Args:
            input_path: Path to input image
            quality: JPEG quality to test
            
        Returns:
            dict: Comparison results
        """
        from PIL import Image
        
        input_path = Path(input_path)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir = Path(tmpdir)
            
            # Compress with standard JPEG
            standard_path = tmpdir / "standard.jpg"
            img = Image.open(input_path)
            img.save(standard_path, 'JPEG', quality=quality, optimize=True)
            standard_size = standard_path.stat().st_size
            
            # Compress with jpegli
            jpegli_path = tmpdir / "jpegli.jpg"
            jpegli_result = self.compress(input_path, jpegli_path, quality=quality)
            
            # Calculate improvement
            improvement = ((standard_size - jpegli_result['output_size']) / standard_size) * 100
            
            return {
                'standard_size': standard_size,
                'jpegli_size': jpegli_result['output_size'],
                'improvement_percent': improvement,
                'quality': quality
            }


# Quality presets for different use cases
QUALITY_PRESETS = {
    'archival': 95,      # Maximum quality for archival purposes
    'high': 90,          # High quality for professional use
    'standard': 85,      # Standard quality, good balance
    'web': 75,           # Web/sharing quality
    'thumbnail': 60      # Thumbnail quality
}


def integrate_with_osxphotos(photo_path: str, 
                           output_dir: str,
                           quality_preset: str = 'standard') -> str:
    """
    Example integration function for osxphotos
    
    Args:
        photo_path: Path to photo from osxphotos
        output_dir: Directory to save compressed photo
        quality_preset: Quality preset name
        
    Returns:
        str: Path to compressed photo
    """
    quality = QUALITY_PRESETS.get(quality_preset, 85)
    
    # Initialize compressor
    compressor = JpegliCompressor()
    
    # Generate output filename
    input_path = Path(photo_path)
    output_path = Path(output_dir) / f"{input_path.stem}_jpegli_q{quality}.jpg"
    
    # Compress
    result = compressor.compress(input_path, output_path, quality=quality)
    
    print(f"Compressed {input_path.name}:")
    print(f"  Original: {result['input_size']:,} bytes")
    print(f"  Compressed: {result['output_size']:,} bytes")
    print(f"  Reduction: {result['reduction_percent']:.1f}%")
    
    return str(output_path)


if __name__ == "__main__":
    # Example usage
    compressor = JpegliCompressor(
        cjpegli_path="./jpegli/cjpegli",
        djpegli_path="./jpegli/djpegli"
    )
    
    # Test compression
    test_image = "test_image.png"
    if os.path.exists(test_image):
        print("Testing jpegli compression...")
        result = compressor.compress(test_image, "test_output.jpg", quality=85)
        print(f"Compression result: {result['reduction_percent']:.1f}% reduction")
        
        # Compare with standard JPEG
        print("\nComparing with standard JPEG...")
        comparison = compressor.compare_with_standard(test_image, quality=85)
        print(f"Jpegli is {comparison['improvement_percent']:.1f}% smaller than standard JPEG")