#!/usr/bin/env python3
"""
Advanced EEG Decoder for OpenBCI with Intermittent Connection
Handles partial packets and real electrode data when worn
"""
import serial
import time
import sys
import numpy as np
from datetime import datetime
from collections import deque
import struct

class OpenBCIDecoder:
    def __init__(self):
        self.port = "/dev/cu.usbserial-DM01MV82"
        self.baudrate = 230400

        # Packet detection
        self.packet_buffer = bytearray()
        self.packet_size = 33
        self.sync_byte_start = 0xA0
        self.sync_byte_end = 0xC0

        # Data storage
        self.eeg_buffer = deque(maxlen=500)
        self.raw_buffer = deque(maxlen=1000)

        # Statistics
        self.packet_count = 0
        self.byte_count = 0
        self.error_count = 0
        self.wearing_detected = False

    def detect_packet_structure(self, data):
        """Analyze data stream for packet boundaries"""
        # Look for OpenBCI packet markers
        if self.sync_byte_start in data and self.sync_byte_end in data:
            start_idx = data.index(self.sync_byte_start)
            end_idx = data.index(self.sync_byte_end)

            if end_idx > start_idx and (end_idx - start_idx) == 32:
                return True, start_idx
        return False, -1

    def parse_eeg_value(self, three_bytes):
        """Convert 3-byte OpenBCI format to microvolts"""
        if len(three_bytes) != 3:
            return 0.0

        # Combine 3 bytes into 24-bit value
        value = (three_bytes[0] << 16) | (three_bytes[1] << 8) | three_bytes[2]

        # Handle two's complement
        if value >= 0x800000:
            value -= 0x1000000

        # Convert to microvolts (gain = 24x for Cyton)
        return value * 0.02235

    def decode_packet(self, packet):
        """Decode a complete 33-byte OpenBCI packet"""
        if len(packet) != 33:
            return None

        if packet[0] != self.sync_byte_start or packet[32] != self.sync_byte_end:
            return None

        # Extract sample number
        sample_num = packet[1]

        # Extract 8 channels (3 bytes each)
        channels = []
        for i in range(8):
            start = 2 + (i * 3)
            three_bytes = packet[start:start+3]
            value = self.parse_eeg_value(three_bytes)
            channels.append(value)

        return {
            'sample_num': sample_num,
            'channels': channels,
            'timestamp': time.time()
        }

    def process_raw_stream(self, data):
        """Process raw byte stream, handling partial packets"""
        self.packet_buffer.extend(data)

        decoded_samples = []

        # Try to find and extract complete packets
        while len(self.packet_buffer) >= 33:
            # Look for start byte
            if self.sync_byte_start in self.packet_buffer:
                start_idx = self.packet_buffer.index(self.sync_byte_start)

                # Remove bytes before start
                if start_idx > 0:
                    self.packet_buffer = self.packet_buffer[start_idx:]

                # Check if we have a complete packet
                if len(self.packet_buffer) >= 33:
                    # Check for end byte at correct position
                    if self.packet_buffer[32] == self.sync_byte_end:
                        # Extract and decode packet
                        packet = bytes(self.packet_buffer[:33])
                        decoded = self.decode_packet(packet)

                        if decoded:
                            decoded_samples.append(decoded)
                            self.packet_count += 1

                        # Remove processed packet
                        self.packet_buffer = self.packet_buffer[33:]
                    else:
                        # End byte not where expected, skip this start byte
                        self.packet_buffer = self.packet_buffer[1:]
                else:
                    # Not enough data for complete packet
                    break
            else:
                # No start byte found, clear buffer
                self.packet_buffer.clear()
                break

        return decoded_samples

    def analyze_signal_quality(self, channels):
        """Analyze if signal indicates electrodes are on head"""
        if not channels:
            return "NO_SIGNAL"

        # Calculate signal metrics
        values = np.array(channels)
        mean_amplitude = np.mean(np.abs(values))
        std_amplitude = np.std(values)
        max_amplitude = np.max(np.abs(values))

        # Detection criteria
        if max_amplitude < 1.0:
            return "NOT_CONNECTED"
        elif max_amplitude > 200:
            return "ARTIFACT"
        elif 10 < mean_amplitude < 100 and std_amplitude > 5:
            return "GOOD_SIGNAL"
        elif mean_amplitude < 10:
            return "WEAK_SIGNAL"
        else:
            return "CHECKING"

    def run(self):
        """Main streaming loop"""
        print("=" * 80)
        print("🧠 ADVANCED EEG DECODER - OpenBCI Cyton")
        print("=" * 80)
        print(f"Port: {self.port}")
        print(f"Baud: {self.baudrate}")
        print("\n💡 TIPS:")
        print("- Ensure electrodes are properly positioned on scalp")
        print("- Wet electrodes provide better signal")
        print("- Movement creates artifacts")
        print("=" * 80)

        try:
            # Connect
            print("\n🔌 Connecting...")
            ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=0.1,
                bytesize=8,
                parity='N',
                stopbits=1
            )
            print("✅ Connected!")

            # Clear buffers
            ser.reset_input_buffer()
            time.sleep(1)

            # Try to start streaming
            print("📡 Attempting to start data stream...")
            ser.write(b'b')  # Start command
            time.sleep(0.5)

            print("\n📊 STREAMING - Press Ctrl+C to stop\n")

            # Main loop
            start_time = time.time()
            last_display = time.time()
            display_interval = 0.5

            while True:
                try:
                    # Read available data
                    if ser.in_waiting > 0:
                        raw_data = ser.read(ser.in_waiting)
                        self.byte_count += len(raw_data)

                        # Store raw bytes for analysis
                        self.raw_buffer.extend(raw_data)

                        # Try to decode packets
                        samples = self.process_raw_stream(raw_data)

                        # Store decoded samples
                        for sample in samples:
                            self.eeg_buffer.append(sample)

                    # Display update
                    current_time = time.time()
                    if current_time - last_display >= display_interval:
                        # Clear screen
                        print("\033[H\033[J", end='')

                        # Header
                        print("=" * 80)
                        print(f"🧠 LIVE EEG DATA - {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
                        print("=" * 80)

                        # Connection status
                        elapsed = current_time - start_time
                        byte_rate = self.byte_count / elapsed if elapsed > 0 else 0

                        print(f"\n📡 CONNECTION STATUS:")
                        print(f"   Data rate: {byte_rate:.1f} bytes/sec")
                        print(f"   Packets decoded: {self.packet_count}")
                        print(f"   Total bytes: {self.byte_count}")

                        # Analyze recent data
                        if self.packet_count > 0 and self.eeg_buffer:
                            # Show latest sample
                            latest = self.eeg_buffer[-1]

                            print(f"\n📊 LATEST SAMPLE (Packet #{latest['sample_num']}):")

                            # Analyze signal quality
                            quality = self.analyze_signal_quality(latest['channels'])

                            # Quality indicator
                            quality_indicators = {
                                "GOOD_SIGNAL": "✅ Excellent - Electrodes detecting brain activity!",
                                "WEAK_SIGNAL": "⚠️  Weak - Check electrode contact",
                                "ARTIFACT": "⚡ Artifact - Too much movement/noise",
                                "NOT_CONNECTED": "❌ No signal - Electrodes not on head?",
                                "CHECKING": "🔍 Analyzing signal quality..."
                            }

                            print(f"\n🎯 Signal Quality: {quality_indicators.get(quality, quality)}")

                            # Display channels
                            print(f"\n📈 CHANNEL VALUES (μV):")
                            for i, value in enumerate(latest['channels']):
                                # Create bar visualization
                                bar_length = int(abs(value) / 5)
                                bar = "█" * min(bar_length, 40)

                                # Color coding based on amplitude
                                if abs(value) > 100:
                                    status = "⚡"  # High amplitude
                                elif abs(value) < 5:
                                    status = "💤"  # Very low
                                else:
                                    status = "📊"  # Normal

                                print(f"   CH{i+1}: {status} {value:8.2f} μV  {bar}")

                            # Statistics
                            all_values = [ch for s in list(self.eeg_buffer)[-10:] for ch in s['channels']]
                            if all_values:
                                print(f"\n📈 STATISTICS (last 10 packets):")
                                print(f"   Mean amplitude: {np.mean(np.abs(all_values)):.2f} μV")
                                print(f"   Std deviation: {np.std(all_values):.2f} μV")
                                print(f"   Max amplitude: {np.max(np.abs(all_values)):.2f} μV")

                            # Wearing detection
                            if quality == "GOOD_SIGNAL" and not self.wearing_detected:
                                self.wearing_detected = True
                                print("\n🎉 DEVICE DETECTED ON HEAD! Getting real EEG data!")

                        elif byte_rate > 0:
                            # Getting data but no valid packets yet
                            print(f"\n⏳ Receiving data but no valid packets decoded yet...")
                            print(f"   Bytes in buffer: {len(self.packet_buffer)}")

                            # Show raw data pattern
                            if self.raw_buffer:
                                recent = list(self.raw_buffer)[-20:]
                                hex_str = " ".join([f"{b:02X}" for b in recent])
                                print(f"\n   Recent bytes: {hex_str}")

                                # Check for packet markers
                                if 0xA0 in recent:
                                    print("   ✅ Found start marker (0xA0)")
                                if 0xC0 in recent:
                                    print("   ✅ Found end marker (0xC0)")
                        else:
                            print("\n⚠️  No data received. Check:")
                            print("   1. Is the device worn on head?")
                            print("   2. Are electrodes making good contact?")
                            print("   3. Try pressing board RESET button")

                        last_display = current_time

                    time.sleep(0.001)

                except KeyboardInterrupt:
                    break
                except Exception as e:
                    print(f"\n⚠️  Error: {e}")
                    self.error_count += 1

            # Cleanup
            ser.write(b's')  # Stop streaming
            ser.close()

        except Exception as e:
            print(f"\n❌ Fatal error: {e}")
            return 1

        # Summary
        print("\n" + "=" * 80)
        print("📊 SESSION SUMMARY")
        print("=" * 80)
        print(f"Total packets decoded: {self.packet_count}")
        print(f"Total bytes received: {self.byte_count}")
        print(f"Errors encountered: {self.error_count}")

        if self.wearing_detected:
            print("\n✅ Successfully detected brain signals!")
            print("The device IS working when worn properly!")
        elif self.byte_count > 0:
            print("\n⚠️  Received data but no clear brain signals detected")
            print("This could mean electrodes need better positioning")

        return 0

if __name__ == "__main__":
    decoder = OpenBCIDecoder()
    sys.exit(decoder.run())