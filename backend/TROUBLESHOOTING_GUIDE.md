# OpenBCI Troubleshooting Guide

## Current Status
Your OpenBCI board is responding but only sending 0xFF acknowledgment bytes, not full EEG data packets.

## Quick Fixes to Try NOW

### 1. Hardware Checks
- [x] Tighten electrodes ✓ (you did this)
- [x] Replace battery ✓ (you did this)
- [x] Switch to "PC" mode ✓ (you did this)
- [x] Press reset button ✓ (you did this)
- [ ] **Try different USB cable** (important!)
- [ ] **Remove Daisy module temporarily** (test with Cyton only)

### 2. Board Reset Sequence
```bash
# Run this exact sequence:
1. Turn board OFF
2. Disconnect USB cable
3. Remove battery for 10 seconds
4. Insert battery
5. Turn board ON (switch to PC)
6. Wait 5 seconds (LED should blink)
7. Connect USB cable
8. Run: python backend/working/MAIN_WORKING_SOLUTION.py
```

### 3. Test Different Baud Rates
```bash
# Try these in order:
python backend/diagnostics/quick_diagnostic.py  # Tests both 230400 and 115200
```

### 4. Firmware Issues (MOST LIKELY CAUSE)

**Your board appears to have custom/old firmware that only sends acknowledgments (0xFF)**

To fix:
1. Download OpenBCI GUI: https://openbci.com/downloads
2. Connect board through GUI first
3. Use GUI to update firmware:
   - Click "System Status"
   - Select "Firmware Update"
   - Follow prompts

### 5. Test With OpenBCI GUI
Before running Python scripts:
1. Open OpenBCI GUI
2. Select "CYTON (live)"
3. Select your serial port
4. Click "START SESSION"
5. If it works there, close GUI and try Python scripts

### 6. Phone/Interference Issues
- [x] Airplane mode ✓ (good thinking!)
- [ ] Move away from WiFi router
- [ ] Turn off Bluetooth devices nearby
- [ ] Try in different room

## File Organization

### ✅ WORKING FILES (Use These First)
- `backend/working/MAIN_WORKING_SOLUTION.py` - **START HERE**
- `backend/working/passive_listener.py` - Listens without sending commands
- `backend/working/simple_terminal_stream.py` - Basic terminal display

### 🔧 DIAGNOSTIC TOOLS
- `backend/diagnostics/quick_diagnostic.py` - Tests connection
- `backend/diagnostics/test_serial.py` - Raw serial test
- `backend/diagnostics/diagnose_crash.py` - Debug crashes

### 🧪 EXPERIMENTAL (Don't Use Yet)
- Files using BrainFlow (incompatible with your firmware)
- Advanced decoders (need full packets first)

## Next Steps in Order

1. **Run the main solution:**
   ```bash
   cd backend/working
   python MAIN_WORKING_SOLUTION.py
   ```

2. **If still only seeing 0xFF:**
   - Your board needs firmware update via OpenBCI GUI
   - This is normal for some older boards

3. **After firmware update:**
   - You should see 33-byte packets
   - All 16 channels will show data

## Expected Output

### Current (with old firmware):
```
Channel 1: 12.7 μV (from 0xFF)
Channels 2-16: 0.0 μV
```

### After firmware update:
```
Channel 1-16: Varying values (-100 to +100 μV)
Data rate: ~250 Hz (Cyton) or ~125 Hz (Cyton+Daisy)
```

## Emergency Commands

If board stops responding:
```bash
# Find port
ls /dev/cu.*

# Test connection
screen /dev/cu.usbserial-DM01MV82 115200

# Send reset command (in screen)
Type: v [Enter]  # Version
Type: ? [Enter]  # Help
Type: d [Enter]  # Default settings
Ctrl+A, K to exit screen
```

## Contact Support
If nothing works:
- OpenBCI Forum: https://openbci.com/forum
- Include: Firmware version, board model, error messages