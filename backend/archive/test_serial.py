#!/usr/bin/env python3
"""
Test basic serial communication with OpenBCI device
"""
import serial
import time
import sys

def test_serial_basic():
    ports = ["/dev/cu.usbserial-DM01MV82", "/dev/tty.usbserial-DM01MV82"]
    baud_rates = [115200, 230400, 57600, 9600]

    print("🔍 Testing Basic Serial Communication")
    print("=" * 50)

    for port in ports:
        print(f"\n📡 Testing port: {port}")

        for baud in baud_rates:
            print(f"   Trying baud rate: {baud}")
            try:
                # Test basic serial connection
                with serial.Serial(
                    port=port,
                    baudrate=baud,
                    timeout=2,
                    bytesize=8,
                    parity='N',
                    stopbits=1,
                    xonxoff=False,
                    rtscts=False,
                    dsrdtr=False
                ) as ser:

                    print(f"   ✅ Port opened successfully")

                    # Try to send OpenBCI reset command
                    ser.write(b'v')  # Request board info
                    time.sleep(0.5)

                    # Try to read response
                    if ser.in_waiting > 0:
                        response = ser.read(ser.in_waiting)
                        print(f"   📥 Received: {response}")
                        print(f"   🎯 SUCCESS with {port} at {baud} baud!")
                        return port, baud
                    else:
                        print(f"   ⚠️  No response received")

            except serial.SerialException as e:
                print(f"   ❌ Failed: {e}")
            except Exception as e:
                print(f"   ❌ Error: {e}")

            time.sleep(0.1)

    print("\n💡 If all failed, try:")
    print("1. Power cycle OpenBCI board")
    print("2. Check board is in default mode (not streaming)")
    print("3. Try different USB port")
    print("4. Check macOS permissions")

    return None, None

def test_brainflow_with_settings(port, baud):
    """Test BrainFlow with specific settings"""
    print(f"\n🧠 Testing BrainFlow with {port} at {baud} baud")

    try:
        from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds

        params = BrainFlowInputParams()
        params.serial_port = port
        params.timeout = 10

        # Try different board types
        board_types = [
            (BoardIds.CYTON_BOARD, "Cyton"),
            (BoardIds.CYTON_DAISY_BOARD, "Cyton+Daisy")
        ]

        for board_id, name in board_types:
            print(f"   Testing {name}...")
            try:
                board = BoardShim(board_id, params)
                board.prepare_session()
                print(f"   ✅ {name} connected!")

                # Test brief data collection
                board.start_stream()
                time.sleep(1)
                data = board.get_board_data()
                board.stop_stream()
                board.release_session()

                print(f"   📊 Collected {data.shape[1]} samples")
                print(f"   🎯 SUCCESS: {name} working!")
                return board_id

            except Exception as e:
                print(f"   ❌ {name} failed: {e}")

    except ImportError:
        print("   ⚠️  BrainFlow not available for testing")

    return None

if __name__ == "__main__":
    # Test basic serial first
    port, baud = test_serial_basic()

    if port and baud:
        # Test BrainFlow with successful settings
        board_id = test_brainflow_with_settings(port, baud)
        if board_id:
            print(f"\n🎉 SOLUTION FOUND:")
            print(f"   Port: {port}")
            print(f"   Baud: {baud}")
            print(f"   Board: {board_id}")
    else:
        print("\n❌ No working configuration found")
        print("Hardware troubleshooting may be needed")