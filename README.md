# EEG Love Detection System - ETHGlobal Project

Real-time brain data streaming and analysis system using OpenBCI hardware for emotional response detection with zkProof integration potential.

## 🎯 Project Overview

This system captures real EEG (electroencephalography) data from an OpenBCI Cyton board, streams it via WebSocket to a Next.js frontend, performs neuroscience-based love detection analysis, and provides entry points for zero-knowledge proof generation on brain data.

### Core Features
- **Real-time EEG streaming** at 250Hz from 8 channels
- **Love detection algorithm** based on frontal alpha asymmetry and arousal levels
- **Image-based emotional response** testing with 5 test images
- **WebSocket architecture** for low-latency data streaming
- **zkProof-ready** data structure for on-chain verification

## 🏗️ System Architecture

```
┌─────────────────┐
│  OpenBCI Cyton  │ (Hardware: 8-channel EEG @ 250Hz)
│   USB Serial    │
└────────┬────────┘
         │ PySerial (115200 baud)
         ↓
┌─────────────────┐
│  Backend Server │ (Python: server.py)
│   - Parse packets│ [ZKPROOF: Raw data entry]
│   - Scale to μV │
│   - Queue data  │
└────────┬────────┘
         │ WebSocket (port 8765)
         ↓
┌─────────────────┐
│    Frontend     │ (Next.js + React)
│  - Visualization│
│  - Analysis UI  │
│  - Image tests  │
└─────────────────┘
```

## 📦 Repository Structure

```
eeg-streaming-project/
├── backend/
│   ├── server.py           # Main WebSocket server
│   ├── cli_streamer.py     # CLI tool for debugging
│   └── eeg_processor.py    # Signal processing algorithms
├── frontend/
│   ├── pages/
│   │   ├── index.js        # Main dashboard
│   │   └── image-analysis.js
│   ├── components/
│   │   ├── EEGDashboard.js
│   │   └── ImageLoveAnalysis.js
│   └── public/
│       └── photo/          # Test images (1-5)
├── requirements.txt        # Python dependencies
├── package.json           # Node dependencies
└── README.md              # This file
```

## 🚀 Quick Start

### Prerequisites
- OpenBCI Cyton board connected via USB
- Python 3.9+
- Node.js 14+

### Installation

```bash
# Clone repository
git clone <repo-url>
cd eeg-streaming-project

# Install Python dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd frontend
npm install
cd ..
```

### Running the System

1. **Start Backend Server**
```bash
cd backend
python server.py

# Expected output:
# ✓ OpenBCI connected (Blue+Red lights should be ON)
# WebSocket URL: ws://localhost:8765
```

2. **Start Frontend** (new terminal)
```bash
cd frontend
npm run dev

# Access at http://localhost:3000
```

3. **CLI Streamer** (optional - for debugging)
```bash
cd backend
python cli_streamer.py

# Shows real-time EEG values in terminal
# Useful for verifying hardware connection
```

## 🧠 EEG Data Structure for Smart Contract Integration

### Raw Data Packet Format
Each WebSocket message contains:
```javascript
{
  "type": "eeg",
  "timestamp": 1695123456.789,     // Unix timestamp
  "packet_num": 1234,               // Sequential packet ID
  "channels": [                     // 8 channels in μV
    12.5, -8.3, 15.2, -3.1,
    7.8, -11.4, 9.6, -5.2
  ],
  "status": "streaming"
}
```

### Analysis Result Format
```javascript
{
  "love_score": 85.5,               // 0-100 scale
  "category": "Love at First Sight",
  "components": {
    "frontal_asymmetry": 72.3,      // Emotional approach
    "arousal": 81.2,                // Beta/Gamma activity
    "attention_p300": 65.8           // Attention level
  },
  "raw_values": {
    "faa": 0.0234,                  // Raw asymmetry value
    "avg_arousal": 45.67,           // μV amplitude
    "p300_amplitude": 12.34         // P300 peak
  }
}
```

### zkProof Integration Points

The backend server (`backend/server.py`) has marked entry points for zkProof integration:

1. **Raw Data Capture Point** (Line ~90-100 in `backend/server.py`)
```python
# [ZKPROOF: Raw data point]
# This is WHERE the raw EEG data is available
data = {
    'type': 'eeg',
    'timestamp': time.time(),
    'packet_num': packet_count,
    'channels': channels,  # 8 channels, values in μV
    'status': 'streaming'
}

# DATA QUEUE: This queue holds all EEG packets
self.data_queue.put_nowait(json.dumps(data))
```

2. **How to Access Data for zkProof**

**Option A: Hook into the Data Queue**
```python
# In backend/server.py, modify the serial_reader() method:
if channels:
    # Original data packet
    data = {
        'type': 'eeg',
        'timestamp': time.time(),
        'packet_num': packet_count,
        'channels': channels,
        'status': 'streaming'
    }

    # ADD YOUR ZKPROOF HERE
    # Example: Send to your zkProof generator
    if hasattr(self, 'zk_handler'):
        self.zk_handler.process_eeg_data(data)

    # Continue normal flow
    self.data_queue.put_nowait(json.dumps(data))
```

**Option B: Add WebSocket Endpoint**
```python
# In backend/server.py, add to process_analysis_request():
async def process_analysis_request(self, websocket, request_data):
    if request_data.get('type') == 'get_raw_data':
        # Send last N packets for zkProof
        recent_data = self.captured_packets[-1000:]  # Last 1000 packets

        response = {
            'type': 'raw_data_batch',
            'data': recent_data,
            'count': len(recent_data)
        }
        await websocket.send(json.dumps(response))

    elif request_data.get('type') == 'analyze':
        # Existing analysis code...
```

**Option C: Export Data Stream**
```python
# Add a data export method in backend/server.py:
def export_for_zkproof(self):
    """Export EEG data for zkProof generation"""
    return {
        'packets': self.captured_packets,
        'timestamp_start': self.start_time,
        'timestamp_end': time.time(),
        'sampling_rate': 250,
        'channels': 8,
        'scale_factor': self.scale_factor
    }
```

3. **Analysis Result for Verification** (Line ~145)
```python
# [ZKPROOF: Entry point for verifiable computation]
analysis_result = self.processor.calculate_love_score(channels_data)

# ADD PROOF GENERATION HERE
# proof = generate_zkproof(analysis_result, channels_data)
# return both result and proof to frontend
```

### Suggested zkProof Implementation

For the smart contract engineer, consider these approaches:

1. **Commitment Scheme**: Hash each data packet on arrival
2. **Merkle Tree**: Build proof tree of sequential packets
3. **Computation Proof**: Prove love score calculation without revealing raw EEG
4. **Threshold Proofs**: Prove score > threshold without exact value

Example integration:
```python
from zkproof_lib import ZKProver  # Your ZK library

class VerifiableEEGProcessor:
    def __init__(self):
        self.prover = ZKProver()
        self.commitment_tree = []

    def process_with_proof(self, eeg_data):
        # Commit to raw data
        commitment = self.prover.commit(eeg_data)
        self.commitment_tree.append(commitment)

        # Compute with proof
        result = self.calculate_love_score(eeg_data)
        proof = self.prover.prove_computation(
            inputs=eeg_data,
            computation=self.calculate_love_score,
            output=result
        )

        return result, proof, commitment
```

## 🔧 Hardware Setup

### OpenBCI Configuration
1. Connect Cyton board via USB
2. Set board switch to "PC" position
3. Verify port:
   ```bash
   # macOS
   ls /dev/cu.usbserial-*

   # Linux
   ls /dev/ttyUSB*

   # Windows
   # Check Device Manager for COM port
   ```
4. Update port in `backend/server.py` line 244

### LED Indicators
- **Blue only**: Board powered, not streaming
- **Blue + Red**: Active streaming mode
- **No lights**: Check USB connection

## 📊 Signal Processing Pipeline

### 1. Bandpass Filter (1-45 Hz)
Removes noise and artifacts outside EEG range

### 2. Frontal Alpha Asymmetry (FAA)
```
FAA = log(Right_Frontal_Alpha) - log(Left_Frontal_Alpha)
Positive FAA → Approach emotion (attraction)
Negative FAA → Withdrawal emotion
```

### 3. Frequency Band Analysis
- **Delta** (0.5-4 Hz): Deep sleep, unconscious
- **Theta** (4-8 Hz): Drowsiness, meditation
- **Alpha** (8-12 Hz): Relaxed, eyes closed
- **Beta** (12-30 Hz): Active thinking, arousal
- **Gamma** (30-45 Hz): High-level cognition

### 4. Love Score Calculation
```
Love Score = 0.4 × FAA_score + 0.3 × Arousal + 0.3 × P300_attention
```

## 🛠️ Development

### Adding New Analysis Algorithms
1. Extend `backend/eeg_processor.py`
2. Add new methods to `EEGProcessor` class
3. Call from `process_analysis_request()` in server

### WebSocket API

**Client → Server:**
```javascript
ws.send(JSON.stringify({
  type: 'analyze',
  data: capturedEEGPackets
}))
```

**Server → Client:**
- Real-time data: `{type: 'eeg', ...}`
- Analysis results: `{type: 'analysis_result', ...}`
- Status updates: `{type: 'status', ...}`

## ⚠️ Troubleshooting

### No Data Streaming
1. Check OpenBCI lights (should be blue + red)
2. Verify serial port in `backend/server.py`
3. Ensure board switch is in "PC" position
4. Try power cycling the board

### Port Already in Use
```bash
lsof -i :8765
kill <PID>
```

### Wrong μV Values
- Expected range: ±100μV
- If seeing ±40,000μV, check scale factor (should be 0.02235/1000)

## 📚 Key Files for Smart Contract Team

1. **`backend/server.py`**: Main data flow, see `[ZKPROOF]` markers
2. **`backend/eeg_processor.py`**: Analysis algorithms to verify
3. **`backend/cli_streamer.py`**: CLI tool for testing hardware connection
4. **Data flow**: `serial_reader()` → `parse_packet()` → `data_queue` → `broadcast_data()`

## 🤝 Team Collaboration

### For Smart Contract Engineer - Data Access Guide

**Where to Get EEG Data:**
1. **File**: `backend/server.py`
2. **Method**: `serial_reader()` (line ~80-120)
3. **Data Structure**: `self.data_queue` contains JSON strings of EEG packets

**Quick Integration Example:**
```python
# Add this to backend/server.py after line 90
# where data packet is created

# Your zkProof hook
from your_zk_library import ZKProofGenerator

class OpenBCIWebSocketServer:
    def __init__(self):
        # ... existing code ...
        self.zk_generator = ZKProofGenerator()
        self.proof_batch = []

    def serial_reader(self):
        # ... existing code ...
        if channels:
            data = {
                'type': 'eeg',
                'timestamp': time.time(),
                'packet_num': packet_count,
                'channels': channels,
                'status': 'streaming'
            }

            # ZKPROOF: Collect data for proof
            self.proof_batch.append(data)

            # Generate proof every 100 packets
            if len(self.proof_batch) >= 100:
                proof = self.zk_generator.create_proof(self.proof_batch)
                # Store or send proof
                self.latest_proof = proof
                self.proof_batch = []

            # Continue normal flow
            self.data_queue.put_nowait(json.dumps(data))
```

**Data Flow Summary:**
- Hardware → Serial Port → `parse_packet()` → **[YOUR ZKPROOF HERE]** → WebSocket → Frontend
- Each packet: ~4ms (250Hz)
- 8 channels per packet
- Values in μV range (±100)

### For Full Stack Engineer
- WebSocket on port 8765
- Frontend components are modular (React)
- State management via React hooks
- Chart.js for visualization

### For UI/UX Developers
- Components in `frontend/components/`
- Styling via inline styles (can migrate to CSS modules)
- Image assets in `frontend/public/photo/`
- Real-time updates via WebSocket subscription

## 📄 Dependencies

### Python (backend)
```
pyserial==3.5      # OpenBCI communication
websockets==11.0   # WebSocket server
numpy==1.24.3      # Numerical processing
scipy==1.10.1      # Signal processing
```

### Node.js (frontend)
```
next==13.4.0       # React framework
react==18.2.0      # UI library
chart.js==4.3.0    # Data visualization
react-chartjs-2    # React Chart.js wrapper
```

## 🔐 Security Notes

- No PHI/PII stored (only anonymous EEG data)
- WebSocket currently unencrypted (add WSS for production)
- Consider rate limiting for analysis requests
- Add authentication for multi-user deployment

## 📈 Performance

- Sampling rate: 250Hz (4ms between packets)
- Latency: <50ms typical (serial + WebSocket)
- Frontend updates: 100Hz max (10ms throttle)
- Analysis computation: <100ms for 5-second capture

## 🚢 Deployment Checklist

- [ ] Update serial port for production hardware
- [ ] Add environment variables for configuration
- [ ] Implement WSS (secure WebSocket)
- [ ] Add error recovery for hardware disconnection
- [ ] Implement data persistence if needed
- [ ] Add zkProof generation
- [ ] Deploy smart contracts
- [ ] Frontend build optimization

## Debug

WebSocket issues: See `backend/server.py` connection handler
Frontend issues: Check browser console for errors

---

**Note**: This system uses REAL brain data. No fake/demo data. The analysis is based on peer-reviewed neuroscience research but should be considered experimental.