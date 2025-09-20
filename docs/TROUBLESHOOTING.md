# 🔧 OpenBCI Troubleshooting Guide

## Quick Diagnosis

Run this test first:
```bash
cd backend
python test_serial.py
```

Based on output:
- **Only b'\xff' packets** → Firmware needs update (see FIRMWARE_UPDATE.md)
- **33-byte packets with 0xA0/0xC0** → Firmware is good, check streaming code
- **No data at all** → Port/connection issue

---

## Common Issues & Solutions

### 1. Still Getting b'\xff' After Firmware Update

**Symptom**: After flashing, board still sends single b'\xff' bytes

**Solutions**:

1. **Flash didn't complete properly**
   ```bash
   # Verify in Arduino IDE Serial Monitor
   # Send 'v' - should return "OpenBCI V3.1.2" not silence
   ```

2. **Wrong board selected in Arduino**
   - Must be "OpenBCI Cyton" not "Arduino Uno" or others
   - Tools → Board → OpenBCI Boards → OpenBCI Cyton

3. **Bootloader issue**
   - Hold RESET button on Cyton
   - Start upload in Arduino IDE
   - Release RESET when "Uploading..." appears

4. **Port locked by another process**
   ```bash
   # Kill any process using the port
   lsof -i :8765
   ps aux | grep python | grep real_data
   kill -9 [PID]
   ```

### 2. Garbled/Malformed Data

**Symptom**: Random bytes, no 0xA0/0xC0 pattern

**Solutions**:

1. **Wrong baudrate**
   ```python
   # Standard firmware uses 115200
   # Legacy uses 230400
   # Try both in test_serial.py
   ```

2. **Packet sync lost**
   ```python
   # The parser auto-resyncs on 0xA0
   # If not working, power cycle board
   ```

3. **Daisy not properly connected**
   ```bash
   # Check physical connection
   # Send 'c' command to enable 16-channel mode
   # Should see "Daisy attached" response
   ```

### 3. Board Disconnects/Goes to Sleep

**Symptom**: Blue LED turns off, data stops

**Solutions**:

1. **Don't send commands in listen-only mode**
   - Legacy firmware: NO commands at all
   - Standard firmware: Only 'v', 'c', 'b', 's' allowed

2. **Power management on macOS**
   ```bash
   # Prevent USB sleep
   sudo pmset -a hibernatemode 0
   sudo pmset -a autopoweroff 0
   sudo pmset -a standby 0
   ```

3. **Use powered USB hub**
   - Board may draw too much current
   - Especially with Daisy attached

### 4. WebSocket Connection Issues

**Symptom**: Frontend can't connect or keeps disconnecting

**Solutions**:

1. **Port already in use**
   ```bash
   lsof -t -i :8765 | xargs kill -9
   ```

2. **Firewall blocking WebSocket**
   ```bash
   # macOS: Allow Python in Security & Privacy
   System Preferences → Security & Privacy → Firewall → Options
   ```

3. **Wrong WebSocket library version**
   ```bash
   pip install websockets==12.0
   ```

### 5. No Data Showing in Frontend

**Symptom**: Connected but no values updating

**Solutions**:

1. **Check browser console (F12)**
   - Should see "WebSocket connected"
   - Look for "Received X samples" logs

2. **Backend not streaming**
   - Check backend terminal for "📤 Sample #" logs
   - If not, serial connection issue

3. **Queue overflow**
   - Restart backend
   - Frontend may be too slow

### 6. Sample Rate Too Low

**Symptom**: Expected 250Hz, getting much less

**Solutions**:

1. **CPU throttling**
   ```python
   # In real_data_streaming.py, reduce sleep
   time.sleep(0.0001)  # Instead of 0.001
   ```

2. **Serial buffer overflow**
   ```python
   # Increase buffer size
   ser = serial.Serial(..., buffer_size=65536)
   ```

3. **WebSocket broadcast too slow**
   ```python
   # Reduce broadcast interval
   await asyncio.sleep(0.02)  # 50Hz updates
   ```

### 7. Only 8 Channels Showing

**Symptom**: Channels 9-16 are all zeros

**Solutions**:

1. **Daisy not detected**
   ```python
   # Send 'c' command after connecting
   # Look for "16 channel mode" confirmation
   ```

2. **Interleaving not working**
   - Even packets = Cyton (1-8)
   - Odd packets = Daisy (9-16)
   - Check packet combining logic

3. **Physical connection**
   - Ensure Daisy pins fully seated
   - Check for bent pins

---

## Diagnostic Commands

### Test Serial Connection
```python
import serial
ser = serial.Serial('/dev/cu.usbserial-DM01MV82', 115200, timeout=1)
ser.write(b'v')
print(ser.read(100))  # Should show version
ser.close()
```

### Monitor Raw Bytes
```python
import serial
ser = serial.Serial('/dev/cu.usbserial-DM01MV82', 115200)
ser.write(b'b')  # Start stream
for _ in range(10):
    data = ser.read(33)
    print(f"Packet: {data.hex()}")
    print(f"Start: 0x{data[0]:02x}, End: 0x{data[-1]:02x}")
ser.write(b's')  # Stop
ser.close()
```

### Check Daisy
```python
import serial
ser = serial.Serial('/dev/cu.usbserial-DM01MV82', 115200)
ser.write(b'c')  # Query channel mode
response = ser.read(100)
print(response.decode('ascii', errors='ignore'))
ser.close()
```

---

## Emergency Recovery

If nothing works:

1. **Full Power Cycle**
   ```bash
   # 1. Unplug USB
   # 2. Turn board OFF (switch)
   # 3. Wait 10 seconds
   # 4. Turn board ON (switch to PC)
   # 5. Plug USB
   # 6. Wait for blue LED
   ```

2. **Factory Reset via Arduino**
   ```bash
   # Reflash with DefaultBoard.ino
   # This resets all settings
   ```

3. **Different Computer/OS**
   - Try on Windows/Linux
   - Rules out macOS-specific issues

4. **Different USB Cable**
   - Some cables are charge-only
   - Need data cable

---

## Still Stuck?

1. Check OpenBCI forums: https://openbci.com/forum
2. GitHub issues: https://github.com/OpenBCI/OpenBCI_Cyton_Library/issues
3. Verify hardware: Try OpenBCI GUI as baseline test