# OpenBCI Setup & Streaming Solution

## Hardware
- **Device**: OpenBCI Ultracortex Mark IV
- **Board**: Cyton (8 channels) + Daisy (additional 8 channels)
- **Port**: `/dev/cu.usbserial-DM01MV82` (macOS)
- **Baud Rate**: 115200 (standard OpenBCI rate)

## Current Status (2025-09-20)
✅ **WORKING**: Direct serial streaming using PySerial
✅ **Channels 1-8**: Receiving real EEG data from Cyton board
❌ **Channels 9-16**: Not receiving data from Daisy board (shows 0.0μV)
⚠️ **Scaling Issue**: Values showing ±40,000μV instead of normal ±200μV range

## The Journey: Problems & Solutions

### Problem 1: BrainFlow Not Working
**Error**: `BOARD_NOT_READY_ERROR:7 unable to prepare streaming session`
**Cause**: Board firmware incompatibility with BrainFlow library
**Solution**: Abandoned BrainFlow, switched to direct PySerial communication

### Problem 2: Only Getting 0xFF Bytes
**Symptom**: Board only sending single byte (0xFF) acknowledgments
**Solution**: Send proper initialization sequence:
```python
ser.write(b's')  # Stop streaming
time.sleep(0.5)
ser.write(b'd')  # Default settings
time.sleep(0.5)
ser.write(b'b')  # Begin streaming
```

### Problem 3: Understanding Light Patterns
- **Blue light only**: Board powered on, not streaming
- **Blue + Red lights**: STREAMING MODE ACTIVE ✓
- **Lights off**: Board stopped/idle

### Problem 4: Packet Structure
OpenBCI sends 33-byte packets:
- Byte 0: 0xA0 (start marker)
- Byte 1: Packet counter
- Bytes 2-25: 8 channels × 3 bytes (24-bit values)
- Bytes 26-31: Auxiliary data
- Byte 32: 0xC0 (end marker)

## Working Solution (PySerial)

**Technology**: Pure Python with PySerial library
**No external dependencies**: Not using BrainFlow, just serial communication

### Core Code:
```python
import serial
import time

# Connect
ser = serial.Serial("/dev/cu.usbserial-DM01MV82", 115200, timeout=0.1)

# Initialize streaming
ser.write(b's')  # Stop
time.sleep(0.5)
ser.write(b'd')  # Defaults
time.sleep(0.5)
ser.write(b'b')  # Begin (triggers Blue+Red lights)

# Read and parse packets
buffer = bytearray()
while True:
    buffer.extend(ser.read(ser.in_waiting))
    # Look for 0xA0...0xC0 packets (33 bytes)
    # Parse 24-bit values for each channel
```

## Current Channel Readings

### What Each Channel Shows:
- **Ch 1-8**: Active EEG signals from Cyton board
  - Values fluctuating = picking up brain activity
  - High values (±40,000μV) = scaling factor needs adjustment

- **Ch 9-16**: All showing 0.0μV
  - Daisy board not properly initialized
  - May need firmware update or different init sequence

### Normal EEG Ranges:
- **Delta (0.5-4 Hz)**: ±100-200μV
- **Theta (4-8 Hz)**: ±50-100μV
- **Alpha (8-12 Hz)**: ±20-50μV
- **Beta (12-30 Hz)**: ±10-30μV
- **Gamma (30+ Hz)**: ±5-20μV

## Files Created

1. **WORKING_DISPLAY.py** - Shows first 3 channels, confirmed streaming
2. **CALIBRATED_STREAM.py** - Shows all 16 channels with visualization
3. **force_stream.py** - Diagnostic tool, shows raw packet structure

## Next Steps

1. **Fix Scaling**: Adjust scale factor from 0.02235 to proper value
2. **Enable Daisy**: Send commands to activate channels 9-16
3. **Add Filters**: Implement bandpass filters for cleaner signals
4. **Real-time Processing**: Add FFT for frequency analysis

## Troubleshooting Commands

```bash
# Find serial port
ls /dev/cu.*

# Test connection
python force_stream.py

# View real-time data
python CALIBRATED_STREAM.py
```

## Key Learning
- BrainFlow doesn't work with all OpenBCI firmware versions
- Direct serial communication with PySerial is more reliable
- Proper initialization sequence is critical
- Light patterns indicate streaming status