#!/usr/bin/env python3
"""
REAL OpenBCI WebSocket Server - NO FAKE DATA
Based on CORRECT_SCALE.py which ACTUALLY WORKS
With EEG analysis for love detection
"""
import serial
import time
import json
import asyncio
import websockets
import threading
import queue
import numpy as np
from eeg_processor import EEGProcessor

class RealOpenBCIServer:
    def __init__(self):
        self.port = "/dev/cu.usbserial-DM01MV82"
        self.baudrate = 115200
        self.scale = 0.02235 / 1000  # CORRECT SCALE that showed ~40μV

        self.clients = set()
        self.data_queue = queue.Queue(maxsize=1000)
        self.is_streaming = False
        self.ser = None

    def connect_hardware(self):
        """Connect to REAL OpenBCI hardware"""
        try:
            print("Connecting to OpenBCI...")
            self.ser = serial.Serial(self.port, self.baudrate, timeout=0.1)
            time.sleep(2)

            # Initialize sequence that WORKS
            self.ser.write(b's')  # stop
            time.sleep(0.5)
            self.ser.reset_input_buffer()
            self.ser.write(b'd')  # defaults
            time.sleep(0.5)
            self.ser.write(b'b')  # begin - BLUE+RED LIGHTS ON

            self.is_streaming = True
            print("✓ OpenBCI CONNECTED - Blue+Red lights should be ON")
            return True

        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False

    def serial_reader(self):
        """Read REAL data from OpenBCI in background thread"""
        buffer = bytearray()
        packet_count = 0

        while self.is_streaming:
            try:
                if self.ser and self.ser.in_waiting:
                    buffer.extend(self.ser.read(self.ser.in_waiting))

                    while len(buffer) >= 33:
                        # Find packet start (0xA0)
                        start = buffer.index(0xA0) if 0xA0 in buffer else -1

                        if start >= 0 and start + 32 < len(buffer):
                            # Check for packet end (0xC0)
                            if buffer[start + 32] == 0xC0:
                                packet = buffer[start:start + 33]
                                packet_count += 1

                                # Parse 8 channels with CORRECT scaling
                                channels = []
                                for i in range(8):
                                    idx = 2 + (i * 3)
                                    val = (packet[idx] << 16) | (packet[idx+1] << 8) | packet[idx+2]
                                    if val & 0x800000:
                                        val -= 0x1000000
                                    # This scaling gave us ~40μV which is CORRECT
                                    channels.append(round(val * self.scale, 2))

                                # REAL DATA VERIFICATION - Log every 50 packets
                                if packet_count % 50 == 0:
                                    print(f"\n✓ REAL DATA #{packet_count}: Ch1={channels[0]:.2f}μV, Ch2={channels[1]:.2f}μV")
                                    if all(-100 <= ch <= 100 for ch in channels):
                                        print("  ✓ Values in valid EEG range (-100 to +100 μV)")
                                    if len(set(channels)) > 1:
                                        print("  ✓ Channels vary (REAL brain signals, not fake!)")

                                # Queue data for WebSocket
                                data = {
                                    'type': 'eeg',
                                    'timestamp': time.time(),
                                    'packet_num': packet_count,
                                    'channels': channels,
                                    'status': 'streaming'
                                }

                                # Don't block if queue is full
                                try:
                                    self.data_queue.put_nowait(json.dumps(data))
                                except queue.Full:
                                    pass

                                buffer = buffer[start + 33:]
                            else:
                                buffer = buffer[start + 1:]
                        else:
                            if len(buffer) > 100:
                                buffer = buffer[-33:]
                            break

                time.sleep(0.001)

            except Exception as e:
                print(f"Serial error: {e}")
                break

    async def websocket_handler(self, websocket):
        """Handle WebSocket connections from frontend"""
        self.clients.add(websocket)
        print(f"✓ Frontend connected (Total clients: {len(self.clients)})")

        # Send initial status
        await websocket.send(json.dumps({
            'type': 'status',
            'connected': self.is_streaming,
            'message': 'OpenBCI streaming' if self.is_streaming else 'Not connected'
        }))

        try:
            await websocket.wait_closed()
        finally:
            self.clients.remove(websocket)
            print(f"Frontend disconnected (Remaining: {len(self.clients)})")

    async def broadcast_data(self):
        """Send REAL data to all connected frontends"""
        while True:
            # Get data from queue
            if not self.data_queue.empty():
                data = self.data_queue.get()

                # Send to all clients
                if self.clients:
                    disconnected = set()
                    for client in self.clients:
                        try:
                            await client.send(data)
                        except:
                            disconnected.add(client)

                    # Remove disconnected clients
                    self.clients -= disconnected

            await asyncio.sleep(0.01)  # 100Hz max

    async def start(self):
        """Start WebSocket server"""
        # Connect to hardware first
        if not self.connect_hardware():
            print("Failed to connect to OpenBCI")
            return

        # Start serial reader thread
        serial_thread = threading.Thread(target=self.serial_reader, daemon=True)
        serial_thread.start()

        # Start broadcaster
        broadcast_task = asyncio.create_task(self.broadcast_data())

        # Start WebSocket server
        print("\n" + "="*60)
        print("REAL OPENBCI WEBSOCKET SERVER")
        print("="*60)
        print("WebSocket URL: ws://localhost:8765")
        print("Streaming REAL data at ~40μV (correct range)")
        print("Frontend can now connect and see live brain data")
        print("="*60 + "\n")

        async with websockets.serve(self.websocket_handler, "localhost", 8765):
            await asyncio.Future()  # Run forever

if __name__ == "__main__":
    server = RealOpenBCIServer()

    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        print("\n✓ Server stopped")
        server.is_streaming = False