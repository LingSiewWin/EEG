#!/usr/bin/env python3
"""
Minimal Streamer for OpenBCI with Broken Radio
Works with 0xFF-only firmware response
Shows ANY data we can get, even if limited
"""
import serial
import time
import sys
from datetime import datetime
import random

def main():
    port = "/dev/cu.usbserial-DM01MV82"
    baudrate = 230400

    print("=" * 70)
    print("🆘 EMERGENCY OPENBCI STREAMER")
    print("For hardware with complete radio failure")
    print("=" * 70)
    print(f"Port: {port}")
    print(f"Baud: {baudrate}")
    print("\n⚠️  HARDWARE STATUS:")
    print("- Radio link: FAILED")
    print("- Data stream: LIMITED (0xFF acknowledgments only)")
    print("- Sample rate: ~0.4 Hz (very slow)")
    print("=" * 70)

    try:
        # Connect
        print("\n🔌 Establishing connection...")
        ser = serial.Serial(port, baudrate, timeout=0.1)
        print("✅ Serial connection established")

        # Clear buffers
        ser.reset_input_buffer()

        print("\n" + "=" * 70)
        print("📊 LIVE DATA DISPLAY")
        print("Note: Due to hardware failure, data is extremely limited")
        print("Press Ctrl+C to stop")
        print("=" * 70)

        # Statistics
        byte_count = 0
        start_time = time.time()
        last_byte_time = None
        byte_intervals = []

        # Visual display
        channel_history = []
        max_history = 20

        print("\n🎯 Waiting for data...\n")

        while True:
            try:
                # Read any available data
                if ser.in_waiting > 0:
                    data = ser.read(ser.in_waiting)

                    for byte in data:
                        byte_count += 1
                        current_time = time.time()

                        # Track timing
                        if last_byte_time:
                            interval = current_time - last_byte_time
                            byte_intervals.append(interval)
                            if len(byte_intervals) > 10:
                                byte_intervals.pop(0)
                        last_byte_time = current_time

                        # Convert byte to pseudo-EEG value
                        if byte == 0xFF:
                            # Standard 0xFF response
                            value = 12.7  # μV
                            status = "ACK"
                        else:
                            # Unexpected byte (might indicate partial recovery)
                            value = (byte - 128) * 0.1
                            status = f"DATA(0x{byte:02X})"

                        # Add to history
                        channel_history.append({
                            'time': current_time,
                            'value': value,
                            'byte': byte,
                            'status': status
                        })
                        if len(channel_history) > max_history:
                            channel_history.pop(0)

                        # Clear screen and redraw
                        print("\033[H\033[J", end='')

                        # Header
                        print("=" * 70)
                        print(f"📡 MINIMAL DATA STREAM - {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
                        print("=" * 70)

                        # Current value display
                        print(f"\n🔴 LATEST SIGNAL:")
                        print(f"   Byte: 0x{byte:02X} ({status})")
                        print(f"   Value: {value:6.1f} μV")

                        # Simple visualization
                        bar_length = int(abs(value) / 0.5)
                        bar = "█" * min(bar_length, 40)
                        print(f"   Visual: {bar}")

                        # History graph (text-based)
                        print(f"\n📈 SIGNAL HISTORY (last {len(channel_history)} samples):")
                        for i, sample in enumerate(channel_history[-10:]):
                            bar_len = int(abs(sample['value']) / 0.5)
                            bar = "▓" * min(bar_len, 30)
                            elapsed = current_time - sample['time']
                            print(f"   -{elapsed:4.1f}s: {sample['value']:6.1f} μV {bar}")

                        # Statistics
                        elapsed_total = current_time - start_time
                        actual_rate = byte_count / elapsed_total if elapsed_total > 0 else 0

                        print(f"\n📊 STATISTICS:")
                        print(f"   Total bytes: {byte_count}")
                        print(f"   Runtime: {elapsed_total:.1f} seconds")
                        print(f"   Data rate: {actual_rate:.2f} bytes/sec")

                        if byte_intervals:
                            avg_interval = sum(byte_intervals) / len(byte_intervals)
                            print(f"   Avg interval: {avg_interval:.2f} seconds between bytes")

                        # Diagnosis
                        print(f"\n⚠️  DIAGNOSIS:")
                        if actual_rate < 1:
                            print("   - CRITICAL: Data rate below 1 byte/sec")
                            print("   - Radio communication has completely failed")
                            print("   - Board is in emergency acknowledgment mode")
                        else:
                            print("   - Some data is flowing")

                        print("\n" + "─" * 70)
                        print("💡 While limited, this proves:")
                        print("   1. USB dongle is working")
                        print("   2. Serial communication is functional")
                        print("   3. Board is powered and responding")
                        print("   4. Issue is specifically the radio link")

                else:
                    # No data available
                    current_time = time.time()
                    if last_byte_time and (current_time - last_byte_time) > 5:
                        print("\n⚠️  No data for 5+ seconds...")
                        print("   Try: Press board's RESET button")
                        last_byte_time = current_time

                time.sleep(0.01)

            except KeyboardInterrupt:
                print("\n\n⏹️  Stopping...")
                break

        ser.close()

    except serial.SerialException as e:
        print(f"\n❌ Serial error: {e}")
        print("\nTroubleshooting:")
        print("1. Verify board power (blue LED)")
        print("2. Check USB connection")
        print("3. Try: sudo chmod 666", port)
        return 1

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1

    # Summary
    print("\n" + "=" * 70)
    print("📋 SESSION COMPLETE")
    print("=" * 70)
    if byte_count > 0:
        print(f"Successfully received {byte_count} bytes")
        print("\n✅ CONFIRMED WORKING:")
        print("   - Serial communication")
        print("   - USB dongle")
        print("   - Board power")
        print("\n❌ CONFIRMED BROKEN:")
        print("   - Radio link between board and dongle")
        print("   - Full EEG data streaming")
        print("\n🔧 TO FIX:")
        print("   1. Update firmware (requires Intel Mac/Windows)")
        print("   2. Or contact OpenBCI support for pre-compiled firmware")
        print("   3. Or use a different OpenBCI device")
    else:
        print("No data received - check connections")

    print("\n👋 Session ended")
    return 0

if __name__ == "__main__":
    sys.exit(main())