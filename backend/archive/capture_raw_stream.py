#!/usr/bin/env python3
"""
Capture and analyze raw data stream from OpenBCI
Shows exactly what the board is sending
"""
import serial
import time
import sys
from collections import Counter

def main():
    port = "/dev/cu.usbserial-DM01MV82"
    baudrate = 230400

    print("=" * 70)
    print("📡 RAW DATA CAPTURE - OpenBCI Hardware Analysis")
    print("=" * 70)
    print(f"Port: {port}")
    print(f"Baud: {baudrate}")
    print("Duration: 5 seconds")
    print("=" * 70)

    try:
        # Connect
        print("\n🔌 Connecting...")
        ser = serial.Serial(
            port=port,
            baudrate=baudrate,
            timeout=0.1,
            bytesize=8,
            parity='N',
            stopbits=1
        )

        print("✅ Connected!")
        time.sleep(1)

        # Clear buffers
        ser.reset_input_buffer()

        # Capture data for 5 seconds
        print("\n📥 Capturing raw data stream...")
        print("─" * 70)

        start_time = time.time()
        all_bytes = []
        byte_counter = Counter()

        while time.time() - start_time < 5:
            if ser.in_waiting > 0:
                data = ser.read(ser.in_waiting)
                all_bytes.extend(data)

                for byte in data:
                    byte_counter[byte] += 1

                # Show live progress
                sys.stdout.write(f"\r  Captured: {len(all_bytes)} bytes")
                sys.stdout.flush()

            time.sleep(0.001)

        print(f"\n✅ Capture complete: {len(all_bytes)} total bytes")
        print("─" * 70)

        # Analysis
        print("\n📊 DATA ANALYSIS:")
        print("─" * 70)

        if all_bytes:
            # Byte frequency analysis
            print("\n1. BYTE FREQUENCY (top 10):")
            for byte_val, count in byte_counter.most_common(10):
                percent = (count / len(all_bytes)) * 100
                print(f"   0x{byte_val:02X}: {count:5d} times ({percent:5.1f}%)")

            # Pattern detection
            print("\n2. PATTERN DETECTION:")

            # Check for 0xFF dominance
            ff_count = byte_counter[0xFF]
            ff_percent = (ff_count / len(all_bytes)) * 100
            print(f"   0xFF bytes: {ff_percent:.1f}% of stream")

            # Check for OpenBCI packet markers
            a0_count = byte_counter[0xA0]
            c0_count = byte_counter[0xC0]
            if a0_count > 0 or c0_count > 0:
                print(f"   0xA0 (packet start): {a0_count} occurrences")
                print(f"   0xC0 (packet end): {c0_count} occurrences")

                if a0_count > 0 and c0_count > 0:
                    print("   ✅ Standard OpenBCI packet markers detected!")
            else:
                print("   ❌ No standard packet markers (0xA0/0xC0) found")

            # Show first 100 bytes as hex
            print("\n3. FIRST 100 BYTES (HEX):")
            first_100 = all_bytes[:min(100, len(all_bytes))]
            for i in range(0, len(first_100), 20):
                chunk = first_100[i:i+20]
                hex_str = " ".join([f"{b:02X}" for b in chunk])
                print(f"   {i:03d}: {hex_str}")

            # Check for repeating patterns
            print("\n4. REPEATING PATTERNS:")
            if len(all_bytes) >= 33:
                # Check for 33-byte packet structure
                potential_packets = 0
                for i in range(len(all_bytes) - 33):
                    if all_bytes[i] == 0xA0 and all_bytes[i+32] == 0xC0:
                        potential_packets += 1

                if potential_packets > 0:
                    print(f"   Found {potential_packets} potential 33-byte packets")
                else:
                    print("   No 33-byte packet structure detected")

            # Check data variability
            unique_bytes = len(byte_counter)
            print(f"\n5. DATA CHARACTERISTICS:")
            print(f"   Unique byte values: {unique_bytes}/256")
            print(f"   Data rate: {len(all_bytes)/5:.1f} bytes/second")

            if unique_bytes < 10:
                print("   ⚠️  Low variability - possible communication issue")
            elif ff_percent > 80:
                print("   ⚠️  Mostly 0xFF - board in acknowledgment-only mode")
            elif a0_count > 0 and c0_count > 0:
                print("   ✅ Looks like valid OpenBCI data stream!")
            else:
                print("   ❓ Non-standard data format detected")

        else:
            print("❌ No data captured!")
            print("\nPossible issues:")
            print("- Board not powered on")
            print("- USB connection problem")
            print("- Board needs reset")

        ser.close()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1

    print("\n" + "=" * 70)
    print("RECOMMENDATIONS:")

    if all_bytes:
        if ff_percent > 80:
            print("1. Board firmware is in legacy mode (0xFF acknowledgments)")
            print("2. Radio link between board and dongle has failed")
            print("3. Firmware update required for full functionality")
            print("4. Current mode provides minimal data only")
        elif a0_count > 0 and c0_count > 0:
            print("1. Board appears to be sending valid packets!")
            print("2. Try using real_data_streaming.py for full streaming")
        else:
            print("1. Data format is non-standard")
            print("2. May need different baudrate or configuration")
    else:
        print("1. Check physical connections")
        print("2. Power cycle the board")
        print("3. Verify port permissions")

    print("=" * 70)
    return 0

if __name__ == "__main__":
    sys.exit(main())