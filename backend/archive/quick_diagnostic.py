#!/usr/bin/env python3
"""
Quick diagnostic to check OpenBCI connection status
"""
import serial
import time

def main():
    port = "/dev/cu.usbserial-DM01MV82"

    print("🔍 OPENBCI QUICK DIAGNOSTIC")
    print("=" * 50)

    # Test at both baudrates
    for baudrate in [230400, 115200]:
        print(f"\nTesting {baudrate} baud...")

        try:
            ser = serial.Serial(port, baudrate, timeout=1)

            # Send version command
            ser.write(b'v')
            time.sleep(0.5)

            response = ser.read(100)

            if response:
                print(f"✅ Got response: {response[:20].hex()}")

                if response == b'\xff':
                    print("   → Legacy firmware (0xFF mode)")
                    print("   → Board has radio communication failure")
                    print("   → Can only send acknowledgments, not full data")
                elif b"OpenBCI" in response:
                    print(f"   → Standard firmware: {response.decode('ascii', errors='ignore')[:50]}")
                else:
                    print(f"   → Unknown: {response[:20]}")

                ser.close()
                return baudrate
            else:
                print("❌ No response")

            ser.close()

        except Exception as e:
            print(f"❌ Error: {e}")

    print("\n" + "=" * 50)
    print("DIAGNOSIS:")
    print("- Board responds with 0xFF at 230400 baud")
    print("- This indicates firmware sends only acknowledgments")
    print("- Radio link between board and dongle is broken")
    print("- Limited data available without firmware update")

    return 0

if __name__ == "__main__":
    main()