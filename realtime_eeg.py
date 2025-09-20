#!/usr/bin/env python3
import serial
import struct
import time
import sys

def parse_channel_data(three_bytes):
    """Convert 3 bytes to microvolts"""
    val = (three_bytes[0] << 16) | (three_bytes[1] << 8) | three_bytes[2]
    if val & 0x800000:  # negative number
        val = val - 0x1000000
    return val * 0.02235  # scale factor to μV

def main():
    ser = serial.Serial("/dev/cu.usbserial-DM01MV82", 115200, timeout=0.1)
    time.sleep(1)

    # Initialize board
    ser.write(b's')  # stop first
    time.sleep(0.5)
    ser.reset_input_buffer()
    ser.write(b'd')  # default settings
    time.sleep(0.5)
    ser.write(b'b')  # begin streaming

    print("\033[2J\033[H")  # Clear screen
    print("=" * 60)
    print("REAL-TIME EEG STREAMING - 16 CHANNELS")
    print("=" * 60)

    packet = []
    packet_count = 0
    last_display = time.time()

    while True:
        if ser.in_waiting:
            data = ser.read(ser.in_waiting)

            for byte in data:
                packet.append(byte)

                # Look for complete 33-byte packet
                if len(packet) >= 33:
                    # Find packet boundaries
                    if 0xA0 in packet and 0xC0 in packet:
                        start_idx = packet.index(0xA0)
                        if start_idx + 32 < len(packet) and packet[start_idx + 32] == 0xC0:
                            # Valid packet found!
                            valid_packet = packet[start_idx:start_idx + 33]
                            packet_count += 1

                            # Parse all 16 channels (Cyton + Daisy)
                            channels = []

                            # First 8 channels from Cyton
                            for i in range(8):
                                idx = 1 + (i * 3)
                                channel_bytes = valid_packet[idx:idx + 3]
                                channels.append(parse_channel_data(channel_bytes))

                            # Display update every 100ms
                            if time.time() - last_display > 0.1:
                                print("\033[2J\033[H")  # Clear screen
                                print("=" * 60)
                                print(f"REAL-TIME EEG - PACKET #{packet_count}")
                                print(f"Time: {time.strftime('%H:%M:%S')}")
                                print("=" * 60)

                                # Display channels with bar graph
                                for i, val in enumerate(channels):
                                    # Scale for visualization (-100 to +100 μV range)
                                    bar_val = int((val + 100) * 20 / 200)
                                    bar = '█' * max(0, min(bar_val, 20))

                                    print(f"Ch {i+1:2d}: {val:7.2f} μV |{bar:20s}|")

                                print("-" * 60)
                                print("Press Ctrl+C to stop")
                                last_display = time.time()

                            # Reset packet buffer
                            packet = packet[start_idx + 33:]
                        else:
                            # Remove processed bytes
                            packet = packet[1:]
                    else:
                        # Buffer overflow protection
                        if len(packet) > 100:
                            packet = packet[-33:]

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nStopped.")
    except Exception as e:
        print(f"Error: {e}")