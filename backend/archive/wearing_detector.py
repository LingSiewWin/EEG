#!/usr/bin/env python3
"""
OpenBCI Wearing Detection Script
Detects when device is worn based on signal characteristics
"""
import serial
import time
import numpy as np
from datetime import datetime

def main():
    port = "/dev/cu.usbserial-DM01MV82"
    baudrate = 230400

    print("=" * 70)
    print("🧠 OPENBCI WEARING DETECTOR")
    print("=" * 70)
    print("This script detects when the device is worn on your head")
    print("by analyzing signal characteristics")
    print("=" * 70)

    try:
        # Connect
        ser = serial.Serial(port, baudrate, timeout=0.1)
        print("✅ Connected to OpenBCI")

        # Statistics
        not_worn_bytes = []
        worn_bytes = []
        current_state = "UNKNOWN"
        state_start_time = time.time()

        # Monitoring
        byte_buffer = []
        buffer_size = 100
        analysis_interval = 2.0  # Analyze every 2 seconds
        last_analysis = time.time()

        print("\n📊 MONITORING - Put on/take off the device to see changes")
        print("=" * 70)

        while True:
            try:
                # Read data
                if ser.in_waiting > 0:
                    data = ser.read(ser.in_waiting)

                    for byte in data:
                        byte_buffer.append(byte)
                        if len(byte_buffer) > buffer_size:
                            byte_buffer.pop(0)

                # Periodic analysis
                current_time = time.time()
                if current_time - last_analysis >= analysis_interval and byte_buffer:
                    # Calculate metrics
                    byte_array = np.array(byte_buffer)
                    data_rate = len(byte_buffer) / analysis_interval

                    # Key metrics for detection
                    unique_values = len(np.unique(byte_array))
                    mean_value = np.mean(byte_array)
                    std_value = np.std(byte_array)
                    ff_count = np.sum(byte_array == 0xFF)
                    ff_ratio = ff_count / len(byte_array)

                    # Wearing detection logic
                    previous_state = current_state

                    if data_rate < 1.0:
                        current_state = "NOT_WORN"
                        reason = "Very low data rate (<1 byte/sec)"
                    elif ff_ratio > 0.95:
                        current_state = "NOT_WORN"
                        reason = "Only 0xFF acknowledgments"
                    elif unique_values < 5:
                        current_state = "NOT_WORN"
                        reason = "Low signal variability"
                    elif data_rate > 3 and unique_values > 20:
                        current_state = "WORN"
                        reason = "High data rate and variability"
                    elif std_value > 30:
                        current_state = "WORN"
                        reason = "High signal variation"
                    else:
                        current_state = "CHECKING"
                        reason = "Analyzing..."

                    # State change detection
                    if current_state != previous_state:
                        state_duration = current_time - state_start_time
                        print(f"\n🔄 STATE CHANGE: {previous_state} → {current_state}")
                        print(f"   Previous state duration: {state_duration:.1f} seconds")
                        print(f"   Reason: {reason}")
                        state_start_time = current_time

                        # Store statistics
                        if current_state == "WORN":
                            worn_bytes = byte_buffer.copy()
                            print("   📈 WORN CHARACTERISTICS:")
                            print(f"      Data rate: {data_rate:.1f} bytes/sec")
                            print(f"      Unique values: {unique_values}/256")
                            print(f"      Std deviation: {std_value:.1f}")
                            print(f"      0xFF ratio: {ff_ratio:.1%}")
                        elif current_state == "NOT_WORN":
                            not_worn_bytes = byte_buffer.copy()
                            print("   📉 NOT WORN CHARACTERISTICS:")
                            print(f"      Data rate: {data_rate:.1f} bytes/sec")
                            print(f"      Unique values: {unique_values}/256")
                            print(f"      Std deviation: {std_value:.1f}")
                            print(f"      0xFF ratio: {ff_ratio:.1%}")

                    # Regular update
                    print(f"\r⏱️  {datetime.now().strftime('%H:%M:%S')} | "
                          f"State: {current_state:10s} | "
                          f"Rate: {data_rate:5.1f} b/s | "
                          f"Variety: {unique_values:3d}/256", end="")

                    # Clear buffer for next analysis
                    byte_buffer = []
                    last_analysis = current_time

                time.sleep(0.01)

            except KeyboardInterrupt:
                break

        # Final analysis
        print("\n\n" + "=" * 70)
        print("📊 WEARING DETECTION SUMMARY")
        print("=" * 70)

        if worn_bytes and not_worn_bytes:
            worn_array = np.array(worn_bytes)
            not_worn_array = np.array(not_worn_bytes)

            print("\nCOMPARISON: Worn vs Not Worn")
            print("─" * 40)
            print(f"{'Metric':<20} {'WORN':>10} {'NOT WORN':>10}")
            print("─" * 40)

            # Data rate is calculated elsewhere, using variety as proxy
            print(f"{'Unique values':.<20} {len(np.unique(worn_array)):>10d} {len(np.unique(not_worn_array)):>10d}")
            print(f"{'Mean value':.<20} {np.mean(worn_array):>10.1f} {np.mean(not_worn_array):>10.1f}")
            print(f"{'Std deviation':.<20} {np.std(worn_array):>10.1f} {np.std(not_worn_array):>10.1f}")
            print(f"{'0xFF count':.<20} {np.sum(worn_array==0xFF):>10d} {np.sum(not_worn_array==0xFF):>10d}")

            print("\n✅ KEY FINDING:")
            if len(np.unique(worn_array)) > len(np.unique(not_worn_array)) * 2:
                print("Device shows SIGNIFICANTLY more signal variety when worn!")
                print("This confirms electrodes are detecting electrical activity.")
            elif np.std(worn_array) > np.std(not_worn_array) * 2:
                print("Signal variation increases dramatically when worn!")
                print("The device IS responding to being on your head.")
            else:
                print("Some difference detected between worn and not worn states.")

        ser.close()

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1

    return 0

if __name__ == "__main__":
    main()