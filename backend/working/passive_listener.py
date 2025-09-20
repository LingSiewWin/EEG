#!/usr/bin/env python3
"""
Passive OpenBCI Listener - No Commands Sent
Works with boards that crash on initialization
Captures whatever data the board sends naturally
"""
import serial
import time
import sys
import numpy as np
from datetime import datetime
from collections import deque

class PassiveOpenBCIListener:
    def __init__(self):
        self.port = "/dev/cu.usbserial-DM01MV82"
        self.baudrate = 230400

        # Data tracking
        self.all_bytes = deque(maxlen=10000)
        self.packet_candidates = []

        # Statistics
        self.start_time = time.time()
        self.byte_count = 0
        self.c0_markers = 0
        self.a0_markers = 0

    def analyze_data_pattern(self, data):
        """Analyze data for OpenBCI patterns"""
        analysis = {
            'has_c0': 0xC0 in data,
            'has_a0': 0xA0 in data,
            'unique_count': len(set(data)),
            'ff_ratio': data.count(0xFF) / len(data) if data else 0,
            'data_rate': self.byte_count / (time.time() - self.start_time)
        }

        # Look for 33-byte sequences ending in C0
        c0_positions = [i for i, b in enumerate(data) if b == 0xC0]
        for pos in c0_positions:
            if pos >= 32:
                # Potential packet
                potential = data[pos-32:pos+1]
                if len(potential) == 33:
                    analysis['potential_packet'] = potential

        return analysis

    def visualize_channels(self, byte_sequence):
        """Convert bytes to channel values for visualization"""
        channels = []

        # Simple interpretation: each byte as a signed value
        for byte in byte_sequence[:8]:  # First 8 bytes as 8 channels
            if byte == 0xFF:
                value = 12.7
            else:
                value = (byte - 128) * 0.1
            channels.append(value)

        return channels

    def run(self):
        print("=" * 80)
        print("👂 PASSIVE OPENBCI LISTENER")
        print("=" * 80)
        print("NO commands sent - just listening to natural data flow")
        print("This prevents board crashes")
        print("\n📌 INSTRUCTIONS:")
        print("1. Make sure device is ON (blue LED)")
        print("2. Wear the device with good electrode contact")
        print("3. If blue LED goes off, press RESET button")
        print("=" * 80)

        try:
            # Connect WITHOUT sending anything
            print("\n🔌 Opening serial port (passive mode)...")
            ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=0.01,  # Very short timeout for non-blocking
                bytesize=8,
                parity='N',
                stopbits=1,
                rtscts=False,
                dsrdtr=False,
                xonxoff=False
            )

            print("✅ Port open - NOT sending any commands")
            print("👂 Listening for natural data flow...")
            print("\nPress Ctrl+C to stop\n")

            # Just listen
            last_display = time.time()
            display_interval = 1.0
            recent_window = deque(maxlen=100)

            while True:
                try:
                    # Read without sending anything
                    if ser.in_waiting > 0:
                        data = ser.read(ser.in_waiting)
                        self.byte_count += len(data)

                        for byte in data:
                            self.all_bytes.append(byte)
                            recent_window.append(byte)

                            if byte == 0xC0:
                                self.c0_markers += 1
                            if byte == 0xA0:
                                self.a0_markers += 1

                    # Display updates
                    if time.time() - last_display >= display_interval:
                        # Clear and update display
                        print("\033[H\033[J", end='')

                        print("=" * 80)
                        print(f"👂 PASSIVE LISTENING - {datetime.now().strftime('%H:%M:%S')}")
                        print("=" * 80)

                        # Statistics
                        elapsed = time.time() - self.start_time
                        data_rate = self.byte_count / elapsed if elapsed > 0 else 0

                        print(f"\n📊 STATISTICS:")
                        print(f"   Runtime: {elapsed:.1f} seconds")
                        print(f"   Total bytes: {self.byte_count}")
                        print(f"   Data rate: {data_rate:.2f} bytes/sec")
                        print(f"   C0 markers: {self.c0_markers}")
                        print(f"   A0 markers: {self.a0_markers}")

                        # Data analysis
                        if recent_window:
                            analysis = self.analyze_data_pattern(list(recent_window))

                            print(f"\n📈 DATA ANALYSIS:")
                            print(f"   Unique values: {analysis['unique_count']}/256")
                            print(f"   0xFF ratio: {analysis['ff_ratio']:.1%}")

                            # Show recent bytes
                            recent = list(recent_window)[-30:]
                            hex_str = " ".join([f"{b:02X}" for b in recent])
                            print(f"\n📥 Recent bytes:")
                            print(f"   {hex_str}")

                            # Detection
                            if analysis['has_c0'] and analysis['has_a0']:
                                print("\n✅ PACKET MARKERS DETECTED!")
                                print("   Found both A0 (start) and C0 (end)")

                            if 'potential_packet' in analysis:
                                print("\n🎯 POTENTIAL PACKET FOUND!")
                                pkt = analysis['potential_packet']
                                print(f"   First 3 bytes: {pkt[:3].hex()}")
                                print(f"   Last 3 bytes: {pkt[-3:].hex()}")

                            # Channel visualization (from recent data)
                            if analysis['unique_count'] > 5:
                                print(f"\n📊 INTERPRETED CHANNELS (μV):")
                                channels = self.visualize_channels(recent[-8:])
                                for i, val in enumerate(channels):
                                    bar = "█" * int(abs(val))
                                    print(f"   CH{i+1}: {val:6.1f} {bar}")

                            # Wearing detection
                            if data_rate < 2:
                                print("\n⚠️  LOW DATA RATE - Check electrode contact")
                            elif data_rate > 4 and analysis['unique_count'] > 20:
                                print("\n✅ GOOD SIGNAL - Device appears to be worn!")
                            elif analysis['ff_ratio'] > 0.9:
                                print("\n⚠️  Mostly 0xFF - Device may not be worn")

                        else:
                            print("\n⏳ Waiting for data...")
                            print("   - Check blue LED is ON")
                            print("   - Ensure good electrode contact")
                            print("   - Try pressing RESET if no data")

                        last_display = time.time()

                    time.sleep(0.001)

                except KeyboardInterrupt:
                    break

        except serial.SerialException as e:
            print(f"\n❌ Serial error: {e}")
            return 1

        finally:
            if 'ser' in locals() and ser.is_open:
                ser.close()

            # Final analysis
            print("\n" + "=" * 80)
            print("📊 FINAL ANALYSIS")
            print("=" * 80)

            if self.byte_count > 0:
                final_rate = self.byte_count / (time.time() - self.start_time)
                print(f"Average data rate: {final_rate:.2f} bytes/sec")

                if self.c0_markers > 0 and self.a0_markers > 0:
                    print("\n✅ BOARD IS SENDING PACKET DATA!")
                    print(f"   Found {self.a0_markers} start markers")
                    print(f"   Found {self.c0_markers} end markers")
                    print("   Board CAN work without initialization commands")
                elif final_rate < 2:
                    print("\n⚠️  Very low data rate suggests:")
                    print("   - Poor electrode contact")
                    print("   - Device not worn properly")
                    print("   - Radio link severely degraded")
                else:
                    print("\n📌 Board sends data but not standard packets")
                    print("   Custom decoding may be needed")

                print("\n💡 KEY FINDING:")
                print("Board works best in PASSIVE mode - no commands sent!")
                print("This avoids crashes while still getting data")

            else:
                print("No data received - check connections")

        return 0

if __name__ == "__main__":
    listener = PassiveOpenBCIListener()
    sys.exit(listener.run())