#!/usr/bin/env python3
import serial
import time
import sys

ser = serial.Serial("/dev/cu.usbserial-DM01MV82", 115200, timeout=0.5)
time.sleep(2)  # Let board initialize

# Force reset and stream
print("Forcing stream start...")
ser.write(b's')  # stop
time.sleep(0.5)
ser.reset_input_buffer()
ser.write(b'v')  # version check
time.sleep(0.5)

response = ser.read(1000)
print(f"Version response: {response[:50]}")

ser.write(b'd')  # default
time.sleep(0.5)
ser.write(b'b')  # begin

print("Reading stream...")
start = time.time()
total = 0

while time.time() - start < 5:
    if ser.in_waiting:
        data = ser.read(ser.in_waiting)
        total += len(data)

        # Show raw hex
        hex_str = ' '.join(f'{b:02x}' for b in data[:20])
        print(f"\r{total} bytes | {hex_str}...", end='')

        # Check for OpenBCI markers
        if 0xA0 in data:
            print(f"\nFOUND START BYTE at position {data.index(0xA0)}")
        if 0xC0 in data:
            print(f"\nFOUND END BYTE at position {data.index(0xC0)}")

print(f"\n\nTotal: {total} bytes in 5 seconds = {total/5} bytes/sec")
ser.close()