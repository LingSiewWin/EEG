#!/usr/bin/env python3
"""
Quick hardware debug script for OpenBCI
"""
import glob
from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds

def debug_openbci():
    print("🔍 OpenBCI Hardware Debug")
    print("=" * 40)

    # Check available ports
    patterns = ["/dev/tty.usbserial-*", "/dev/cu.usbserial-*"]
    all_ports = []
    for pattern in patterns:
        ports = glob.glob(pattern)
        all_ports.extend(ports)

    print(f"📡 Found {len(all_ports)} potential serial ports:")
    for port in all_ports:
        print(f"   - {port}")

    if not all_ports:
        print("❌ No serial ports found. Check USB connection.")
        return

    # Try different board types
    board_types = [
        (BoardIds.CYTON_BOARD, "Cyton 8-channel"),
        (BoardIds.CYTON_DAISY_BOARD, "Cyton+Daisy 16-channel"),
        (BoardIds.GANGLION_BOARD, "Ganglion 4-channel")
    ]

    for port in all_ports:
        print(f"\n🔌 Testing port: {port}")

        for board_id, board_name in board_types:
            try:
                print(f"   Trying {board_name}...")
                params = BrainFlowInputParams()
                params.serial_port = port
                params.timeout = 5  # Short timeout for testing

                board = BoardShim(board_id, params)
                board.prepare_session()
                print(f"   ✅ {board_name} connected successfully!")

                # Get board info
                sampling_rate = BoardShim.get_sampling_rate(board_id)
                eeg_channels = BoardShim.get_eeg_channels(board_id)
                print(f"   📊 Sampling rate: {sampling_rate}Hz")
                print(f"   📈 EEG channels: {len(eeg_channels)} channels")

                board.release_session()
                return board_id, port, board_name

            except Exception as e:
                print(f"   ❌ {board_name} failed: {e}")

    print("\n💡 Troubleshooting Tips:")
    print("1. Check board power (blue LED solid)")
    print("2. Check transmission (red LED blinking)")
    print("3. Try power cycling the board")
    print("4. Try different USB port")
    print("5. Use DEMO_MODE=true for testing")

if __name__ == "__main__":
    debug_openbci()