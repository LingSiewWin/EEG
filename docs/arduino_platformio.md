# OpenBCI Cyton Firmware Update on Apple Silicon Mac - Complete Troubleshooting Guide

## Problem Statement
- **Goal**: Update OpenBCI Cyton firmware to stream real electrode data instead of sample data for WebSocket/Web3 ZK-proof project
- **Hardware**: Apple Silicon MacBook (M-series chip)
- **Challenge**: Compiler toolchain incompatibility with Apple Silicon architecture

## Environment Setup

### Initial Conditions
- **OS**: macOS on Apple Silicon (M1/M2/M3)
- **Arduino IDE**: Attempted versions 1.8.19 and 2.x
- **Target Board**: OpenBCI Cyton 32-bit (PIC32MX250F128B microcontroller)

## Troubleshooting Journey

### Attempt 1: Arduino IDE 2.x with ChipKIT 2.x
**Setup:**
- Downloaded latest Arduino IDE 2.x
- Installed ChipKIT core 2.x

**Error:**
```
pic32-g++: bad CPU type in executable
```

**Analysis:** ChipKIT 2.x tools incompatible with Apple Silicon

---

### Attempt 2: Arduino IDE 1.8.19 with ChipKIT 1.3.1
**Rationale:** OpenBCI forums recommend ChipKIT 1.3.1 to avoid data stream issues

**Setup Process:**
1. **Clean Installation:**
   ```bash
   # Complete cleanup
   sudo rm -rf /Applications/Arduino.app
   rm -rf ~/Library/Arduino15/
   rm -rf ~/Documents/Arduino/
   ```

2. **Install Arduino IDE 1.8.19:**
   - Downloaded from Arduino legacy page
   - Set permissions before ChipKIT installation:
   ```bash
   sudo chmod -R 755 /Applications/Arduino.app
   sudo chmod -R 755 ~/Documents/Arduino
   ```

3. **Install ChipKIT 1.3.1:**
   - Added board manager URL: `https://raw.githubusercontent.com/chipKIT32/chipKIT-core/master/package_chipkit_index.json`
   - Installed specifically version 1.3.1 (not latest)

**Error:**
```
fork/exec /Users/.../pic32-g++: bad CPU type in executable
```

**Analysis:** Same fundamental issue - 32-bit Intel binaries incompatible with Apple Silicon

---

### Attempt 3: Rosetta 2 Configuration
**Goal:** Force Arduino and compiler tools to run under Intel emulation

**Steps Taken:**
1. **Install Rosetta 2:**
   ```bash
   sudo softwareupdate --install-rosetta --agree-to-license
   ```

2. **Force Arduino to use Rosetta:**
   ```bash
   sudo defaults write /Applications/Arduino.app/Contents/Info.plist LSRequiresNativeExecution -bool NO
   ```

3. **Alternative launch method:**
   ```bash
   arch -x86_64 /Applications/Arduino.app/Contents/MacOS/Arduino
   ```

**Problem:** JVM errors when modifying Arduino.app directly

**Solution:** Used manual Rosetta launch via terminal

---

### Attempt 4: Compiler Tool Wrapper Scripts
**Analysis:** Arduino runs under Rosetta but doesn't pass Intel emulation to compiler subprocesses

**Solution Attempt:**
```bash
cd /Users/.../chipKIT/tools/pic32-tools/1.42-pic32gcc/bin/

# Create backup and wrapper scripts
mkdir -p original_tools
for file in pic32-*; do
    if [ -f "$file" ] && [ -x "$file" ] && [ ! -d "$file" ]; then
        file_size=$(stat -f%z "$file")
        if [ "$file_size" -gt 1000 ]; then
            cp "$file" "original_tools/$file"
            cat > "$file" << 'EOF'
#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
export ARCHPREFERENCE=i386
exec arch -x86_64 "$SCRIPT_DIR/original_tools/$(basename "$0")" "$@"
EOF
            chmod +x "$file"
        fi
    fi
done
```

**Result:** Wrappers created successfully for 23 tools, but still failed due to underlying 32-bit binary incompatibility

---

### Attempt 5: PlatformIO Alternative
**Rationale:** Modern development platform might have better Apple Silicon support

**Setup:**
1. **Installation:**
   - Installed VS Code
   - Added PlatformIO extension
   
2. **Project Creation:**
   ```ini
   [env:openbci]
   platform = microchippic32
   board = openbci
   framework = arduino
   ```

3. **Libraries:** PlatformIO automatically managed dependencies

**Error:**
```
sh: /Users/.../toolchain-microchippic32/bin/pic32-g++: Bad CPU type in executable
```

**Applied Same Fix:** Created Rosetta wrapper scripts for PlatformIO's toolchain

**Final Result:** Same failure - even with wrappers, 32-bit Intel binaries (`Mach-O executable i386`) cannot execute on Apple Silicon

---

## Technical Analysis

### Root Cause
The fundamental issue is that **all PIC32 compiler toolchains** (both ChipKIT and PlatformIO) use 32-bit Intel binaries that are incompatible with Apple Silicon, even with Rosetta 2 emulation.

### Binary Analysis
```bash
file pic32-g++
# Output: Mach-O executable i386
```

### Versions Tested
- **ChipKIT**: 1.3.1, 1.4.1, 2.1.0
- **PlatformIO**: toolchain-microchippic32 @ 1.40803.143
- **Arduino IDE**: 1.8.19, 2.x

All versions exhibited the same incompatibility.

## Working Solutions

### 1. Contact OpenBCI Support (Recommended)
**Email:** support@openbci.com

**Request:**
- Pre-compiled firmware files
- Apple Silicon-compatible tools
- Alternative update methods

**Justification:** OpenBCI documentation states users should contact support before firmware modifications.

### 2. Cloud-Based Compilation
**Options:**
- GitHub Codespaces
- Cloud-based Arduino IDE
- Remote development environments

**Process:**
1. Upload code to cloud platform
2. Compile on Intel-based cloud machines
3. Download compiled firmware for local upload

### 3. Alternative Hardware
- Use Intel Mac or Windows machine
- Borrow/rent compatible hardware
- Virtual machine with Intel emulation

### 4. Verify Problem First
Before complex workarounds, confirm that:
- Board is actually showing sample data vs. real data
- Electrodes are properly connected
- OpenBCI GUI shows synthetic vs. real signals

## Lessons Learned

### Key Insights
1. **Apple Silicon compatibility** is still limited for embedded development toolchains
2. **32-bit Intel binaries** are particularly problematic, even with Rosetta 2
3. **ChipKIT toolchain** hasn't been updated for modern Apple hardware
4. **PlatformIO** uses the same underlying incompatible tools

### Successful Approaches
- **Rosetta 2 installation** and configuration worked correctly
- **Wrapper script methodology** was technically sound
- **PlatformIO setup** provided better development environment

### Failed Approaches
- Direct binary execution on Apple Silicon
- Rosetta emulation for 32-bit tools
- Multiple toolchain versions

## Recommendations for Future Users

### For Apple Silicon Mac Users
1. **Contact OpenBCI support first** before attempting local compilation
2. **Use cloud-based development** for PIC32 projects
3. **Consider Intel Mac access** for embedded development
4. **Verify problem exists** before pursuing firmware updates

### For OpenBCI Development
1. **Update toolchain** to 64-bit Intel or Apple Silicon native binaries
2. **Provide pre-compiled firmware** options
3. **Document Apple Silicon limitations**
4. **Consider web-based compilation service**

## Command Reference

### Useful Commands
```bash
# Check binary architecture
file /path/to/binary

# Force Rosetta launch
arch -x86_64 /Applications/Arduino.app/Contents/MacOS/Arduino

# Install Rosetta 2
sudo softwareupdate --install-rosetta --agree-to-license

# Check file sizes for wrapper scripts
stat -f%z filename
```

### File Locations
- **Arduino ChipKIT tools:** `~/Library/Arduino15/packages/chipKIT/tools/pic32-tools/`
- **PlatformIO tools:** `~/.platformio/packages/toolchain-microchippic32/bin/`
- **Arduino preferences:** `~/Library/Arduino15/`

## Conclusion

While multiple technical approaches were attempted, the fundamental incompatibility between 32-bit PIC32 compiler tools and Apple Silicon architecture prevents local compilation. The most practical solution is to use cloud-based compilation or contact OpenBCI support for pre-compiled firmware files.

**Status:** Unresolved locally, requires external solution
**Recommended Next Step:** Contact support@openbci.com
**Alternative:** Use GitHub Codespaces for cloud compilation