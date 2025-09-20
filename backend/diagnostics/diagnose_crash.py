#!/usr/bin/env python3
"""
Diagnose OpenBCI Board Crash Issues
Tests which commands cause the blue LED to turn off
"""
import serial
import time
import sys

def test_command(ser, command, description):
    """Test a single command and see if board crashes"""
    print(f"\n📝 Testing: {description}")
    print(f"   Command: {command}")

    # Clear buffer
    ser.reset_input_buffer()

    # Send command
    ser.write(command)

    # Wait and check for response
    time.sleep(1.0)

    response_bytes = ser.read(100)

    if response_bytes:
        print(f"   ✅ Got response: {response_bytes[:20].hex()}")

        # Check if it's just 0xFF
        if response_bytes == b'\xff' * len(response_bytes):
            print("   ⚠️  Only 0xFF acknowledgments")
        else:
            print("   📊 Contains data!")

        print("   👁️  CHECK: Is blue LED still on?")
        return True
    else:
        print("   ❌ No response")
        print("   ⚠️  CHECK: Blue LED may be OFF - board crashed?")
        return False

    input("   Press Enter to continue...")

def main():
    port = "/dev/cu.usbserial-DM01MV82"
    baudrate = 230400

    print("=" * 70)
    print("🔍 OPENBCI CRASH DIAGNOSTICS")
    print("=" * 70)
    print("This will test which commands cause your board to crash")
    print("Watch the blue LED on the board!")
    print("=" * 70)

    try:
        print("\n🔌 Connecting...")
        ser = serial.Serial(port, baudrate, timeout=1.0)
        print("✅ Connected")

        input("\n👁️  Verify blue LED is ON, then press Enter...")

        # Test commands in order of likelihood to work
        test_commands = [
            (b'v', "Version query (safest)"),
            (b'?', "Help command"),
            (b'd', "Default settings"),
            (b'D', "Query register settings"),
            (b'c', "Query channel settings"),
            (b'b', "Start streaming (risky)"),
            (b's', "Stop streaming"),
        ]

        working_commands = []
        crashing_commands = []

        for cmd, desc in test_commands:
            works = test_command(ser, cmd, desc)

            if works:
                working_commands.append((cmd, desc))
            else:
                crashing_commands.append((cmd, desc))
                print("\n⚠️  Board may have crashed!")
                print("Steps to recover:")
                print("1. Press RESET button on board")
                print("2. Wait for blue LED")
                print("3. Press Enter to continue")
                input()

                # Reconnect
                ser.close()
                time.sleep(1)
                ser = serial.Serial(port, baudrate, timeout=1.0)

        # Summary
        print("\n" + "=" * 70)
        print("📊 DIAGNOSTIC RESULTS")
        print("=" * 70)

        if working_commands:
            print("\n✅ SAFE COMMANDS:")
            for cmd, desc in working_commands:
                print(f"   {cmd} - {desc}")

        if crashing_commands:
            print("\n❌ CRASHING COMMANDS:")
            for cmd, desc in crashing_commands:
                print(f"   {cmd} - {desc}")

        print("\n💡 CONCLUSIONS:")
        if len(crashing_commands) > len(working_commands):
            print("⚠️  Board firmware is unstable")
            print("   - Most commands cause crashes")
            print("   - Likely firmware corruption")
            print("   - Best to use listen-only mode")
        elif b'b' in [c[0] for c in crashing_commands]:
            print("⚠️  Streaming command crashes board")
            print("   - Cannot use normal streaming")
            print("   - Must capture passive data only")
        else:
            print("✅ Board relatively stable")
            print("   - Some commands work")
            print("   - May be able to stream with care")

        ser.close()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())