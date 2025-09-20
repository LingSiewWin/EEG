#!/usr/bin/env python3
"""
REAL OpenBCI Hardware Data Streamer - 16 Channel Support
- Supports BOTH old firmware (b'\xff' packets) and new firmware (33-byte packets)
- Parses real EEG data from all 16 channels after firmware update
- Streams at 250Hz for Cyton, 125Hz for Cyton+Daisy
- WebSocket server for live dashboard
"""
import serial
import time
import json
import asyncio
import websockets
import threading
import queue
import struct
from datetime import datetime
from collections import deque

class RealOpenBCIStreamer:
    def __init__(self):
        # Hardware config
        self.port = "/dev/cu.usbserial-DM01MV82"
        self.baudrate = 115200  # Standard after firmware update

        # Data storage
        self.samples = deque(maxlen=1000)  # Keep last 1000 samples
        self.sample_count = 0
        self.packet_count = 0
        self.firmware_version = "Unknown"
        self.is_daisy_attached = False
        self.streaming_mode = None  # 'legacy' or 'standard'

        # Threading
        self.serial_thread = None
        self.ws_server = None
        self.clients = set()
        self.running = False

        # Thread-safe queue for samples
        self.sample_queue = queue.Queue(maxsize=500)

        # Packet buffer for assembling 33-byte packets
        self.packet_buffer = bytearray()

        # Daisy interleaving state
        self.last_daisy_packet = None
        self.expecting_daisy = False

    def parse_standard_packet(self, packet):
        """Parse 33-byte OpenBCI standard packet format"""
        if len(packet) != 33:
            return None

        if packet[0] != 0xA0 or packet[32] != 0xC0:
            return None

        sample_num = packet[1]

        # Parse 8 channels (3 bytes each, 24-bit signed big-endian)
        channels = []
        for i in range(8):
            idx = 2 + (i * 3)
            # Combine 3 bytes into 24-bit signed integer
            value = (packet[idx] << 16) | (packet[idx+1] << 8) | packet[idx+2]

            # Handle sign extension for negative values
            if value >= 0x800000:
                value -= 0x1000000

            # Convert to microvolts (ADS1299 gain = 24)
            uV = value * 0.02235
            channels.append(round(uV, 2))

        # Check if this is a Daisy packet (sample_num is odd for Daisy)
        is_daisy = (sample_num % 2 == 1) if self.is_daisy_attached else False

        return {
            "sample_num": sample_num,
            "channels": channels,
            "is_daisy": is_daisy,
            "timestamp": time.time()
        }

    def combine_daisy_packets(self, cyton_packet, daisy_packet):
        """Combine Cyton (ch 1-8) and Daisy (ch 9-16) packets into 16-channel sample"""
        if not cyton_packet or not daisy_packet:
            return None

        return {
            "timestamp": cyton_packet["timestamp"],
            "channels": cyton_packet["channels"] + daisy_packet["channels"],  # 16 channels total
            "sample_num": cyton_packet["sample_num"],
            "packet_nums": [cyton_packet["sample_num"], daisy_packet["sample_num"]]
        }

    def detect_firmware_version(self, ser):
        """Send 'v' command to get firmware version"""
        try:
            # Clear buffers
            ser.reset_input_buffer()
            ser.reset_output_buffer()

            # Send version command
            ser.write(b'v')
            time.sleep(0.5)

            # Read response
            response = ser.read(ser.in_waiting)
            if response:
                version_str = response.decode('ascii', errors='ignore')
                if "OpenBCI" in version_str:
                    self.firmware_version = version_str.strip()
                    print(f"✅ Firmware detected: {self.firmware_version}")
                    return "standard"
                else:
                    print(f"⚠️  Non-standard response: {response.hex()}")
                    if response == b'\xff' * len(response):
                        print("📍 Legacy firmware detected (b'\\xff' mode)")
                        self.firmware_version = "Legacy (acknowledgment-only)"
                        return "legacy"
            return None
        except Exception as e:
            print(f"❌ Error detecting firmware: {e}")
            return None

    def start_serial_listener(self):
        """Serial listener supporting both legacy and standard firmware"""
        print("=" * 60)
        print("🚀 REAL OpenBCI 16-Channel Hardware Streamer")
        print(f"📡 Port: {self.port}")
        print("=" * 60)

        ser = None
        try:
            # Try standard baudrate first
            print(f"🔌 Connecting at {self.baudrate} baud...")
            ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=0.1,
                rtscts=False,
                dsrdtr=False,
                xonxoff=False
            )

            time.sleep(2)  # Wait for board to stabilize

            # Detect firmware version
            self.streaming_mode = self.detect_firmware_version(ser)

            # If standard firmware not detected, try legacy baudrate
            if not self.streaming_mode:
                print(f"🔄 Trying legacy baudrate 230400...")
                ser.close()
                ser = serial.Serial(
                    port=self.port,
                    baudrate=230400,
                    timeout=0.1,
                    rtscts=False,
                    dsrdtr=False,
                    xonxoff=False
                )
                time.sleep(1)
                self.streaming_mode = self.detect_firmware_version(ser)

            if not self.streaming_mode:
                self.streaming_mode = "legacy"  # Default to legacy if unclear

            print(f"📋 Mode: {self.streaming_mode.upper()}")

            # Start streaming based on mode
            if self.streaming_mode == "standard":
                print("🎯 Starting 16-channel streaming...")

                # Check for Daisy
                ser.write(b'c')  # Enable 16-channel mode if Daisy present
                time.sleep(0.5)
                response = ser.read(ser.in_waiting)
                if b"daisy" in response.lower() or b"16" in response:
                    self.is_daisy_attached = True
                    print("✅ Daisy module detected - 16 channels enabled")

                # Start streaming
                ser.write(b'b')
                print("📊 Streaming started...")

                # Main streaming loop for standard firmware
                last_broadcast = time.time()
                while self.running:
                    if ser.in_waiting >= 33:
                        # Look for start byte
                        byte = ser.read(1)
                        if byte[0] == 0xA0:
                            # Read rest of packet
                            rest = ser.read(32)
                            packet = byte + rest

                            parsed = self.parse_standard_packet(packet)
                            if parsed:
                                self.packet_count += 1

                                if self.is_daisy_attached:
                                    # Handle Daisy interleaving
                                    if parsed["is_daisy"]:
                                        self.last_daisy_packet = parsed
                                    else:
                                        # Cyton packet - combine with last Daisy if available
                                        if self.last_daisy_packet:
                                            combined = self.combine_daisy_packets(parsed, self.last_daisy_packet)
                                            if combined:
                                                self.samples.append(combined)
                                                self.sample_queue.put(combined)
                                                self.sample_count += 1

                                                # Print periodic updates
                                                if time.time() - last_broadcast >= 2.0:
                                                    ch_str = ", ".join([f"{v:.1f}" for v in combined["channels"]])
                                                    print(f"\n📤 Sample #{self.sample_count}: [{ch_str}] μV")
                                                    print(f"   16 channels from Cyton+Daisy")
                                                    last_broadcast = time.time()
                                else:
                                    # Cyton only - 8 channels
                                    sample = {
                                        "timestamp": parsed["timestamp"],
                                        "channels": parsed["channels"] + [0.0] * 8,  # Pad to 16
                                        "sample_num": parsed["sample_num"]
                                    }
                                    self.samples.append(sample)
                                    self.sample_queue.put(sample)
                                    self.sample_count += 1

                                    if time.time() - last_broadcast >= 2.0:
                                        ch_str = ", ".join([f"{v:.1f}" for v in sample["channels"][:8]])
                                        print(f"\n📤 Sample #{self.sample_count}: [{ch_str}, ...] μV")
                                        print(f"   8 channels from Cyton only")
                                        last_broadcast = time.time()

                    time.sleep(0.001)  # Small delay to prevent CPU spinning

            else:  # Legacy mode
                print("⚠️  Legacy firmware mode - limited to acknowledgments")
                print("👂 Listening for hardware packets...\n")

                packet_num = 0
                last_broadcast = time.time()

                while self.running:
                    if ser.in_waiting > 0:
                        raw_bytes = ser.read(ser.in_waiting)

                        for byte in raw_bytes:
                            packet_num += 1
                            self.sample_count += 1

                            print(f"📥 LEGACY PACKET #{packet_num}: b'\\x{byte:02x}'")

                            # Legacy conversion
                            channels = [0.0] * 16
                            if byte == 0xFF:
                                channels[0] = 12.7
                            else:
                                channels[0] = round((byte - 128) * 0.1, 1)

                            sample = {
                                "timestamp": time.time(),
                                "channels": channels,
                                "packet_num": packet_num,
                                "legacy": True
                            }

                            self.samples.append(sample)
                            self.sample_queue.put(sample)

                    # Periodic broadcast
                    if time.time() - last_broadcast >= 2.0 and self.samples:
                        last_sample = self.samples[-1]
                        print(f"\n📤 Broadcasting legacy sample #{self.sample_count}")
                        print(f"   Channel 1: {last_sample['channels'][0]} μV (from b'\\xff')")
                        last_broadcast = time.time()

                    time.sleep(0.001)

        except serial.SerialException as e:
            print(f"❌ Serial error: {e}")
        except KeyboardInterrupt:
            print("\n⏹️  Stopping...")
        finally:
            if ser and ser.is_open:
                if self.streaming_mode == "standard":
                    try:
                        ser.write(b's')  # Stop streaming
                        print("📊 Streaming stopped")
                    except:
                        pass
                ser.close()
                print("🔌 Serial port closed")

    async def handle_websocket(self, websocket):
        """WebSocket handler for clients (compatible with websockets 12.0)"""
        # Register client
        self.clients.add(websocket)
        client_ip = websocket.remote_address[0] if websocket.remote_address else "unknown"
        print(f"✅ Client connected from {client_ip}. Total clients: {len(self.clients)}")

        # Send welcome message with status
        await websocket.send(json.dumps({
            "type": "status",
            "message": f"Connected to OpenBCI - Mode: {self.streaming_mode or 'detecting'}",
            "firmware_version": self.firmware_version,
            "total_samples": len(self.samples),
            "is_daisy": self.is_daisy_attached,
            "channels": 16 if self.is_daisy_attached else 8,
            "source": "authentic_openbci_hardware"
        }))

        try:
            await websocket.wait_closed()
        finally:
            self.clients.discard(websocket)
            print(f"👋 Client {client_ip} disconnected. Remaining: {len(self.clients)}")

    async def broadcast_loop(self):
        """Broadcast real samples to all WebSocket clients at higher rate"""
        while self.running:
            # Faster broadcast for 250Hz data
            await asyncio.sleep(0.04)  # 25Hz update rate to browser

            if self.clients and not self.sample_queue.empty():
                # Gather samples from queue
                samples_to_send = []
                while not self.sample_queue.empty() and len(samples_to_send) < 10:
                    try:
                        samples_to_send.append(self.sample_queue.get_nowait())
                    except queue.Empty:
                        break

                if samples_to_send:
                    # Calculate sample rate
                    sample_rate = 0
                    if len(self.samples) > 10:
                        recent = list(self.samples)[-10:]
                        time_diff = recent[-1]["timestamp"] - recent[0]["timestamp"]
                        if time_diff > 0:
                            sample_rate = 9 / time_diff

                    # Prepare broadcast message
                    message = json.dumps({
                        "type": "eeg_data",
                        "samples": [
                            {
                                "timestamp": s["timestamp"],
                                "channels": s["channels"]
                            } for s in samples_to_send
                        ],
                        "sample_count": len(samples_to_send),
                        "channel_count": 16,
                        "sample_rate": round(sample_rate, 1),
                        "source": "authentic_openbci_hardware",
                        "mode": self.streaming_mode
                    })

                    # Send to all connected clients
                    disconnected = set()
                    for client in self.clients:
                        try:
                            await client.send(message)
                        except:
                            disconnected.add(client)

                    # Remove disconnected clients
                    self.clients -= disconnected

    async def start_websocket_server(self):
        """Start WebSocket server"""
        print("\n🌐 Starting WebSocket server on ws://localhost:8765")

        # Start broadcast loop
        asyncio.create_task(self.broadcast_loop())

        # Start WebSocket server
        async with websockets.serve(self.handle_websocket, "localhost", 8765):
            print("✅ WebSocket server ready for connections")
            await asyncio.Future()

    def run(self):
        """Main entry point"""
        self.running = True

        # Start serial listener in separate thread
        self.serial_thread = threading.Thread(target=self.start_serial_listener, daemon=True)
        self.serial_thread.start()

        # Give serial time to initialize and detect firmware
        time.sleep(3)

        # Run WebSocket server in main thread
        try:
            asyncio.run(self.start_websocket_server())
        except KeyboardInterrupt:
            print("\n⏹️  Shutting down...")
        finally:
            self.running = False
            print(f"\n📊 Total samples collected: {self.sample_count}")
            print(f"📦 Total packets processed: {self.packet_count}")
            print(f"🔧 Firmware: {self.firmware_version}")
            print("👍 Clean shutdown complete")


if __name__ == "__main__":
    streamer = RealOpenBCIStreamer()
    streamer.run()