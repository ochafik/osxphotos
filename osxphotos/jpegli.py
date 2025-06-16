"""Jpegli integration for osxphotos"""

import os
import pathlib
import platform
import subprocess
import tempfile
from typing import Optional

from .platform import is_macos

__all__ = ["JpegliEncoder", "JpegliError"]


class JpegliError(Exception):
    """Error during jpegli encoding"""
    pass


class JpegliEncoder:
    """Encode JPEG files using jpegli"""
    
    def __init__(self):
        self._jpegli_path = self._get_jpegli_path()
        if not self._jpegli_path or not os.path.exists(self._jpegli_path):
            raise JpegliError("jpegli binary not found")
    
    def _get_jpegli_path(self) -> Optional[str]:
        """Get path to jpegli binary"""
        if not is_macos:
            return None
        
        # Determine architecture
        arch = platform.machine()
        if arch == "arm64":
            binary_name = "cjpegli_arm64"
        elif arch == "x86_64":
            binary_name = "cjpegli_x86_64"
        else:
            return None
        
        # Look for binary in resources directory
        binary_path = os.path.join(
            os.path.dirname(__file__), "resources", "bin", binary_name
        )
        if os.path.exists(binary_path):
            # Ensure it's executable
            os.chmod(binary_path, 0o755)
            return binary_path
        
        return None
    
    def encode(self, input_path: str, output_path: str, quality: int = 85) -> bool:
        """
        Encode a JPEG file using jpegli
        
        Args:
            input_path: Path to input JPEG file
            output_path: Path to output JPEG file
            quality: JPEG quality (1-100), default 85
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            JpegliError if encoding fails
        """
        if not self._jpegli_path:
            raise JpegliError("jpegli not available on this platform")
        
        # Validate inputs
        input_path = str(pathlib.Path(input_path).resolve())
        output_path = str(pathlib.Path(output_path).resolve())
        
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input file not found: {input_path}")
        
        if not 1 <= quality <= 100:
            raise ValueError(f"Quality must be between 1 and 100, got {quality}")
        
        # Build command
        cmd = [
            self._jpegli_path,
            input_path,
            output_path,
            "-q", str(quality)
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True
            )
            return True
        except subprocess.CalledProcessError as e:
            raise JpegliError(f"jpegli encoding failed: {e.stderr}")