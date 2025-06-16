# jpegli Export Fix Analysis

## Issue Summary

The error "name 'jpegli_reencode' is not defined" occurs when running osxphotos export with the `--jpegli-reencode` flag. The error is thrown during the export process.

## Root Cause Analysis

After analyzing the code, I've identified the root cause:

1. The `jpegli_reencode` parameter was added to the CLI options and ExportOptions class correctly
2. However, it was NOT added to the `export_photo()` function signature in `osxphotos/cli/export.py`
3. When the export code collects parameters using `locals()` and filters them based on `inspect.getfullargspec(export_photo).args`, it tries to pass `jpegli_reencode` to `export_photo()`
4. Since `jpegli_reencode` is not in the function signature, it gets passed as part of kwargs
5. This causes an error when the function is called

## Code Analysis

### Line 1988-1990 in export.py:
```python
kwargs = {
    k: v
    for k, v in locals().items()
    if k in inspect.getfullargspec(export_photo).args
}
```

This code filters local variables to only include those that are accepted by `export_photo()`. Since `jpegli_reencode` is not in the function signature, it should be filtered out, but it appears to be getting through somehow.

### The export_photo function (starting at line 2286):
The function signature does not include `jpegli_reencode` parameter, but the code at line 2801 tries to pass it to ExportOptions.

## Fix Required

Add `jpegli_reencode` parameter to the `export_photo()` function signature:

1. Add it to the function parameters (around line 2323, after `convert_to_jpeg`)
2. Add documentation for it in the docstring
3. Ensure it's passed correctly to ExportOptions

## Recommended Changes

### 1. Update export_photo function signature (line ~2322):

```python
def export_photo(
    # ... existing parameters ...
    convert_to_jpeg=False,
    jpegli_reencode=False,  # ADD THIS LINE
    jpeg_quality=1.0,
    # ... rest of parameters ...
```

### 2. Update the docstring (around line ~2347):

```python
"""Helper function for export that does the actual export

Args:
    # ... existing args ...
    convert_to_jpeg: bool; if True, converts non-jpeg images to jpeg
    jpegli_reencode: bool; if True, re-encodes JPEG files using jpegli encoder
    # ... rest of args ...
```

### 3. Verify the parameter is passed to ExportOptions correctly

The code at line 2801 already passes `jpegli_reencode=jpegli_reencode`, so this should work once the parameter is added to the function signature.

## Alternative Investigation

If the above fix doesn't resolve the issue, the error might be coming from a different source:

1. Check if any template functions are trying to access `options.jpegli_reencode`
2. The PhotoTemplate system passes RenderOptions (not ExportOptions) to template functions, so any template function trying to access `jpegli_reencode` would fail
3. Search for any custom template functions that might be accessing this field

## Testing Recommendation

After applying the fix:
1. Test basic export: `osxphotos export /path/to/dest --jpegli-reencode`
2. Test with convert-to-jpeg: `osxphotos export /path/to/dest --convert-to-jpeg --jpegli-reencode`
3. Test with various template options to ensure no template functions are affected