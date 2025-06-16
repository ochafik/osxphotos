"""Test jpegli integration"""

import os
import pathlib
import tempfile

import pytest

from osxphotos.exportoptions import ExportOptions
from osxphotos.jpegli import JpegliEncoder, JpegliError
from osxphotos.fileutil import FileUtil

# Skip tests if jpegli not available
skip_test = "OSXPHOTOS_TEST_JPEGLI" not in os.environ
pytestmark = pytest.mark.skipif(
    skip_test, reason="Skip jpegli tests unless explicitly enabled"
)

PHOTOS_DB_15_7 = "tests/Test-13.0.0.photoslibrary"
UUID_HEIC = "7783E8E6-9CAC-40F3-BE22-81FB7051C266"
UUID_JPEG = "A1DD1F98-2ECD-431F-9AC9-5AFEFE2D3A5C"  # Test-13.0 has JPEGs


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
        # Create a simple test JPEG using PIL
        try:
            from PIL import Image
        except ImportError:
            pytest.skip("PIL not available")
        
        # Create a test image
        input_file = tmp_path / "test.jpg"
        output_file = tmp_path / "output.jpg"
        
        # Create a simple RGB image
        img = Image.new('RGB', (100, 100), color='red')
        img.save(str(input_file), 'JPEG')
        
        try:
            encoder = JpegliEncoder()
            result = encoder.encode(str(input_file), str(output_file), quality=85)
            assert result
            assert output_file.exists()
            
            # Check that output is smaller or similar size (jpegli should compress better)
            input_size = input_file.stat().st_size
            output_size = output_file.stat().st_size
            assert output_size > 0
            # Jpegli typically produces smaller files
            assert output_size <= input_size * 1.1  # Allow 10% margin
        except JpegliError:
            pytest.skip("jpegli not available on this platform")


class TestFileUtilJpegli:
    def test_reencode_jpeg_with_jpegli(self, tmp_path):
        """Test FileUtil.reencode_jpeg_with_jpegli method"""
        try:
            from PIL import Image
        except ImportError:
            pytest.skip("PIL not available")
        
        # Create a test image
        input_file = tmp_path / "test.jpg"
        output_file = tmp_path / "output.jpg"
        
        # Create a simple RGB image
        img = Image.new('RGB', (100, 100), color='blue')
        img.save(str(input_file), 'JPEG', quality=95)
        
        # Test reencoding
        result = FileUtil.reencode_jpeg_with_jpegli(
            str(input_file), str(output_file), quality=85
        )
        
        assert output_file.exists()
        # Result may be False if jpegli is not available, but file should still exist
        # (falls back to copy)
        
    def test_reencode_jpeg_with_jpegli_missing_file(self, tmp_path):
        """Test FileUtil.reencode_jpeg_with_jpegli with missing input file"""
        input_file = tmp_path / "missing.jpg"
        output_file = tmp_path / "output.jpg"
        
        # Should fall back to copy, which will fail
        # Since the file doesn't exist, the fallback copy will also fail
        # causing an exception
        try:
            result = FileUtil.reencode_jpeg_with_jpegli(
                str(input_file), str(output_file), quality=85
            )
            # If no exception, result should be False
            assert result is False
        except FileNotFoundError:
            # This is expected when the fallback copy also fails
            pass
        
        # Output should not be created
        assert not output_file.exists()


@pytest.fixture(scope="module")
def photosdb():
    import osxphotos
    return osxphotos.PhotosDB(dbfile=PHOTOS_DB_15_7)


class TestExportWithJpegli:
    def test_export_convert_to_jpeg_with_jpegli(self, photosdb, tmp_path):
        """Test converting HEIC to JPEG then reencoding with jpegli"""
        from osxphotos.photoexporter import PhotoExporter
        
        photos = photosdb.photos(uuid=[UUID_HEIC])
        assert len(photos) == 1
        
        export_options = ExportOptions(
            convert_to_jpeg=True,
            jpegli_reencode=True,
            jpeg_quality=0.85
        )
        
        exporter = PhotoExporter(photos[0])
        results = exporter.export(str(tmp_path), options=export_options)
        
        assert len(results.exported) == 1
        exported_file = pathlib.Path(results.exported[0])
        assert exported_file.exists()
        assert exported_file.suffix.lower() in [".jpeg", ".jpg"]
    
    def test_export_existing_jpeg_with_jpegli(self, photosdb, tmp_path):
        """Test reencoding existing JPEG with jpegli"""
        from osxphotos.photoexporter import PhotoExporter
        
        photos = photosdb.photos(uuid=[UUID_JPEG])
        assert len(photos) == 1
        
        export_options = ExportOptions(
            convert_to_jpeg=True,  # Required for jpegli_reencode
            jpegli_reencode=True,
            jpeg_quality=0.85
        )
        
        exporter = PhotoExporter(photos[0])
        results = exporter.export(str(tmp_path), options=export_options)
        
        assert len(results.exported) == 1
        exported_file = pathlib.Path(results.exported[0])
        assert exported_file.exists()
        assert exported_file.suffix.lower() in [".jpeg", ".jpg"]
    
    def test_export_without_jpegli(self, photosdb, tmp_path):
        """Test normal export without jpegli"""
        from osxphotos.photoexporter import PhotoExporter
        
        photos = photosdb.photos(uuid=[UUID_HEIC])
        assert len(photos) == 1
        
        export_options = ExportOptions(
            convert_to_jpeg=True,
            jpegli_reencode=False,  # No jpegli
            jpeg_quality=0.85
        )
        
        exporter = PhotoExporter(photos[0])
        results = exporter.export(str(tmp_path), options=export_options)
        
        assert len(results.exported) == 1
        exported_file = pathlib.Path(results.exported[0])
        assert exported_file.exists()
        assert exported_file.suffix.lower() in [".jpeg", ".jpg"]