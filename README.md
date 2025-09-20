# 🧠 OpenBCI Real-Time EEG Streaming Project

**✅ WORKING** - Real brain data streaming from OpenBCI to web browser (NO FAKE DATA)

## 🎯 Current Status (September 20, 2025)

### ✅ What's Working NOW:
- **Hardware Connected**: OpenBCI Cyton streaming real EEG at ~40μV (correct physiological range)
- **WebSocket Server**: Real-time streaming from hardware to browser
- **Next.js Dashboard**: Live visualization of 8 channels with proper scaling
- **Love Detection**: 5-second capture for "love at first sight" analysis
- **No BrainFlow**: Direct PySerial communication (more reliable)

### 📊 Real Data Confirmed:
- **Packet Structure**: 33-byte OpenBCI packets (0xA0 start, 0xC0 end)
- **Sample Rate**: ~250Hz from Cyton board
- **Channel Values**: ±40μV (normal EEG range, NOT ±40,000μV)
- **Blue+Red Lights**: Confirm active streaming mode

## 🚀 Quick Start

### 1. Backend - WebSocket Server
```bash
# Start the real streaming server
python real_stream_server.py

# You should see:
# ✓ OpenBCI CONNECTED - Blue+Red lights should be ON
# WebSocket URL: ws://localhost:8765
```

### 2. Frontend - Next.js Dashboard
```bash
cd frontend
npm install  # First time only
npm run dev

# Open browser to http://localhost:3000
```

## 📁 Project Structure

```
eeg-streaming-project/
├── real_stream_server.py      # ✅ MAIN WebSocket server (WORKING)
├── CORRECT_SCALE.py           # ✅ CLI streamer with correct μV scaling
├── force_stream.py            # ✅ Diagnostic tool (proves packets work)
├── VERIFY_REAL_EEG.py        # ✅ Interactive test (blink/jaw detection)
│
├── frontend/
│   ├── pages/
│   │   └── index.js          # Next.js entry
│   └── components/
│       └── EEGDashboard.js   # ✅ Real-time display + love detection
│
└── docs/
    └── OpenBCI_Setup_Solution.md  # Troubleshooting guide
```

## 💖 Love Detection Feature

Click "CAPTURE 5 SECONDS FOR LOVE DETECTION" button to:
1. Record 5 seconds of brain activity
2. Calculate average amplitude across all channels
3. Get love score:
   - <20μV = 30% (Calm/Neutral)
   - 20-40μV = 60% (Interested)
   - 40-60μV = 80% (Excited)
   - >60μV = 95% (Very Attracted!)

## 🔧 Hardware Setup

- **Device**: OpenBCI Ultracortex Mark IV
- **Board**: Cyton (8 channels) + Daisy (8 channels, not detected yet)
- **Port**: `/dev/cu.usbserial-DM01MV82` (macOS)
- **Baud**: 115200
- **Firmware**: Standard OpenBCI (sends 33-byte packets)

## 🐛 Troubleshooting

### WebSocket Won't Connect
```bash
# Kill all processes and restart
pkill -f python
pkill -f node

# Start backend first, then frontend
python real_stream_server.py
cd frontend && npm run dev
```

### No Data Showing
- Check Blue+Red lights are ON (streaming mode)
- Verify port: `ls /dev/cu.*`
- Board switch must be in "PC" position

### Wrong Values (±40,000μV instead of ±40μV)
- Use `CORRECT_SCALE.py` or `real_stream_server.py`
- Scale factor: 0.02235 / 1000 (NOT just 0.02235)

## 📈 Technical Details

### Packet Format
```python
# 33-byte OpenBCI packet structure
[0xA0]              # Start byte
[packet_counter]    # 1 byte
[channel_1]         # 3 bytes (24-bit)
[channel_2]         # 3 bytes
...
[channel_8]         # 3 bytes
[aux_data]          # 6 bytes
[0xC0]              # End byte
```

### Scaling Formula
```python
# Convert 24-bit ADC to microvolts
raw_24bit = (byte1 << 16) | (byte2 << 8) | byte3
if raw_24bit & 0x800000:  # Handle negative
    raw_24bit -= 0x1000000
microvolts = raw_24bit * (0.02235 / 1000)  # CORRECT scaling
```

## 🎯 Next Steps

- [ ] Enable Daisy board (channels 9-16)
- [ ] Add FFT for frequency analysis
- [ ] Implement proper image-based love matching
- [ ] Add ZK proof for privacy-preserving matching
- [ ] Deploy to production

## ⚠️ Important Notes

1. **NO FAKE DATA**: This uses REAL brain signals from hardware
2. **First Principle**: Real data or nothing - no demo/simulation mode
3. **Correct Range**: Normal EEG is ±50μV, not thousands
4. **Light Indicators**: Blue+Red = streaming, Blue only = idle

---

**Built with**: Python (PySerial), WebSockets, Next.js, React
**Hardware**: OpenBCI Cyton+Daisy 16-channel EEG
**No BrainFlow**: Direct serial for better reliability