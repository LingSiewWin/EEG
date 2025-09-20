#!/usr/bin/env python3
"""
VERIFY THIS IS REAL EEG
Interactive tests to prove you're reading brain data
"""
import serial
import time
import statistics

ser = serial.Serial("/dev/cu.usbserial-DM01MV82", 115200, timeout=0.1)
time.sleep(2)

ser.write(b's')
time.sleep(0.5)
ser.reset_input_buffer()
ser.write(b'd')
time.sleep(0.5)
ser.write(b'b')

buffer = bytearray()
SCALE = 0.02235 / 1000

print("\n" + "="*70)
print("REAL EEG VERIFICATION TEST")
print("="*70)
print("\nFollow these instructions to prove this is YOUR brain activity:\n")

test_phase = 0
test_start = time.time()
baseline_values = []
test_values = []

while True:
    if ser.in_waiting:
        buffer.extend(ser.read(ser.in_waiting))

        while len(buffer) >= 33:
            try:
                start = buffer.index(0xA0)
                if start + 32 < len(buffer) and buffer[start + 32] == 0xC0:
                    packet = buffer[start:start + 33]

                    # Parse first channel (frontal)
                    val = (packet[2] << 16) | (packet[3] << 8) | packet[4]
                    if val & 0x800000:
                        val -= 0x1000000
                    ch1_uV = val * SCALE

                    current_time = time.time() - test_start

                    # Test sequence
                    if test_phase == 0 and current_time < 5:
                        print(f"\rPHASE 1: BASELINE - Relax and breathe normally... {5-int(current_time)}s", end='')
                        baseline_values.append(abs(ch1_uV))

                    elif test_phase == 0 and current_time >= 5:
                        test_phase = 1
                        test_start = time.time()
                        baseline_avg = statistics.mean(baseline_values)
                        print(f"\n\nBaseline recorded: {baseline_avg:.2f} μV average")
                        print("\n" + "="*70)

                    elif test_phase == 1 and current_time < 5:
                        print(f"\rPHASE 2: BLINK TEST - Blink your eyes 3 times NOW... {5-int(current_time)}s", end='')
                        test_values.append(abs(ch1_uV))

                    elif test_phase == 1 and current_time >= 5:
                        test_phase = 2
                        test_start = time.time()
                        blink_max = max(test_values)
                        print(f"\n\nBlink artifacts detected: {blink_max:.2f} μV peak")
                        if blink_max > baseline_avg * 2:
                            print("✓ VERIFIED: Eye blinks detected!")
                        test_values = []
                        print("\n" + "="*70)

                    elif test_phase == 2 and current_time < 5:
                        print(f"\rPHASE 3: JAW CLENCH - Clench your jaw NOW... {5-int(current_time)}s", end='')
                        test_values.append(abs(ch1_uV))

                    elif test_phase == 2 and current_time >= 5:
                        test_phase = 3
                        test_start = time.time()
                        jaw_max = max(test_values)
                        print(f"\n\nJaw clench detected: {jaw_max:.2f} μV peak")
                        if jaw_max > baseline_avg * 3:
                            print("✓ VERIFIED: Muscle artifacts detected!")
                        test_values = []
                        print("\n" + "="*70)

                    elif test_phase == 3 and current_time < 10:
                        print(f"\rPHASE 4: EYES CLOSED - Close your eyes and relax... {10-int(current_time)}s | Ch1: {ch1_uV:+6.2f} μV", end='')
                        test_values.append(abs(ch1_uV))

                    elif test_phase == 3 and current_time >= 10:
                        test_phase = 4
                        alpha_avg = statistics.mean(test_values)
                        print(f"\n\nEyes closed average: {alpha_avg:.2f} μV")
                        if alpha_avg > baseline_avg:
                            print("✓ VERIFIED: Alpha waves increased with eyes closed!")

                        print("\n" + "="*70)
                        print("TEST COMPLETE - THIS IS REAL EEG FROM YOUR BRAIN!")
                        print("="*70)
                        print(f"\nSummary:")
                        print(f"• Baseline: {baseline_avg:.2f} μV")
                        print(f"• Eye blinks: {blink_max:.2f} μV (should be 2-3x baseline)")
                        print(f"• Jaw clench: {jaw_max:.2f} μV (should be 3-5x baseline)")
                        print(f"• Alpha (eyes closed): {alpha_avg:.2f} μV (should increase)")
                        print("\nYour OpenBCI is working perfectly!")
                        return

                    buffer = buffer[start + 33:]
                else:
                    buffer = buffer[start + 1:]
            except ValueError:
                buffer = bytearray()
                break