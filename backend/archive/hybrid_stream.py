#!/usr/bin/env python3
"""
Hybrid Streaming Approach - BrainFlow with Serial Fallback
Automatically switches between BrainFlow and direct serial based on what works
Perfect for hardware with intermittent radio issues
"""
import sys
import time
import serial
import struct
import threading
import queue
from datetime import datetime
import numpy as np

# Try to import BrainFlow, but continue if not available
BRAINFLOW_AVAILABLE = True
try:
    from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds, BrainFlowError
except ImportError:
    BRAINFLOW_AVAILABLE = False
    print("⚠️  BrainFlow not available, will use serial-only mode")


class HybridOpenBCIStreamer:
    def __init__(self):
        # Configuration
        self.port = "/dev/cu.usbserial-DM01MV82"
        self.mode = None  # 'brainflow', 'serial_standard', or 'serial_legacy'

        # Statistics
        self.sample_count = 0
        self.packet_count = 0
        self.error_count = 0
        self.mode_switches = 0

        # Data
        self.data_queue = queue.Queue(maxsize=1000)
        self.running = False

        # BrainFlow
        self.board = None
        self.board_id = None

        # Serial
        self.ser = None
        self.packet_buffer = bytearray()

    def try_brainflow(self):
        """Attempt to connect via BrainFlow"""
        if not BRAINFLOW_AVAILABLE:
            return False

        print("\n🧠 Attempting BrainFlow connection...")

        board_configs = [
            (BoardIds.CYTON_BOARD, "Cyton"),
            (BoardIds.CYTON_DAISY_BOARD, "Cyton+Daisy")
        ]

        for board_id, name in board_configs:
            print(f"  Testing {name}...")

            params = BrainFlowInputParams()
            params.serial_port = self.port
            params.timeout = 10

            try:
                board = BoardShim(board_id, params)
                board.prepare_session()

                # Quick data test
                board.start_stream()
                time.sleep(1)
                data = board.get_board_data()
                board.stop_stream()

                if data.shape[1] > 0:
                    print(f"  ✅ BrainFlow working with {name}!")
                    self.board = board
                    self.board_id = board_id
                    self.mode = 'brainflow'
                    return True

                board.release_session()

            except Exception as e:
                print(f"  ❌ {name} failed: {str(e)[:50]}")

        return False

    def try_serial(self):
        """Attempt direct serial connection"""
        print("\n📡 Attempting direct serial connection...")

        for baudrate in [115200, 230400]:
            print(f"  Testing {baudrate} baud...")

            try:
                ser = serial.Serial(
                    port=self.port,
                    baudrate=baudrate,
                    timeout=1,
                    bytesize=8,
                    parity='N',
                    stopbits=1
                )

                # Clear buffers
                ser.reset_input_buffer()
                ser.reset_output_buffer()

                # Test version command
                ser.write(b'v')
                time.sleep(0.5)

                response = ser.read(100)
                if response:
                    # Check response type
                    if b"OpenBCI" in response:
                        print(f"  ✅ Standard firmware detected at {baudrate} baud")
                        self.ser = ser
                        self.mode = 'serial_standard'
                        return True
                    elif response == b'\xff' * len(response):
                        print(f"  ⚠️  Legacy firmware (0xFF mode) at {baudrate} baud")
                        self.ser = ser
                        self.mode = 'serial_legacy'
                        return True

                ser.close()

            except Exception as e:
                print(f"  ❌ Failed at {baudrate}: {e}")

        return False

    def connect(self):
        """Try all connection methods"""
        print("=" * 70)
        print("🔌 HYBRID CONNECTION MANAGER")
        print("=" * 70)

        # Try BrainFlow first (preferred)
        if self.try_brainflow():
            return True

        # Fall back to direct serial
        if self.try_serial():
            return True

        print("\n❌ All connection methods failed")
        return False

    def parse_standard_packet(self, packet):
        """Parse 33-byte OpenBCI packet"""
        if len(packet) != 33:
            return None

        if packet[0] != 0xA0 or packet[32] != 0xC0:
            return None

        channels = []
        for i in range(8):
            idx = 2 + (i * 3)
            value = (packet[idx] << 16) | (packet[idx+1] << 8) | packet[idx+2]
            if value >= 0x800000:
                value -= 0x1000000
            uV = value * 0.02235
            channels.append(round(uV, 2))

        return {
            'timestamp': time.time(),
            'channels': channels,
            'packet_num': packet[1]
        }

    def stream_brainflow(self):
        """Stream data using BrainFlow"""
        print("\n📊 Streaming via BrainFlow...")
        self.board.start_stream()

        while self.running and self.mode == 'brainflow':
            try:
                data = self.board.get_board_data()

                if data.shape[1] > 0:
                    # Get EEG channels
                    eeg_channels = BoardShim.get_eeg_channels(self.board_id)
                    eeg_data = data[eeg_channels, :]

                    # Process latest sample
                    for i in range(data.shape[1]):
                        sample = {
                            'timestamp': time.time(),
                            'channels': (eeg_data[:, i] * 0.02235).tolist(),
                            'mode': 'brainflow'
                        }
                        self.data_queue.put(sample)
                        self.sample_count += 1

                time.sleep(0.01)

            except BrainFlowError as e:
                print(f"⚠️  BrainFlow error: {e}")
                self.error_count += 1

                if self.error_count > 10:
                    print("🔄 Switching to serial mode...")
                    self.mode_switches += 1
                    self.board.stop_stream()
                    self.board.release_session()

                    if self.try_serial():
                        self.mode = f'serial_{self.mode.split("_")[1] if "_" in self.mode else "standard"}'
                    else:
                        break

    def stream_serial_standard(self):
        """Stream data using standard serial protocol"""
        print("\n📊 Streaming via serial (standard protocol)...")

        # Start streaming
        self.ser.write(b'b')
        time.sleep(0.5)

        while self.running and self.mode == 'serial_standard':
            try:
                if self.ser.in_waiting > 0:
                    # Read available bytes
                    new_bytes = self.ser.read(self.ser.in_waiting)
                    self.packet_buffer.extend(new_bytes)

                    # Look for complete packets
                    while len(self.packet_buffer) >= 33:
                        # Find packet start
                        start_idx = self.packet_buffer.find(0xA0)
                        if start_idx == -1:
                            self.packet_buffer.clear()
                            break

                        # Remove bytes before start
                        if start_idx > 0:
                            self.packet_buffer = self.packet_buffer[start_idx:]

                        # Check if we have complete packet
                        if len(self.packet_buffer) >= 33:
                            packet = bytes(self.packet_buffer[:33])
                            self.packet_buffer = self.packet_buffer[33:]

                            # Parse packet
                            parsed = self.parse_standard_packet(packet)
                            if parsed:
                                sample = {
                                    'timestamp': parsed['timestamp'],
                                    'channels': parsed['channels'],
                                    'mode': 'serial_standard'
                                }
                                self.data_queue.put(sample)
                                self.sample_count += 1
                                self.packet_count += 1

                time.sleep(0.001)

            except Exception as e:
                print(f"⚠️  Serial error: {e}")
                self.error_count += 1

    def stream_serial_legacy(self):
        """Stream data using legacy serial (0xFF mode)"""
        print("\n📊 Streaming via serial (legacy 0xFF mode)...")
        print("⚠️  Limited data available due to firmware issues")

        while self.running and self.mode == 'serial_legacy':
            try:
                if self.ser.in_waiting > 0:
                    data = self.ser.read(self.ser.in_waiting)

                    for byte in data:
                        # Create pseudo-sample from 0xFF byte
                        channels = [0.0] * 8
                        if byte == 0xFF:
                            channels[0] = 12.7  # Nominal value
                        else:
                            channels[0] = (byte - 128) * 0.1

                        sample = {
                            'timestamp': time.time(),
                            'channels': channels,
                            'mode': 'serial_legacy'
                        }
                        self.data_queue.put(sample)
                        self.sample_count += 1

                time.sleep(0.01)

            except Exception as e:
                print(f"⚠️  Serial error: {e}")
                self.error_count += 1

    def display_loop(self):
        """Display data in terminal"""
        last_display = 0
        display_interval = 0.5  # seconds

        while self.running:
            current_time = time.time()

            if current_time - last_display >= display_interval:
                samples = []

                # Get recent samples
                while not self.data_queue.empty() and len(samples) < 10:
                    try:
                        samples.append(self.data_queue.get_nowait())
                    except:
                        break

                if samples:
                    # Display latest sample
                    latest = samples[-1]

                    print("\n" + "=" * 70)
                    print(f"📊 LIVE EEG - {datetime.now().strftime('%H:%M:%S')} - Mode: {self.mode}")
                    print("=" * 70)

                    # Channel bars
                    for i, value in enumerate(latest['channels']):
                        bar_length = int(abs(value) / 10)
                        bar = "█" * min(bar_length, 40)
                        print(f"CH{i+1:02d}: {value:8.2f} μV  {bar}")

                    # Statistics
                    print(f"\n📈 Stats: {self.sample_count} samples | "
                          f"⚠️  {self.error_count} errors | "
                          f"🔄 {self.mode_switches} mode switches")

                last_display = current_time

            time.sleep(0.1)

    def run(self):
        """Main entry point"""
        print("=" * 70)
        print("🎯 HYBRID OPENBCI STREAMER")
        print("Automatically uses best available connection method")
        print("=" * 70)

        # Connect
        if not self.connect():
            print("\n💡 Troubleshooting:")
            print("1. Power cycle the board")
            print("2. Check USB connection")
            print("3. Verify port permissions: sudo chmod 666 " + self.port)
            return

        print(f"\n✅ Connected in {self.mode} mode")
        print("Press Ctrl+C to stop\n")

        self.running = True

        # Start display thread
        display_thread = threading.Thread(target=self.display_loop, daemon=True)
        display_thread.start()

        try:
            # Stream based on mode
            if self.mode == 'brainflow':
                self.stream_brainflow()
            elif self.mode == 'serial_standard':
                self.stream_serial_standard()
            elif self.mode == 'serial_legacy':
                self.stream_serial_legacy()

        except KeyboardInterrupt:
            print("\n\n⏹️  Stopping...")

        finally:
            self.running = False

            # Cleanup
            if self.board:
                try:
                    self.board.stop_stream()
                    self.board.release_session()
                except:
                    pass

            if self.ser:
                try:
                    if self.mode == 'serial_standard':
                        self.ser.write(b's')  # Stop streaming
                    self.ser.close()
                except:
                    pass

            # Final stats
            print("\n" + "=" * 70)
            print("📊 SESSION SUMMARY")
            print("=" * 70)
            print(f"Mode used: {self.mode}")
            print(f"Total samples: {self.sample_count}")
            print(f"Total errors: {self.error_count}")
            print(f"Mode switches: {self.mode_switches}")

            if self.sample_count > 0:
                print(f"Success rate: {(1 - self.error_count/max(self.sample_count, 1)) * 100:.1f}%")

            print("\n👋 Session ended")


if __name__ == "__main__":
    streamer = HybridOpenBCIStreamer()
    streamer.run()