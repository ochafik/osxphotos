# Building jpegli on macOS

## Overview
Jpegli is Google's new JPEG coding library that provides:
- 35% compression ratio improvement at high quality settings
- Full compatibility with traditional JPEG standards
- Both encoder (cjpegli) and decoder (djpegli)
- Support for 10+ bits per component
- Advanced quantization heuristics for better quality

## Prerequisites

1. Install Homebrew if not already installed:
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

2. Install required dependencies:
```bash
brew install llvm coreutils cmake giflib jpeg-turbo libpng ninja zlib
```

3. Set up environment variables:
```bash
# Add LLVM to PATH (use the Homebrew-installed clang)
export PATH="/usr/local/opt/llvm/bin:$PATH"

# Set CMAKE_PREFIX_PATH for dependency resolution
export CMAKE_PREFIX_PATH=$(brew --prefix giflib):$(brew --prefix jpeg-turbo):$(brew --prefix libpng):$(brew --prefix zlib)

# Set compilers
export CC=clang
export CXX=clang++
```

## Build Process

### Option 1: Using ci.sh (Recommended)

1. Clone the repository:
```bash
git clone https://github.com/google/jpegli.git
cd jpegli
```

2. Build with the CI script:
```bash
./ci.sh release
```

This will:
- Configure CMake with optimized settings
- Build the project
- Run tests automatically

### Option 2: Manual CMake Build

1. Clone and create build directory:
```bash
git clone https://github.com/google/jpegli.git
cd jpegli
mkdir build && cd build
```

2. Configure with CMake:
```bash
cmake .. \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_C_COMPILER=clang \
    -DCMAKE_CXX_COMPILER=clang++ \
    -GNinja
```

3. Build:
```bash
ninja
```

## Build Output

After successful build, you'll find:
- `tools/cjpegli`: JPEG encoder
- `tools/djpegli`: JPEG decoder
- `lib/jpegli/libjpeg.so.62.3.0`: Shared library (drop-in replacement for libjpeg)

## Known Issues on macOS

1. **"Best effort" support**: The project documentation notes that macOS builds may have some test failures and excluded sub-projects.

2. **Clang version**: Ensure you're using the Homebrew-installed clang, not Apple's XCode version:
```bash
which clang  # Should show /usr/local/opt/llvm/bin/clang
```

3. **Build warnings**: Some warnings are expected on macOS builds but don't affect functionality.

## Testing

To run tests after building:
```bash
./ci.sh test
```

Or for specific tests:
```bash
./ci.sh test -R <test_name_pattern>
```

## Integration Notes

For integrating with osxphotos:
1. The library can be used as a drop-in replacement for libjpeg
2. Consider static linking to avoid dependency issues
3. The encoder provides significant compression improvements while maintaining compatibility
4. May require wrapper functions to integrate with Python via ctypes or similar