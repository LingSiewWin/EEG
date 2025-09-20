#!/usr/bin/env python3
"""
THIS WORKS - YOUR BOARD IS STREAMING!
Run this to see real-time EEG in terminal
"""
import serial
import time

ser = serial.Serial("/dev/cu.usbserial-DM01MV82", 115200, timeout=0.1)
time.sleep(1)

print("Starting stream (watch for red+blue lights)...")
ser.write(b's')  # stop
time.sleep(0.5)
ser.write(b'd')  # defaults
time.sleep(0.5)
ser.write(b'b')  # begin - LIGHTS SHOULD TURN RED+BLUE NOW

print("\nSTREAMING! You'll see channel values below:\n")

packet = []
count = 0

while True:
    if ser.in_waiting:
        data = ser.read(ser.in_waiting)

        for byte in data:
            packet.append(byte)

            if len(packet) == 33:
                if packet[0] == 0xA0 and packet[32] == 0xC0:
                    count += 1

                    # Parse first 3 channels as example
                    ch1 = ((packet[2] << 16) | (packet[3] << 8) | packet[4])
                    if ch1 & 0x800000: ch1 -= 0x1000000
                    ch1 *= 0.02235

                    ch2 = ((packet[5] << 16) | (packet[6] << 8) | packet[7])
                    if ch2 & 0x800000: ch2 -= 0x1000000
                    ch2 *= 0.02235

                    ch3 = ((packet[8] << 16) | (packet[9] << 8) | packet[10])
                    if ch3 & 0x800000: ch3 -= 0x1000000
                    ch3 *= 0.02235

                    # Show in terminal
                    print(f"\rPacket #{count} | Ch1: {ch1:7.2f} μV | Ch2: {ch2:7.2f} μV | Ch3: {ch3:7.2f} μV", end='')

                packet = []
            elif len(packet) > 33:
                packet = packet[1:]  # shift buffer