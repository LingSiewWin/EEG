#!/usr/bin/env python3
"""
OpenBCI Stream with Reset Recovery
Handles board crashes and requires manual reset
Designed for boards that stop responding after initialization
"""
import serial
import time
import sys
from datetime import datetime
import numpy as np

class ResilientOpenBCIStream:
    def __init__(self):
        self.port = "/dev/cu.usbserial-DM01MV82"
        self.baudrate = 230400

        # State tracking
        self.last_data_time = None
        self.reset_required = False
        self.packet_buffer = bytearray()

        # Statistics
        self.byte_count = 0
        self.valid_packets = 0
        self.reset_count = 0

    def connect_minimal(self):
        """Minimal connection - no commands that might crash board"""
        try:
            print("🔌 Establishing minimal connection...")
            ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=0.1,
                bytesize=8,
                parity='N',
                stopbits=1,
                rtscts=False,
                dsrdtr=False,
                xonxoff=False
            )

            # DON'T send any commands - just listen
            print("✅ Connected in listen-only mode")
            print("⚠️  NOT sending any commands to avoid crashes")

            # Just clear input buffer
            ser.reset_input_buffer()

            return ser

        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return None

    def find_packet_boundaries(self, data):
        """Find OpenBCI packet markers in data stream"""
        packets = []

        # Look for 0xC0 (end marker you found)
        c0_positions = [i for i, byte in enumerate(data) if byte == 0xC0]

        for end_pos in c0_positions:
            # Check if we have enough bytes before it for a packet
            if end_pos >= 32:
                # Look for potential start position
                start_pos = end_pos - 32

                # Could be 0xA0 or other start markers
                potential_packet = data[start_pos:end_pos+1]

                if len(potential_packet) == 33:
                    packets.append(potential_packet)
                    print(f"   📦 Found potential packet: {potential_packet[:3].hex()}...{potential_packet[-3:].hex()}")

        return packets

    def decode_partial_data(self, data):
        """Decode whatever we can from partial data"""
        # Simple interpretation of bytes as channel values
        channels = []
        for i in range(0, len(data), 3):
            if i + 2 < len(data):
                # Treat every 3 bytes as a channel reading
                value = (data[i] << 16) | (data[i+1] << 8) | data[i+2]
                if value >= 0x800000:
                    value -= 0x1000000
                uV = value * 0.02235
                channels.append(uV)

        return channels

    def run(self):
        """Main streaming loop with reset recovery"""
        print("=" * 80)
        print("🔧 RESET-RECOVERY OPENBCI STREAMER")
        print("=" * 80)
        print("Designed for boards that crash after initialization")
        print("\n⚠️  IMPORTANT:")
        print("- Blue LED going off = board crashed")
        print("- Press RESET button when prompted")
        print("- We'll listen without sending commands")
        print("=" * 80)

        ser = self.connect_minimal()
        if not ser:
            return 1

        print("\n📊 LISTENING FOR DATA")
        print("Press Ctrl+C to stop")
        print("=" * 80)

        start_time = time.time()
        last_display = time.time()
        display_interval = 1.0
        no_data_counter = 0

        try:
            while True:
                try:
                    # Read available data WITHOUT sending any commands
                    if ser.in_waiting > 0:
                        data = ser.read(ser.in_waiting)
                        self.byte_count += len(data)
                        self.last_data_time = time.time()
                        no_data_counter = 0

                        # Add to buffer
                        self.packet_buffer.extend(data)

                        # Keep buffer size manageable
                        if len(self.packet_buffer) > 1000:
                            self.packet_buffer = self.packet_buffer[-500:]

                        # Look for packets
                        packets = self.find_packet_boundaries(self.packet_buffer)
                        if packets:
                            self.valid_packets += len(packets)

                    else:
                        no_data_counter += 1

                    # Display update
                    current_time = time.time()
                    if current_time - last_display >= display_interval:
                        # Clear screen
                        print("\033[H\033[J", end='')

                        print("=" * 80)
                        print(f"📡 RESILIENT STREAM - {datetime.now().strftime('%H:%M:%S')}")
                        print("=" * 80)

                        # Connection status
                        elapsed = current_time - start_time
                        byte_rate = self.byte_count / elapsed if elapsed > 0 else 0

                        print(f"\n📊 STATUS:")
                        print(f"   Total bytes: {self.byte_count}")
                        print(f"   Data rate: {byte_rate:.1f} bytes/sec")
                        print(f"   Valid packets found: {self.valid_packets}")
                        print(f"   Resets performed: {self.reset_count}")

                        # Data analysis
                        if self.packet_buffer:
                            recent = list(self.packet_buffer[-40:])

                            print(f"\n📥 RECENT DATA:")
                            hex_str = " ".join([f"{b:02X}" for b in recent[-20:]])
                            print(f"   {hex_str}")

                            # Check for markers
                            if 0xC0 in recent:
                                print("   ✅ Found end marker (0xC0)")
                            if 0xA0 in recent:
                                print("   ✅ Found start marker (0xA0)")

                            # Analyze data characteristics
                            unique = len(set(recent))
                            ff_count = recent.count(0xFF)

                            print(f"\n📈 SIGNAL ANALYSIS:")
                            print(f"   Unique values: {unique}")
                            print(f"   0xFF ratio: {ff_count}/{len(recent)} ({ff_count*100/len(recent):.1f}%)")

                            if unique > 10:
                                print("   ✅ High variability - likely real EEG data!")

                                # Try to decode some channels
                                channels = self.decode_partial_data(bytes(recent))
                                if channels:
                                    print(f"\n   Decoded values (μV): {[f'{v:.1f}' for v in channels[:5]]}")
                            elif ff_count > len(recent) * 0.8:
                                print("   ⚠️  Mostly 0xFF - device may not be worn")

                        # Check if we need reset
                        if no_data_counter > 50:  # ~5 seconds
                            print("\n" + "⚠️ " * 10)
                            print("NO DATA DETECTED - BOARD MAY HAVE CRASHED")
                            print("👉 Press the RESET button on the OpenBCI board")
                            print("⚠️ " * 10)

                            # Wait for reset
                            self.reset_count += 1
                            no_data_counter = 0

                            # Clear buffer after reset
                            self.packet_buffer.clear()
                            ser.reset_input_buffer()

                        last_display = current_time

                    time.sleep(0.01)

                except serial.SerialException as e:
                    print(f"\n❌ Serial error: {e}")
                    print("Attempting to reconnect...")

                    ser.close()
                    time.sleep(2)
                    ser = self.connect_minimal()

                    if not ser:
                        break

                except KeyboardInterrupt:
                    break

        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")

        finally:
            if ser and ser.is_open:
                ser.close()

            # Summary
            print("\n" + "=" * 80)
            print("📊 SESSION SUMMARY")
            print("=" * 80)
            print(f"Total bytes received: {self.byte_count}")
            print(f"Valid packets found: {self.valid_packets}")
            print(f"Resets required: {self.reset_count}")

            if self.byte_count > 0:
                print("\n💡 FINDINGS:")
                if self.valid_packets > 0:
                    print("✅ Device CAN send valid packets")
                if self.reset_count > 0:
                    print("⚠️  Board crashes when commands are sent")
                print("📌 Board works best in listen-only mode")
                print("🔧 Manual resets may be required periodically")

        return 0

if __name__ == "__main__":
    streamer = ResilientOpenBCIStream()
    sys.exit(streamer.run())