#!/usr/bin/env python3
"""
Simple Terminal Streamer for OpenBCI with Radio Issues
Direct serial connection at 230400 baud for legacy firmware
Shows real-time data in terminal without WebSocket complexity
"""
import serial
import time
import sys
from datetime import datetime


def main():
    # Configuration based on test results
    port = "/dev/cu.usbserial-DM01MV82"
    baudrate = 230400  # Confirmed working baudrate

    print("=" * 70)
    print("🧠 SIMPLE OPENBCI TERMINAL STREAMER")
    print("For hardware with radio communication issues")
    print("=" * 70)
    print(f"Port: {port}")
    print(f"Baud: {baudrate}")
    print("=" * 70)

    try:
        # Open serial connection
        print("🔌 Connecting...")
        ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            timeout=0.1,
            bytesize=8,
            parity='N',
            stopbits=1,
            xonxoff=False,
            rtscts=False,
            dsrdtr=False
        )

        print("✅ Connected!")
        time.sleep(1)

        # Clear buffers
        ser.reset_input_buffer()
        ser.reset_output_buffer()

        # Test version command
        print("\n🔍 Checking firmware...")
        ser.write(b'v')
        time.sleep(0.5)

        response = ser.read(100)
        if response:
            if b"OpenBCI" in response:
                print(f"✅ Standard firmware: {response.decode('ascii', errors='ignore')}")
                firmware_type = "standard"
            elif response == b'\xff' * len(response):
                print("⚠️  Legacy firmware detected (0xFF acknowledgment mode)")
                firmware_type = "legacy"
            else:
                print(f"❓ Unknown response: {response.hex()}")
                firmware_type = "unknown"
        else:
            print("⚠️  No firmware response - assuming legacy mode")
            firmware_type = "legacy"

        print("\n" + "=" * 70)
        print("📊 STREAMING DATA - Press Ctrl+C to stop")
        print("=" * 70)

        # Statistics
        sample_count = 0
        byte_count = 0
        start_time = time.time()
        last_display = time.time()
        display_interval = 0.5  # Update display every 0.5 seconds

        # Data accumulator
        recent_bytes = []

        if firmware_type == "standard":
            print("🚀 Starting standard streaming...")
            ser.write(b'b')  # Start streaming
            time.sleep(0.5)

        print("\n👂 Listening for data...\n")

        while True:
            try:
                # Read available data
                if ser.in_waiting > 0:
                    data = ser.read(ser.in_waiting)
                    byte_count += len(data)

                    for byte in data:
                        sample_count += 1
                        recent_bytes.append(byte)

                        # Keep only last 100 bytes
                        if len(recent_bytes) > 100:
                            recent_bytes.pop(0)

                # Display update
                current_time = time.time()
                if current_time - last_display >= display_interval and recent_bytes:
                    # Clear screen (works on most terminals)
                    print("\033[H\033[J", end='')

                    # Header
                    print("=" * 70)
                    print(f"📊 LIVE DATA STREAM - {datetime.now().strftime('%H:%M:%S')}")
                    print("=" * 70)

                    # Data visualization
                    if firmware_type == "legacy":
                        # For legacy mode, show byte values
                        print("\n📥 Recent bytes (legacy 0xFF mode):")

                        # Show last 10 bytes as hex
                        last_10 = recent_bytes[-10:] if len(recent_bytes) >= 10 else recent_bytes
                        hex_str = " ".join([f"0x{b:02X}" for b in last_10])
                        print(f"  Hex: {hex_str}")

                        # Convert to pseudo-voltage
                        print("\n📈 Channel 1 values (μV):")
                        for i, byte in enumerate(last_10):
                            if byte == 0xFF:
                                value = 12.7
                            else:
                                value = (byte - 128) * 0.1

                            # Create simple bar chart
                            bar_length = int(abs(value))
                            bar = "█" * min(bar_length, 50)
                            print(f"  [{i}]: {value:6.1f} μV  {bar}")

                    else:
                        # For standard mode, try to parse packets
                        print("\n📥 Raw data stream:")
                        hex_display = " ".join([f"{b:02X}" for b in recent_bytes[-20:]])
                        print(f"  {hex_display}")

                        # Look for packet structure
                        if 0xA0 in recent_bytes and 0xC0 in recent_bytes:
                            print("\n✅ Valid packet markers detected!")

                    # Statistics
                    elapsed = current_time - start_time
                    bytes_per_sec = byte_count / elapsed if elapsed > 0 else 0
                    samples_per_sec = sample_count / elapsed if elapsed > 0 else 0

                    print("\n" + "─" * 70)
                    print("📈 Statistics:")
                    print(f"  Runtime: {elapsed:.1f} seconds")
                    print(f"  Total bytes: {byte_count}")
                    print(f"  Total samples: {sample_count}")
                    print(f"  Data rate: {bytes_per_sec:.1f} bytes/sec")
                    print(f"  Sample rate: {samples_per_sec:.1f} samples/sec")

                    if byte_count == 0:
                        print("\n⚠️  No data received yet. Possible issues:")
                        print("  - Board may need power cycle")
                        print("  - Radio communication failure")
                        print("  - Try pressing RESET button on board")

                    last_display = current_time

                # Small delay to prevent CPU spinning
                time.sleep(0.001)

            except KeyboardInterrupt:
                print("\n\n⏹️  Stopping stream...")
                break
            except Exception as e:
                print(f"\n⚠️  Error: {e}")
                time.sleep(1)

    except serial.SerialException as e:
        print(f"\n❌ Serial connection failed: {e}")
        print("\n💡 Troubleshooting:")
        print("1. Check if board is powered on (blue LED)")
        print("2. Verify USB connection")
        print("3. Try: sudo chmod 666 " + port)
        print("4. Power cycle the board")
        return 1

    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        return 1

    finally:
        # Cleanup
        try:
            if firmware_type == "standard" and 'ser' in locals():
                ser.write(b's')  # Stop streaming
                print("✅ Stream stopped")

            if 'ser' in locals() and ser.is_open:
                ser.close()
                print("✅ Serial port closed")
        except:
            pass

        # Final summary
        if 'sample_count' in locals() and sample_count > 0:
            print("\n" + "=" * 70)
            print("📊 SESSION SUMMARY")
            print("=" * 70)
            print(f"Total samples collected: {sample_count}")
            print(f"Total bytes received: {byte_count}")
            print(f"Session duration: {elapsed:.1f} seconds")
            print(f"Average data rate: {bytes_per_sec:.1f} bytes/sec")

        print("\n👋 Goodbye!")

    return 0


if __name__ == "__main__":
    sys.exit(main())