#!/usr/bin/env python3
"""
CORRECT SCALING FOR OPENBCI
Normal EEG range: ±100μV
"""
import serial
import time
import math

ser = serial.Serial("/dev/cu.usbserial-DM01MV82", 115200, timeout=0.1)
time.sleep(2)

print("Initializing OpenBCI...")
ser.write(b's')
time.sleep(0.5)
ser.reset_input_buffer()
ser.write(b'd')
time.sleep(0.5)
ser.write(b'b')

print("Streaming... (Blue+Red lights ON)\n")

buffer = bytearray()
packet_count = 0

# FIX: Correct scale factor
# Your values are 1000x too high, so divide by 1000
SCALE = 0.02235 / 1000  # This should give proper μV range

while True:
    if ser.in_waiting:
        buffer.extend(ser.read(ser.in_waiting))

        while len(buffer) >= 33:
            try:
                start = buffer.index(0xA0)
                if start + 32 < len(buffer) and buffer[start + 32] == 0xC0:
                    packet = buffer[start:start + 33]
                    packet_count += 1

                    channels = []
                    for i in range(8):
                        idx = 2 + (i * 3)
                        val = (packet[idx] << 16) | (packet[idx+1] << 8) | packet[idx+2]
                        if val & 0x800000:
                            val -= 0x1000000
                        uV = val * SCALE
                        channels.append(uV)

                    if packet_count % 10 == 0:
                        print("\033[H\033[J")
                        print("="*80)
                        print("NORMAL EEG RANGES (for reference):")
                        print("  • Relaxed/Eyes closed: 10-50 μV (Alpha waves)")
                        print("  • Alert/Thinking: 5-30 μV (Beta waves)")
                        print("  • Drowsy: 20-100 μV (Theta waves)")
                        print("  • Muscle artifacts: >100 μV (NOT brain activity)")
                        print("="*80)
                        print(f"YOUR REAL-TIME EEG | Packets: {packet_count}")
                        print("-"*80)

                        for i, val in enumerate(channels):
                            # Determine what type of activity
                            abs_val = abs(val)
                            if abs_val < 5:
                                activity = "Very quiet"
                                bar_char = '░'
                            elif abs_val < 20:
                                activity = "Beta (alert/thinking)"
                                bar_char = '▒'
                            elif abs_val < 50:
                                activity = "Alpha (relaxed)"
                                bar_char = '▓'
                            elif abs_val < 100:
                                activity = "Theta (drowsy)"
                                bar_char = '█'
                            else:
                                activity = "ARTIFACT (muscle/movement)"
                                bar_char = '█'

                            # Visual bar
                            bar_len = int(min(abs_val / 2, 40))
                            bar = bar_char * bar_len

                            print(f"  Ch {i+1:2d}: {val:+8.2f} μV |{bar:40s}| {activity}")

                        print("-"*80)
                        print("\nTIPS FOR BETTER SIGNAL:")
                        print("  1. Relax your jaw and face muscles")
                        print("  2. Close your eyes to see Alpha waves (8-12 Hz)")
                        print("  3. Values >100μV usually mean electrode needs adjustment")

                    buffer = buffer[start + 33:]
                else:
                    buffer = buffer[start + 1:]
            except ValueError:
                buffer = bytearray()
                break