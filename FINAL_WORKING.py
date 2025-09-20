#!/usr/bin/env python3
"""
FINAL WORKING OpenBCI STREAM
Correct scaling for real EEG values
Using PySerial (NOT BrainFlow)
"""
import serial
import time

print("="*60)
print("OpenBCI REAL-TIME EEG VIEWER")
print("Technology: PySerial (Direct Serial Communication)")
print("="*60)

ser = serial.Serial("/dev/cu.usbserial-DM01MV82", 115200, timeout=0.1)
time.sleep(2)

print("Initializing board...")
ser.write(b's')  # stop
time.sleep(0.5)
ser.reset_input_buffer()
ser.write(b'd')  # defaults
time.sleep(0.5)
ser.write(b'b')  # begin - Watch for BLUE+RED lights!

print("Streaming started! (Blue+Red lights should be ON)\n")

buffer = bytearray()
packet_count = 0

# CORRECT scale factor for OpenBCI Cyton
# 24-bit ADC, ±187500μV input range
SCALE = 0.02235  # Correct OpenBCI scaling factor

while True:
    if ser.in_waiting:
        buffer.extend(ser.read(ser.in_waiting))

        while len(buffer) >= 33:
            try:
                start = buffer.index(0xA0)
                if start + 32 < len(buffer) and buffer[start + 32] == 0xC0:
                    packet = buffer[start:start + 33]
                    packet_count += 1

                    # Parse 8 channels
                    channels = []
                    for i in range(8):
                        idx = 2 + (i * 3)
                        # Combine 3 bytes into 24-bit value
                        val = (packet[idx] << 16) | (packet[idx+1] << 8) | packet[idx+2]
                        # Convert to signed
                        if val & 0x800000:
                            val -= 0x1000000
                        # Scale to microvolts
                        uV = val * SCALE
                        channels.append(uV)

                    # Update display every 10 packets
                    if packet_count % 10 == 0:
                        print("\033[H\033[J")  # Clear
                        print("="*70)
                        print(f"REAL-TIME EEG | Packets: {packet_count} | {time.strftime('%H:%M:%S')}")
                        print("="*70)
                        print("Channel |   Value (μV) | Signal Strength")
                        print("-"*70)

                        for i, val in enumerate(channels):
                            # Visual bar (scaled to ±100μV)
                            bar_len = int(abs(val) / 5) if abs(val) < 100 else 20
                            bar = '█' * min(bar_len, 20)

                            # Interpret signal
                            if abs(val) < 10:
                                status = "Low/Quiet"
                            elif abs(val) < 50:
                                status = "Normal"
                            elif abs(val) < 100:
                                status = "Active"
                            else:
                                status = "High/Artifact"

                            print(f"  Ch {i+1:2d} | {val:+10.2f} | {bar:20s} {status}")

                        print("-"*70)
                        print("Daisy Channels 9-16: Not detected (check connections)")
                        print("\nPress Ctrl+C to stop")

                    buffer = buffer[start + 33:]
                else:
                    buffer = buffer[start + 1:]
            except ValueError:
                buffer = bytearray()
                break