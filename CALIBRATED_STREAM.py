#!/usr/bin/env python3
"""
CALIBRATED 16-CHANNEL EEG STREAM
Proper scaling for OpenBCI Cyton+Daisy
"""
import serial
import time
import sys

print("CONNECTING TO OPENBCI...")
ser = serial.Serial("/dev/cu.usbserial-DM01MV82", 115200, timeout=0.1)
time.sleep(2)

print("STARTING STREAM...")
ser.write(b's')  # stop
time.sleep(0.5)
ser.reset_input_buffer()
ser.write(b'd')  # defaults
time.sleep(0.5)
ser.write(b'b')  # begin

print("\n" + "="*60)
print("LIVE EEG - ALL 16 CHANNELS")
print("="*60)

buffer = bytearray()
packet_count = 0
channels = [0.0] * 16

# Correct scale factor for 24-bit ADC with 4.5V reference and gain of 24
SCALE_FACTOR = 4.5 / 24 / (2**23 - 1) * 1000000  # Convert to μV

while True:
    if ser.in_waiting:
        buffer.extend(ser.read(ser.in_waiting))

        while len(buffer) >= 33:
            try:
                start = buffer.index(0xA0)
                if start + 32 < len(buffer) and buffer[start + 32] == 0xC0:
                    packet = buffer[start:start + 33]
                    packet_count += 1

                    # Parse 8 channels from this packet
                    for i in range(8):
                        idx = 2 + (i * 3)
                        val = (packet[idx] << 16) | (packet[idx+1] << 8) | packet[idx+2]
                        if val & 0x800000:
                            val -= 0x1000000
                        channels[i] = val * SCALE_FACTOR

                    # Display every 10 packets (~40Hz update)
                    if packet_count % 10 == 0:
                        print("\033[H\033[J")  # Clear screen
                        print("="*60)
                        print(f"LIVE EEG | Packets: {packet_count} | {time.strftime('%H:%M:%S')}")
                        print("="*60)

                        # Show channels in 2 columns
                        for i in range(8):
                            # Create simple bar visualization
                            val1 = channels[i]
                            val2 = channels[i+8] if i+8 < 16 else 0

                            # Clamp to reasonable range
                            bar1 = int((val1 + 100) / 10) if -100 < val1 < 100 else 0
                            bar2 = int((val2 + 100) / 10) if -100 < val2 < 100 else 0

                            bar1 = '█' * max(0, min(bar1, 20))
                            bar2 = '█' * max(0, min(bar2, 20))

                            print(f"Ch{i+1:2}: {val1:+7.1f}μV |{bar1:20}| Ch{i+9:2}: {val2:+7.1f}μV |{bar2:20}|")

                        print("-"*60)
                        print("Press Ctrl+C to stop")

                    buffer = buffer[start + 33:]
                else:
                    buffer = buffer[start + 1:]
            except ValueError:
                buffer = bytearray()
                break