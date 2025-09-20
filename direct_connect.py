#!/usr/bin/env python3
import serial
import time
import struct

port = "/dev/cu.usbserial-DM01MV82"

# Try both baud rates
for baud in [115200, 230400]:
    try:
        print(f"Testing {baud}...")
        ser = serial.Serial(port, baud, timeout=1)
        ser.reset_input_buffer()

        # Send OpenBCI commands to start streaming
        commands = [
            b'v',  # version
            b'd',  # default settings
            b'b',  # begin streaming
        ]

        for cmd in commands:
            ser.write(cmd)
            time.sleep(0.2)
            response = ser.read(100)
            if response:
                print(f"Got response: {len(response)} bytes")

        # Now stream data
        print("STREAMING...")
        packet = []
        while True:
            if ser.in_waiting:
                data = ser.read(ser.in_waiting)

                for byte in data:
                    packet.append(byte)

                    # OpenBCI packet is 33 bytes
                    if len(packet) == 33:
                        if packet[0] == 0xA0 and packet[32] == 0xC0:
                            # Valid packet! Parse channels
                            channels = []
                            for i in range(8):
                                idx = 1 + (i * 3)
                                val = (packet[idx] << 16) | (packet[idx+1] << 8) | packet[idx+2]
                                if val & 0x800000:
                                    val = val - 0x1000000
                                channels.append(val * 0.02235)  # Convert to microvolts

                            print(f"\rCh1-8: {[f'{c:.1f}' for c in channels]}", end='')
                        packet = []

                    elif len(packet) > 33:
                        # Look for start byte
                        if 0xA0 in packet:
                            packet = packet[packet.index(0xA0):]
                        else:
                            packet = []

    except Exception as e:
        print(f"Failed at {baud}: {e}")
        continue

print("Trying raw connection...")
ser = serial.Serial(port, 115200, timeout=0.1)
ser.write(b'b')  # Start streaming
while True:
    data = ser.read(33)
    if data:
        print(f"Raw: {' '.join(f'{b:02x}' for b in data[:10])}...")