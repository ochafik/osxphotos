# Jpegli Integration Implementation Plan for osxphotos

## Overview
This document outlines the implementation plan for integrating jpegli reencoding into osxphotos. The feature will work when both `--convert-to-jpeg` and `--jpegli-reencode` flags are set, affecting both existing JPEGs and newly converted JPEGs.

## Architecture Analysis

### Current JPEG Conversion Flow
1. **Command Line Interface**: 
   - `osxphotos/cli/export.py` defines the `--convert-to-jpeg` option
   - Options are passed through `ExportOptions` dataclass

2. **Export Pipeline**:
   - `PhotoExporter.export()` in `osxphotos/photoexporter.py` handles the main export logic
   - `_should_convert_to_jpeg()` determines if conversion is needed
   - Actual conversion happens around line 986 using `fileutil.convert_to_jpeg()`

3. **Image Conversion**:
   - `FileUtil.convert_to_jpeg()` in `osxphotos/fileutil.py` delegates to `ImageConverter`
   - `ImageConverter` in `osxphotos/imageconverter.py` uses CoreImage for conversion

### Key Integration Points
1. **After JPEG Conversion**: Hook into the export pipeline after `convert_to_jpeg` completes
2. **For Existing JPEGs**: Process JPEGs that don't need conversion but still require jpegli reencoding
3. **Temporary File Management**: Use existing temp directory infrastructure

## Implementation Design

### 1. Command Line Flag Addition

**File**: `osxphotos/cli/export.py`

Add new option after `--convert-to-jpeg` (around line 330):
```python
@click.option(
    "--jpegli-reencode",
    is_flag=True,
    help="Re-encode JPEG files using jpegli for better compression. "
    "Requires --convert-to-jpeg to be set. This will re-encode all JPEGs "
    "(both existing and newly converted) using Google's jpegli encoder "
    "for improved compression while maintaining quality.",
)
```

Add parameter to export function signature (around line 1147):
```python
def export(
    ...
    convert_to_jpeg: bool = False,
    jpegli_reencode: bool = False,  # Add this
    ...
):
```

### 2. Option Validation

**File**: `osxphotos/cli/export.py`

Add validation in the `incompatible_options` list (around line 1608):
```python
incompatible_options = [
    ...
    ("jpegli_reencode", ("convert_to_jpeg",)),  # jpegli_reencode requires convert_to_jpeg
]
```

### 3. ExportOptions Extension

**File**: `osxphotos/exportoptions.py`

Add new field to `ExportOptions` dataclass (after line 78):
```python
@dataclasses.dataclass
class ExportOptions:
    ...
    convert_to_jpeg: bool = False
    jpegli_reencode: bool = False  # Add this
    ...
```

Update the docstring to include:
```python
"""
...
jpegli_reencode (bool): if True, re-encodes JPEG files using jpegli encoder (requires convert_to_jpeg)
...
"""
```

### 4. Jpegli Integration Module

**New File**: `osxphotos/jpegli.py`
```python
"""Jpegli integration for osxphotos"""

import os
import pathlib
import platform
import subprocess
import tempfile
from typing import Optional

from .platform import is_macos
from .utils import get_resource_path

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
        binary_path = get_resource_path(f"bin/{binary_name}")
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
            "-q", str(quality),
            "-o", output_path,
            input_path
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
```

### 5. FileUtil Extension

**File**: `osxphotos/fileutil.py`

Add jpegli method to `FileUtilABC` (around line 67):
```python
@classmethod
@abstractmethod
def reencode_jpeg_with_jpegli(cls, src_file, dest_file, quality=85):
    pass
```

Add implementation to `FileUtilMacOS` (around line 235):
```python
@classmethod
def reencode_jpeg_with_jpegli(cls, src_file, dest_file, quality=85):
    """Re-encode JPEG using jpegli encoder
    
    Args:
        src_file: source JPEG file
        dest_file: destination path for re-encoded file
        quality: JPEG quality (1-100), default 85
        
    Returns:
        True if success, otherwise False
    """
    try:
        from .jpegli import JpegliEncoder
        
        src_file = normalize_fs_path(src_file)
        dest_file = normalize_fs_path(dest_file)
        
        encoder = JpegliEncoder()
        encoder.encode(src_file, dest_file, quality=quality)
        return True
    except Exception as e:
        # Fall back to regular copy if jpegli fails
        import logging
        logger = logging.getLogger("osxphotos")
        logger.warning(f"jpegli encoding failed, falling back to regular copy: {e}")
        shutil.copy2(src_file, dest_file)
        return False
```

### 6. PhotoExporter Modifications

**File**: `osxphotos/photoexporter.py`

Modify the export logic to handle jpegli reencoding (around line 990):
```python
# After line 990, add jpegli reencoding
if options.convert_to_jpeg:
    # use convert_to_jpeg to export the file
    # convert to a temp file before copying
    tmp_file = increment_filename(
        self._temp_dir_path
        / f"{pathlib.Path(src).stem}_converted_to_jpeg.jpeg"
    )
    fileutil.convert_to_jpeg(
        src, tmp_file, compression_quality=options.jpeg_quality
    )
    src = tmp_file
    converted_to_jpeg_files.append(dest_str)
    
    # Add jpegli reencoding if requested
    if options.jpegli_reencode:
        jpegli_tmp = increment_filename(
            self._temp_dir_path
            / f"{pathlib.Path(src).stem}_jpegli.jpeg"
        )
        # Convert quality from 0.0-1.0 to 1-100
        jpegli_quality = int(options.jpeg_quality * 100)
        if fileutil.reencode_jpeg_with_jpegli(src, jpegli_tmp, quality=jpegli_quality):
            src = jpegli_tmp
            verbose(f"Re-encoded {dest_str} with jpegli")
        else:
            verbose(f"Failed to re-encode {dest_str} with jpegli, using standard JPEG")

# Also handle existing JPEGs when jpegli_reencode is True but convert_to_jpeg is False
elif options.jpegli_reencode and self.photo.uti_original == "public.jpeg":
    # Re-encode existing JPEG with jpegli
    jpegli_tmp = increment_filename(
        self._temp_dir_path
        / f"{pathlib.Path(src).stem}_jpegli.jpeg"
    )
    jpegli_quality = int(options.jpeg_quality * 100)
    if fileutil.reencode_jpeg_with_jpegli(src, jpegli_tmp, quality=jpegli_quality):
        src = jpegli_tmp
        verbose(f"Re-encoded {dest_str} with jpegli")
```

### 7. Binary Distribution

**Directory Structure**:
```
osxphotos/
  resources/
    bin/
      cjpegli_arm64    # ARM64 macOS binary
      cjpegli_x86_64   # Intel macOS binary
```

**File**: `setup.py`

Update to include jpegli binaries:
```python
package_data={
    'osxphotos': [
        'resources/bin/cjpegli_*',
        # ... existing entries
    ]
}
```

### 8. Testing Strategy

**New Test File**: `tests/test_jpegli_integration.py`
```python
import os
import pathlib
import tempfile

import pytest

from osxphotos.exportoptions import ExportOptions
from osxphotos.photoexporter import PhotoExporter
from osxphotos.jpegli import JpegliEncoder, JpegliError

# Skip tests if jpegli not available
skip_test = "OSXPHOTOS_TEST_JPEGLI" not in os.environ
pytestmark = pytest.mark.skipif(
    skip_test, reason="Skip jpegli tests unless explicitly enabled"
)

PHOTOS_DB = "tests/Test-10.15.6.photoslibrary"
UUID_JPEG = "..."  # Need to find a JPEG in test library
UUID_HEIC = "7783E8E6-9CAC-40F3-BE22-81FB7051C266"


class TestJpegliEncoder:
    def test_jpegli_available(self):
        """Test that jpegli encoder can be instantiated"""
        try:
            encoder = JpegliEncoder()
            assert encoder._jpegli_path is not None
        except JpegliError:
            pytest.skip("jpegli not available on this platform")
    
    def test_encode_jpeg(self, tmp_path):
        """Test encoding a JPEG file"""
        # Create a test JPEG (would need actual JPEG data)
        input_file = tmp_path / "test.jpg"
        output_file = tmp_path / "output.jpg"
        
        # ... create test file ...
        
        encoder = JpegliEncoder()
        result = encoder.encode(str(input_file), str(output_file), quality=85)
        assert result
        assert output_file.exists()


@pytest.fixture(scope="module")
def photosdb():
    import osxphotos
    return osxphotos.PhotosDB(dbfile=PHOTOS_DB)


def test_export_with_jpegli_existing_jpeg(photosdb):
    """Test exporting existing JPEG with jpegli reencoding"""
    # Implementation needed
    pass


def test_export_convert_to_jpeg_with_jpegli(photosdb):
    """Test converting HEIC to JPEG then reencoding with jpegli"""
    tempdir = tempfile.TemporaryDirectory(prefix="osxphotos_")
    dest = tempdir.name
    photos = photosdb.photos(uuid=[UUID_HEIC])
    
    export_options = ExportOptions(
        convert_to_jpeg=True,
        jpegli_reencode=True,
        jpeg_quality=0.85
    )
    results = PhotoExporter(photos[0]).export(dest, options=export_options)
    
    assert len(results.exported) == 1
    exported_file = pathlib.Path(results.exported[0])
    assert exported_file.exists()
    assert exported_file.suffix == ".jpeg"
    
    # Verify file was actually processed by jpegli
    # (would need to check file metadata or size difference)
```

### 9. Performance Considerations

1. **Subprocess Overhead**: Each jpegli call spawns a subprocess. For large exports, consider:
   - Batching multiple files if jpegli supports it
   - Using threading/multiprocessing for parallel encoding
   
2. **Temporary Files**: The implementation uses temporary files which adds I/O overhead:
   - Consider in-memory processing if possible
   - Ensure temp files are cleaned up properly

3. **Fallback Strategy**: If jpegli fails, fall back to standard JPEG to ensure export completes

### 10. Platform Support

Initial implementation focuses on macOS:
- ARM64 (Apple Silicon)
- x86_64 (Intel)

Future expansion could include:
- Linux support
- Windows support (if jpegli binaries available)

### 11. Documentation Updates

**File**: `README.md`

Add section about jpegli support:
```markdown
### JPEG Optimization with jpegli

osxphotos supports Google's jpegli encoder for improved JPEG compression. When used with `--convert-to-jpeg`, the `--jpegli-reencode` option will re-encode all JPEG files (both existing and newly converted) using jpegli for better compression while maintaining quality.

Example:
```bash
osxphotos export /path/to/export --convert-to-jpeg --jpegli-reencode --jpeg-quality 0.85
```

Note: jpegli support is currently only available on macOS (Intel and Apple Silicon).
```

## Implementation Steps

1. **Phase 1: Core Infrastructure**
   - Create `jpegli.py` module
   - Add jpegli binaries to resources
   - Extend `FileUtil` with jpegli support
   - Add basic tests

2. **Phase 2: CLI Integration**
   - Add `--jpegli-reencode` option
   - Update `ExportOptions`
   - Add option validation

3. **Phase 3: Export Pipeline Integration**
   - Modify `PhotoExporter` to use jpegli
   - Handle both conversion and reencoding scenarios
   - Add comprehensive tests

4. **Phase 4: Polish & Documentation**
   - Error handling and logging
   - Performance optimization
   - Documentation updates
   - Integration tests

## Risk Mitigation

1. **Binary Compatibility**: Test on various macOS versions
2. **Performance**: Profile with large photo libraries
3. **Error Handling**: Ensure graceful fallback if jpegli fails
4. **File Integrity**: Verify exported files are valid JPEGs

## Future Enhancements

1. **Quality Optimization**: Auto-detect optimal quality settings
2. **Batch Processing**: Process multiple files in one jpegli call
3. **Progress Reporting**: Show jpegli processing progress
4. **Statistics**: Report compression savings achieved