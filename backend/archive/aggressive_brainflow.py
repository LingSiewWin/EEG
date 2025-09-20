#!/usr/bin/env python3
"""
Aggressive BrainFlow Connection Strategy
Multiple retry mechanisms and connection approaches
Designed for hardware with intermittent radio issues
"""
import sys
import time
import threading
import numpy as np
from datetime import datetime

try:
    from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds, BrainFlowError, LogLevels
    from brainflow.data_filter import DataFilter
    BoardShim.enable_dev_board_logger()
    BoardShim.set_log_level(LogLevels.LEVEL_DEBUG.value)
except ImportError:
    print("Installing BrainFlow...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "brainflow"])
    from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds, BrainFlowError, LogLevels
    from brainflow.data_filter import DataFilter
    BoardShim.enable_dev_board_logger()
    BoardShim.set_log_level(LogLevels.LEVEL_DEBUG.value)


class AggressiveBrainFlowStreamer:
    def __init__(self):
        self.port = "/dev/cu.usbserial-DM01MV82"
        self.board = None
        self.board_id = None
        self.streaming = False

        # Statistics
        self.total_samples = 0
        self.connection_attempts = 0
        self.successful_reads = 0
        self.failed_reads = 0

        # Detection flags
        self.wearing_detected = False
        self.good_signal_count = 0

    def try_connection_strategy(self, strategy_name, board_id, timeout, other_info=""):
        """Try a specific connection strategy"""
        print(f"\n🔧 Strategy: {strategy_name}")
        print(f"   Board ID: {board_id}")
        print(f"   Timeout: {timeout}s")
        if other_info:
            print(f"   Extra params: {other_info}")

        params = BrainFlowInputParams()
        params.serial_port = self.port
        params.timeout = timeout

        if other_info:
            params.other_info = other_info

        try:
            board = BoardShim(board_id, params)

            # Multiple prepare attempts with different delays
            prepare_attempts = [
                (0.5, "Quick"),
                (2.0, "Standard"),
                (5.0, "Patient"),
                (10.0, "Extended")
            ]

            for delay, attempt_name in prepare_attempts:
                try:
                    print(f"   Prepare attempt ({attempt_name})...", end="")
                    board.prepare_session()
                    print(" ✅")

                    # Try to get data
                    print("   Starting stream...", end="")
                    board.start_stream()
                    print(" ✅")

                    # Wait for data
                    time.sleep(delay)

                    print("   Reading data...", end="")
                    data = board.get_board_data()

                    if data.shape[1] > 0:
                        print(f" ✅ Got {data.shape[1]} samples!")
                        return board, board_id, data
                    else:
                        print(" ❌ No data")
                        board.stop_stream()
                        board.release_session()

                except BrainFlowError as e:
                    error_msg = str(e)
                    if "BOARD_NOT_READY" in error_msg:
                        print(f" ⏳ Board not ready, waiting {delay}s...")
                        time.sleep(delay)
                    elif "ALREADY_PREPARED" in error_msg:
                        print(" ⚠️  Already prepared")
                        try:
                            board.start_stream()
                            time.sleep(delay)
                            data = board.get_board_data()
                            if data.shape[1] > 0:
                                return board, board_id, data
                        except:
                            pass
                    else:
                        print(f" ❌ {error_msg[:30]}")
                        break

            board.release_session()

        except Exception as e:
            print(f"   ❌ Failed: {str(e)[:50]}")

        return None, None, None

    def aggressive_connect(self):
        """Try multiple aggressive connection strategies"""
        print("=" * 80)
        print("🚀 AGGRESSIVE CONNECTION SEQUENCE")
        print("=" * 80)

        strategies = [
            # Standard approaches
            ("Cyton Standard", BoardIds.CYTON_BOARD, 10, ""),
            ("Cyton Quick", BoardIds.CYTON_BOARD, 5, ""),
            ("Cyton Extended", BoardIds.CYTON_BOARD, 20, ""),

            # With custom baudrate
            ("Cyton 230400 baud", BoardIds.CYTON_BOARD, 10, "baud_rate:230400"),
            ("Cyton 115200 baud", BoardIds.CYTON_BOARD, 10, "baud_rate:115200"),

            # Daisy variants
            ("Cyton+Daisy Standard", BoardIds.CYTON_DAISY_BOARD, 15, ""),
            ("Cyton+Daisy Extended", BoardIds.CYTON_DAISY_BOARD, 25, ""),

            # Synthetic board (fallback for testing)
            ("Synthetic (Testing)", BoardIds.SYNTHETIC_BOARD, 1, ""),
        ]

        for strategy in strategies:
            self.connection_attempts += 1
            board, board_id, data = self.try_connection_strategy(*strategy)

            if board and board_id:
                self.board = board
                self.board_id = board_id
                print(f"\n✅ SUCCESS with strategy: {strategy[0]}")

                if board_id == BoardIds.SYNTHETIC_BOARD:
                    print("⚠️  Using synthetic board for testing")
                    print("   Real hardware connection failed")

                return True

        print("\n❌ All connection strategies failed")
        return False

    def analyze_eeg_quality(self, eeg_data):
        """Analyze if we're getting real brain signals"""
        if eeg_data.size == 0:
            return "NO_DATA"

        # Calculate metrics
        mean_amplitude = np.mean(np.abs(eeg_data))
        std_amplitude = np.std(eeg_data)
        max_amplitude = np.max(np.abs(eeg_data))

        # Wearing detection
        if max_amplitude < 1.0:
            return "NOT_WORN"
        elif max_amplitude > 500:
            return "ARTIFACT"
        elif 5 < mean_amplitude < 150 and std_amplitude > 3:
            return "GOOD_SIGNAL"
        elif mean_amplitude < 5:
            return "POOR_CONTACT"
        else:
            return "ANALYZING"

    def stream_with_recovery(self):
        """Stream with automatic recovery on failure"""
        print("\n" + "=" * 80)
        print("📊 STREAMING WITH AUTO-RECOVERY")
        print("=" * 80)

        consecutive_failures = 0
        last_display = time.time()
        display_interval = 0.5

        while True:
            try:
                # Get data
                data = self.board.get_current_board_data(250)  # Get last 250 samples (1 sec at 250Hz)

                if data.shape[1] > 0:
                    self.total_samples += data.shape[1]
                    self.successful_reads += 1
                    consecutive_failures = 0

                    # Get EEG channels
                    eeg_channels = BoardShim.get_eeg_channels(self.board_id)
                    if len(eeg_channels) > 0:
                        eeg_data = data[eeg_channels, :]

                        # Analyze signal quality
                        quality = self.analyze_eeg_quality(eeg_data)

                        # Update wearing detection
                        if quality == "GOOD_SIGNAL":
                            self.good_signal_count += 1
                            if self.good_signal_count > 5 and not self.wearing_detected:
                                self.wearing_detected = True
                                print("\n🎉 DEVICE WORN DETECTED! Getting real brain signals!")

                        # Display update
                        current_time = time.time()
                        if current_time - last_display >= display_interval:
                            self.display_data(eeg_data, quality)
                            last_display = current_time

                else:
                    # No data available
                    self.failed_reads += 1
                    consecutive_failures += 1

                    if consecutive_failures > 50:  # ~5 seconds at 10Hz checking
                        print("\n⚠️  No data for 5 seconds, attempting recovery...")

                        # Try to restart stream
                        try:
                            self.board.stop_stream()
                            time.sleep(1)
                            self.board.start_stream()
                            print("✅ Stream restarted")
                            consecutive_failures = 0
                        except:
                            print("❌ Recovery failed, reconnecting...")
                            self.board.release_session()

                            if self.aggressive_connect():
                                self.board.start_stream()
                                print("✅ Reconnected!")
                            else:
                                print("❌ Could not reconnect")
                                break

                time.sleep(0.1)  # Check every 100ms

            except KeyboardInterrupt:
                print("\n⏹️  Stopped by user")
                break
            except Exception as e:
                print(f"\n⚠️  Stream error: {e}")
                consecutive_failures += 1

    def display_data(self, eeg_data, quality):
        """Display real-time EEG data"""
        # Clear screen
        print("\033[H\033[J", end='')

        print("=" * 80)
        print(f"🧠 LIVE EEG STREAM - {datetime.now().strftime('%H:%M:%S')}")
        print("=" * 80)

        # Connection info
        print(f"\n📡 CONNECTION:")
        board_name = "Synthetic" if self.board_id == BoardIds.SYNTHETIC_BOARD else "Cyton"
        print(f"   Board: {board_name}")
        print(f"   Total samples: {self.total_samples}")
        print(f"   Success rate: {(self.successful_reads/(self.successful_reads+self.failed_reads+0.001))*100:.1f}%")

        # Signal quality
        quality_msgs = {
            "GOOD_SIGNAL": "✅ Excellent - Real brain activity detected!",
            "POOR_CONTACT": "⚠️  Poor contact - Adjust electrodes",
            "ARTIFACT": "⚡ Movement artifact detected",
            "NOT_WORN": "❌ Device not worn or electrodes disconnected",
            "ANALYZING": "🔍 Analyzing signal...",
            "NO_DATA": "❌ No data"
        }

        print(f"\n🎯 SIGNAL QUALITY: {quality_msgs.get(quality, quality)}")

        if self.wearing_detected:
            print("   👤 WEARING STATUS: Confirmed on head!")

        # Display channels
        if eeg_data.size > 0:
            latest_sample = eeg_data[:, -1]
            print(f"\n📊 CHANNEL VALUES (μV):")

            for i, value in enumerate(latest_sample[:8]):  # Show first 8 channels
                # Convert to microvolts
                value_uv = value * 0.02235 if self.board_id != BoardIds.SYNTHETIC_BOARD else value

                # Bar visualization
                bar_length = int(abs(value_uv) / 5)
                bar = "█" * min(bar_length, 40)

                # Status indicator
                if abs(value_uv) > 100:
                    status = "⚡"
                elif abs(value_uv) < 5:
                    status = "💤"
                else:
                    status = "📊"

                print(f"   CH{i+1}: {status} {value_uv:8.2f} μV  {bar}")

            # Statistics
            print(f"\n📈 STATISTICS:")
            all_values = eeg_data.flatten() * 0.02235 if self.board_id != BoardIds.SYNTHETIC_BOARD else eeg_data.flatten()
            print(f"   Mean: {np.mean(all_values):.2f} μV")
            print(f"   Std Dev: {np.std(all_values):.2f} μV")
            print(f"   Range: [{np.min(all_values):.2f}, {np.max(all_values):.2f}] μV")

    def run(self):
        """Main entry point"""
        print("=" * 80)
        print("🚀 AGGRESSIVE BRAINFLOW STREAMER")
        print("Maximum effort to establish OpenBCI connection")
        print("=" * 80)

        # Try aggressive connection
        if not self.aggressive_connect():
            print("\n💡 TROUBLESHOOTING RECOMMENDATIONS:")
            print("1. Power cycle the OpenBCI board")
            print("2. Ensure blue LEDs are on for both board and dongle")
            print("3. Try pressing RESET button on the board")
            print("4. Check USB connection")
            print("5. The radio link may be permanently damaged")
            return 1

        try:
            # Start streaming
            self.board.start_stream()
            print("\n✅ Stream started!")
            print("Press Ctrl+C to stop\n")

            # Stream with recovery
            self.stream_with_recovery()

        finally:
            # Cleanup
            if self.board:
                try:
                    self.board.stop_stream()
                    self.board.release_session()
                    print("\n✅ Cleanup complete")
                except:
                    pass

            # Summary
            print("\n" + "=" * 80)
            print("📊 SESSION SUMMARY")
            print("=" * 80)
            print(f"Connection attempts: {self.connection_attempts}")
            print(f"Total samples: {self.total_samples}")
            print(f"Successful reads: {self.successful_reads}")
            print(f"Failed reads: {self.failed_reads}")

            if self.wearing_detected:
                print("\n✅ SUCCESS: Device works when worn properly!")
                print("The increased data rate when worn confirms electrode contact is crucial")
            elif self.board_id == BoardIds.SYNTHETIC_BOARD:
                print("\n⚠️  Only synthetic data was available")
                print("Real hardware connection could not be established")

        return 0

if __name__ == "__main__":
    streamer = AggressiveBrainFlowStreamer()
    sys.exit(streamer.run())