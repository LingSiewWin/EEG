#!/usr/bin/env python3
"""
BrainFlow Direct Streaming - Bypass GUI with Robust Error Handling
Designed for OpenBCI Cyton with radio communication issues
Handles intermittent connections and partial data gracefully
"""
import sys
import time
import numpy as np
from datetime import datetime
import threading
import queue
import signal

try:
    from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds, BrainFlowError
    from brainflow.data_filter import DataFilter, FilterTypes
except ImportError:
    print("❌ BrainFlow not installed. Installing now...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "brainflow"])
    from brainflow.board_shim import BoardShim, BrainFlowInputParams, BoardIds, BrainFlowError
    from brainflow.data_filter import DataFilter, FilterTypes


class RobustBrainFlowStreamer:
    def __init__(self):
        # Configuration
        self.port = "/dev/cu.usbserial-DM01MV82"
        self.board = None
        self.board_id = None
        self.running = False

        # Data tracking
        self.sample_count = 0
        self.error_count = 0
        self.reconnect_attempts = 0
        self.last_valid_data = None
        self.data_queue = queue.Queue(maxsize=1000)

        # Display configuration
        self.display_interval = 0.5  # seconds between display updates
        self.last_display_time = 0

    def detect_board_type(self):
        """Try different board configurations to find what works"""
        print("🔍 Auto-detecting board configuration...")

        # Board configurations to try (in order of likelihood)
        board_configs = [
            (BoardIds.CYTON_BOARD, "Cyton (8 channels)", 115200),
            (BoardIds.CYTON_DAISY_BOARD, "Cyton+Daisy (16 channels)", 115200),
            (BoardIds.CYTON_BOARD, "Cyton (legacy baud)", 230400),
            (BoardIds.CYTON_DAISY_BOARD, "Cyton+Daisy (legacy baud)", 230400),
        ]

        for board_id, name, baudrate in board_configs:
            print(f"\n📡 Testing {name} at {baudrate} baud...")

            params = BrainFlowInputParams()
            params.serial_port = self.port
            params.timeout = 15  # Longer timeout for problematic boards

            # Try custom baudrate if not standard
            if baudrate != 115200:
                params.other_info = f"baud_rate:{baudrate}"

            try:
                board = BoardShim(board_id, params)

                # Try to prepare session with retries
                for attempt in range(3):
                    try:
                        print(f"   Attempt {attempt + 1}/3...")
                        board.prepare_session()

                        # Quick test to see if we can get data
                        board.start_stream()
                        time.sleep(0.5)
                        data = board.get_board_data()
                        board.stop_stream()

                        if data.shape[1] > 0:
                            print(f"   ✅ SUCCESS! Got {data.shape[1]} samples")
                            print(f"   📊 Using: {name}")
                            return board, board_id
                        else:
                            print(f"   ⚠️  No data received")

                    except BrainFlowError as e:
                        if "BOARD_NOT_READY" in str(e):
                            print(f"   ⚠️  Board not ready, retrying...")
                            time.sleep(2)
                        else:
                            print(f"   ❌ Error: {e}")
                            break

                board.release_session()

            except Exception as e:
                print(f"   ❌ Failed: {str(e)[:100]}")
                continue

        return None, None

    def connect_with_retries(self, max_retries=5):
        """Connect to board with automatic retries and recovery"""
        print("\n🔌 Establishing connection to OpenBCI...")

        for retry in range(max_retries):
            if retry > 0:
                wait_time = min(2 ** retry, 30)  # Exponential backoff, max 30s
                print(f"⏳ Waiting {wait_time}s before retry {retry + 1}/{max_retries}...")
                time.sleep(wait_time)

            # Detect board if not already known
            if not self.board_id:
                self.board, self.board_id = self.detect_board_type()

                if not self.board:
                    print("❌ Could not detect board type")
                    continue
            else:
                # Use known configuration
                params = BrainFlowInputParams()
                params.serial_port = self.port
                params.timeout = 15

                try:
                    self.board = BoardShim(self.board_id, params)
                    self.board.prepare_session()
                except Exception as e:
                    print(f"❌ Connection failed: {e}")
                    continue

            if self.board:
                try:
                    # Get board info
                    sampling_rate = BoardShim.get_sampling_rate(self.board_id)
                    eeg_channels = BoardShim.get_eeg_channels(self.board_id)

                    print(f"\n✅ Connected Successfully!")
                    print(f"📊 Board: {self.get_board_name()}")
                    print(f"⚡ Sampling Rate: {sampling_rate} Hz")
                    print(f"📍 EEG Channels: {len(eeg_channels)} channels")
                    print(f"🔌 Port: {self.port}")

                    return True

                except Exception as e:
                    print(f"⚠️  Board connected but info retrieval failed: {e}")
                    return True  # Still try to use it

        return False

    def get_board_name(self):
        """Get human-readable board name"""
        if self.board_id == BoardIds.CYTON_BOARD:
            return "OpenBCI Cyton (8-channel)"
        elif self.board_id == BoardIds.CYTON_DAISY_BOARD:
            return "OpenBCI Cyton+Daisy (16-channel)"
        else:
            return f"Board ID {self.board_id}"

    def process_data(self, data):
        """Process and display EEG data with error handling"""
        if data.shape[1] == 0:
            return None

        try:
            # Get EEG channels
            eeg_channels = BoardShim.get_eeg_channels(self.board_id)
            timestamp_channel = BoardShim.get_timestamp_channel(self.board_id)

            # Extract relevant data
            eeg_data = data[eeg_channels, :]
            timestamps = data[timestamp_channel, :] if timestamp_channel >= 0 else None

            # Convert to microvolts (Cyton has 24x gain)
            eeg_data_uv = eeg_data * 0.02235

            # Store for display
            processed = {
                'timestamp': timestamps[-1] if timestamps is not None else time.time(),
                'eeg_data': eeg_data_uv[:, -1],  # Latest sample
                'num_samples': data.shape[1],
                'channels': len(eeg_channels)
            }

            self.last_valid_data = processed
            return processed

        except Exception as e:
            print(f"⚠️  Data processing error: {e}")
            self.error_count += 1
            return None

    def display_data(self, data):
        """Display data in terminal with clear formatting"""
        if not data:
            return

        current_time = time.time()
        if current_time - self.last_display_time < self.display_interval:
            return

        self.last_display_time = current_time

        # Clear previous lines (simple approach)
        print("\n" + "=" * 80)
        print(f"📊 LIVE EEG DATA - {datetime.now().strftime('%H:%M:%S.%f')[:-3]}")
        print("=" * 80)

        # Display channel data
        print(f"Channels ({data['channels']} active):")
        for i, value in enumerate(data['eeg_data']):
            bar_length = int(abs(value) / 10)  # Scale for display
            bar = "█" * min(bar_length, 50)
            sign = "+" if value >= 0 else "-"
            print(f"  CH{i+1:02d}: {sign}{abs(value):7.2f} μV  {bar}")

        # Statistics
        print(f"\nStats:")
        print(f"  📈 Samples: {self.sample_count}")
        print(f"  ⚠️  Errors: {self.error_count}")
        print(f"  🔄 Reconnects: {self.reconnect_attempts}")

        if data['eeg_data'].size > 0:
            print(f"  📊 Range: {np.min(data['eeg_data']):.2f} to {np.max(data['eeg_data']):.2f} μV")
            print(f"  📍 Mean: {np.mean(data['eeg_data']):.2f} μV")

    def streaming_loop(self):
        """Main streaming loop with error recovery"""
        print("\n🚀 Starting data stream...")

        try:
            self.board.start_stream()
            print("✅ Stream started successfully")

            consecutive_errors = 0

            while self.running:
                try:
                    # Get available data (non-blocking)
                    data = self.board.get_board_data()

                    if data.shape[1] > 0:
                        self.sample_count += data.shape[1]
                        processed = self.process_data(data)

                        if processed:
                            self.data_queue.put(processed)
                            self.display_data(processed)
                            consecutive_errors = 0
                    else:
                        # No data available, but that's okay
                        time.sleep(0.01)

                except BrainFlowError as e:
                    consecutive_errors += 1

                    if "BOARD_NOT_READY" in str(e) or consecutive_errors > 10:
                        print(f"\n⚠️  Board communication lost. Attempting recovery...")

                        # Try to recover
                        try:
                            self.board.stop_stream()
                            time.sleep(1)
                            self.board.start_stream()
                            print("✅ Stream recovered")
                            consecutive_errors = 0
                            self.reconnect_attempts += 1
                        except:
                            print("❌ Recovery failed. Reconnecting...")
                            self.reconnect()

                except Exception as e:
                    print(f"⚠️  Streaming error: {e}")
                    self.error_count += 1
                    time.sleep(0.1)

        except Exception as e:
            print(f"❌ Fatal streaming error: {e}")

    def reconnect(self):
        """Reconnect to board after connection loss"""
        print("\n🔄 Reconnecting to board...")

        try:
            # Clean up existing connection
            if self.board:
                try:
                    self.board.stop_stream()
                    self.board.release_session()
                except:
                    pass

            # Wait before reconnecting
            time.sleep(2)

            # Reconnect
            if self.connect_with_retries(max_retries=3):
                self.board.start_stream()
                print("✅ Reconnected successfully")
                self.reconnect_attempts += 1
            else:
                print("❌ Reconnection failed")
                self.running = False

        except Exception as e:
            print(f"❌ Reconnection error: {e}")
            self.running = False

    def signal_handler(self, signum, frame):
        """Handle Ctrl+C gracefully"""
        print("\n\n⏹️  Stopping stream...")
        self.running = False

    def run(self):
        """Main entry point"""
        print("=" * 80)
        print("🧠 BrainFlow Direct Streamer - Robust Mode")
        print("Designed to handle intermittent connections and radio issues")
        print("=" * 80)

        # Set up signal handler for clean exit
        signal.signal(signal.SIGINT, self.signal_handler)

        # Connect to board
        if not self.connect_with_retries():
            print("\n❌ Could not establish connection after multiple attempts")
            print("\n💡 Troubleshooting suggestions:")
            print("1. Power cycle the OpenBCI board (turn off and on)")
            print("2. Ensure dongle is firmly connected to USB")
            print("3. Check blue LED is on for both board and dongle")
            print("4. Try: sudo chmod 666 /dev/cu.usbserial-DM01MV82")
            return

        # Start streaming
        self.running = True

        try:
            self.streaming_loop()
        except KeyboardInterrupt:
            print("\n⏹️  Stream interrupted by user")
        except Exception as e:
            print(f"\n❌ Unexpected error: {e}")
        finally:
            # Cleanup
            print("\n🧹 Cleaning up...")

            if self.board:
                try:
                    self.board.stop_stream()
                    print("✅ Stream stopped")
                except:
                    pass

                try:
                    self.board.release_session()
                    print("✅ Session released")
                except:
                    pass

            # Final statistics
            print("\n" + "=" * 80)
            print("📊 FINAL STATISTICS")
            print("=" * 80)
            print(f"Total samples collected: {self.sample_count}")
            print(f"Total errors encountered: {self.error_count}")
            print(f"Reconnection attempts: {self.reconnect_attempts}")

            if self.sample_count > 0:
                print(f"Success rate: {(1 - self.error_count/max(self.sample_count, 1)) * 100:.1f}%")

            print("\n👋 Goodbye!")


if __name__ == "__main__":
    streamer = RobustBrainFlowStreamer()
    streamer.run()