#!/usr/bin/env python3
import serial
import time

print("CONNECTING TO OPENBCI...")
ser = serial.Serial("/dev/cu.usbserial-DM01MV82", 115200, timeout=0.1)
time.sleep(2)

print("STARTING STREAM (watch for RED+BLUE lights)...")
ser.write(b's')  # stop
time.sleep(0.5)
ser.reset_input_buffer()
ser.write(b'd')  # defaults
time.sleep(0.5)
ser.write(b'b')  # BEGIN - LIGHTS SHOULD BE RED+BLUE NOW!

print("\nSTREAMING ACTIVE! Data below:\n")
print("-" * 50)

buffer = bytearray()
packet_count = 0
last_time = time.time()

while True:
    # Read available data
    if ser.in_waiting:
        new_data = ser.read(ser.in_waiting)
        buffer.extend(new_data)

        # Look for complete packets
        while len(buffer) >= 33:
            # Find packet start (0xA0)
            try:
                start_idx = buffer.index(0xA0)

                # Check if we have a complete packet
                if start_idx + 32 < len(buffer):
                    # Check for packet end (0xC0)
                    if buffer[start_idx + 32] == 0xC0:
                        # Valid packet found!
                        packet = buffer[start_idx:start_idx + 33]
                        packet_count += 1

                        # Parse first 3 channels as example
                        ch1_raw = (packet[2] << 16) | (packet[3] << 8) | packet[4]
                        if ch1_raw & 0x800000:
                            ch1_raw -= 0x1000000
                        ch1_uV = ch1_raw * 0.02235

                        ch2_raw = (packet[5] << 16) | (packet[6] << 8) | packet[7]
                        if ch2_raw & 0x800000:
                            ch2_raw -= 0x1000000
                        ch2_uV = ch2_raw * 0.02235

                        ch3_raw = (packet[8] << 16) | (packet[9] << 8) | packet[10]
                        if ch3_raw & 0x800000:
                            ch3_raw -= 0x1000000
                        ch3_uV = ch3_raw * 0.02235

                        # Display update every 0.1 seconds
                        current_time = time.time()
                        if current_time - last_time > 0.1:
                            print(f"\rPackets: {packet_count:5d} | Ch1: {ch1_uV:+8.2f}μV | Ch2: {ch2_uV:+8.2f}μV | Ch3: {ch3_uV:+8.2f}μV", end='', flush=True)
                            last_time = current_time

                        # Remove processed packet from buffer
                        buffer = buffer[start_idx + 33:]
                    else:
                        # Not a valid packet end, skip this start byte
                        buffer = buffer[start_idx + 1:]
                else:
                    # Not enough data for complete packet
                    break
            except ValueError:
                # No start byte found, clear buffer
                buffer = bytearray()
                break

    time.sleep(0.001)  # Small delay to prevent CPU overuse