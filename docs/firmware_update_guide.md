# OpenBCI Firmware Update Guide for 16-Channel Streaming

## Current Situation

Your OpenBCI Cyton+Daisy board is running non-standard firmware that only sends acknowledgment bytes (0xFF) instead of proper EEG data packets. This is why you only see Channel 1 with 12.7 μV and Channels 2-16 show 0.0 μV.

### Diagnosis Results:
- **Current Output**: Single 0xFF bytes only
- **Expected Output**: 33-byte packets with 0xA0 header containing all 16 channels
- **Root Cause**: Firmware doesn't implement OpenBCI streaming protocol
- **Solution Required**: Firmware update to standard OpenBCI firmware

## Firmware Update Instructions

### Prerequisites
1. **Arduino IDE** (1.8.x or later)
2. **FTDI Drivers** (already installed since serial port works)
3. **OpenBCI firmware files**
4. **USB connection** to your Cyton board

### Step 1: Download OpenBCI Firmware

```bash
# Clone the official OpenBCI firmware repository
git clone https://github.com/OpenBCI/OpenBCI_32bit_Library.git
cd OpenBCI_32bit_Library
```

### Step 2: Install Arduino Board Support

1. Open Arduino IDE
2. Go to **Preferences** → **Additional Board Manager URLs**
3. Add: `https://raw.githubusercontent.com/OpenBCI/OpenBCI_32bit_Library/master/package_openbci_index.json`
4. Go to **Tools** → **Board** → **Boards Manager**
5. Search for "OpenBCI" and install **OpenBCI Boards**

### Step 3: Select Board Configuration

In Arduino IDE:
- **Board**: "OpenBCI Cyton"
- **Port**: `/dev/cu.usbserial-DM01MV82` (your port)
- **Programmer**: "AVR ISP"

### Step 4: Load Firmware

1. Open firmware file:
   - For Cyton only: `OpenBCI_32bit_Library/examples/DefaultBoard/DefaultBoard.ino`
   - For Cyton+Daisy: `OpenBCI_32bit_Library/examples/BoardWithDaisy/BoardWithDaisy.ino`

2. **IMPORTANT**: Since you have Cyton+Daisy (16 channels), use **BoardWithDaisy.ino**

### Step 5: Upload Firmware

1. Put board in upload mode:
   - Press and hold the **PROG** button on the Cyton board
   - Press and release the **RESET** button
   - Release the **PROG** button
   - The board is now in bootloader mode

2. In Arduino IDE:
   - Click **Upload** (→ button)
   - Wait for "Done uploading" message

### Step 6: Verify New Firmware

After successful upload, test with this Python script:

```python
import serial
import time

# Test new firmware
port = serial.Serial('/dev/cu.usbserial-DM01MV82', 115200, timeout=2)
port.reset_input_buffer()

# Send version command
port.write(b'v')
time.sleep(2)

response = port.read(port.in_waiting)
print(f"Firmware response: {response}")

# Should see something like:
# "OpenBCI V3 32bit Board"
# "Daisy attached"

# Start streaming
port.write(b'b')
time.sleep(1)

# Check for proper packets
data = port.read(100)
if b'\xa0' in data:
    print("✅ SUCCESS! Board now sends proper OpenBCI packets!")
else:
    print("❌ Still not working - check connections")

port.close()
```

## Expected Results After Update

### Before (Current):
- Single 0xFF bytes
- Only Channel 1 shows 12.7 μV
- No real EEG data

### After (With Updated Firmware):
- 33-byte packets starting with 0xA0
- All 16 channels with real EEG values
- Proper timestamps and sample numbers
- Compatible with BrainFlow

## Testing Full 16-Channel Streaming

Once firmware is updated, you can use:

1. **BrainFlow** (will now work properly):
```python
from brainflow import BoardShim, BrainFlowInputParams, BoardIds

params = BrainFlowInputParams()
params.serial_port = '/dev/cu.usbserial-DM01MV82'

board = BoardShim(BoardIds.CYTON_DAISY_BOARD, params)
board.prepare_session()  # Should work now!
board.start_stream()

# Get 16-channel data
data = board.get_board_data()
print(f"Channels: {data.shape[0]}, Samples: {data.shape[1]}")
```

2. **Our Custom Parser** (`full_16_channel_streaming.py`):
- Will now receive proper 33-byte packets
- Parse all 16 channels correctly
- Display real EEG values in μV

## Troubleshooting

### Issue: Upload fails
- **Solution**: Make sure board is in bootloader mode (PROG + RESET sequence)

### Issue: Still getting 0xFF after update
- **Solution**: Check if Daisy module is properly connected to Cyton board
- **Solution**: Try uploading BoardWithDaisy.ino specifically

### Issue: Arduino can't find board
- **Solution**: Install OpenBCI board support package in Arduino IDE

### Issue: Port not found in Arduino
- **Solution**: Close all Python scripts using the port first

## Alternative: OpenBCI GUI

If you prefer not to update firmware immediately, you can use the **OpenBCI GUI**:

1. Download from: https://openbci.com/downloads
2. It may auto-update firmware when connecting
3. Verify all 16 channels work in the GUI first
4. Then use our Python scripts

## Summary

Your board needs the standard OpenBCI firmware to stream all 16 channels. The current firmware only sends acknowledgment bytes, which is why you see limited data. After updating the firmware, you'll have:

- ✅ All 16 channels with real EEG data
- ✅ BrainFlow compatibility
- ✅ Standard OpenBCI packet format
- ✅ Full Cyton+Daisy functionality

The firmware update is a one-time process and will permanently fix the streaming issue.