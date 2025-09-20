#!/usr/bin/env python3
"""
EEG Signal Processing for Love Detection
Based on neuroscience research for emotional response
"""
import numpy as np
from scipy import signal
from scipy.fft import fft, fftfreq
import json

class EEGProcessor:
    def __init__(self, sampling_rate=250):
        self.sampling_rate = sampling_rate

        # Frequency bands (Hz)
        self.bands = {
            'delta': (0.5, 4),
            'theta': (4, 8),
            'alpha': (8, 12),
            'beta': (12, 30),
            'gamma': (30, 45)
        }

        # Channel mapping for 8-channel Cyton
        # Assuming standard 10-20 placement
        self.channel_names = ['Fp1', 'Fp2', 'C3', 'C4', 'P7', 'P8', 'O1', 'O2']

    def bandpass_filter(self, data, low_freq=1, high_freq=45):
        """Apply bandpass filter to remove noise"""
        nyquist = self.sampling_rate / 2
        low = low_freq / nyquist
        high = high_freq / nyquist

        # Design filter
        b, a = signal.butter(4, [low, high], btype='band')

        # Apply filter
        filtered = signal.filtfilt(b, a, data)
        return filtered

    def calculate_band_power(self, data):
        """Calculate power for each frequency band"""
        # Apply FFT
        n = len(data)
        fft_vals = fft(data)
        fft_freq = fftfreq(n, 1/self.sampling_rate)

        # Get positive frequencies only
        pos_mask = fft_freq > 0
        freqs = fft_freq[pos_mask]
        power = np.abs(fft_vals[pos_mask]) ** 2

        # Calculate power for each band
        band_powers = {}
        for band_name, (low, high) in self.bands.items():
            band_mask = (freqs >= low) & (freqs <= high)
            band_powers[band_name] = np.mean(power[band_mask]) if np.any(band_mask) else 0

        return band_powers

    def calculate_frontal_alpha_asymmetry(self, left_frontal, right_frontal):
        """
        Calculate frontal alpha asymmetry (FAA)
        Positive FAA = approach motivation (attraction)
        Negative FAA = withdrawal motivation
        """
        # Filter for alpha band (8-12 Hz)
        left_alpha = self.bandpass_filter(left_frontal, 8, 12)
        right_alpha = self.bandpass_filter(right_frontal, 8, 12)

        # Calculate power
        left_power = np.mean(left_alpha ** 2)
        right_power = np.mean(right_alpha ** 2)

        # Log transform and calculate asymmetry
        if left_power > 0 and right_power > 0:
            faa = np.log(right_power) - np.log(left_power)
        else:
            faa = 0

        return faa

    def detect_p300(self, data, stimulus_time=0):
        """
        Detect P300 event-related potential
        Positive peak around 300ms after stimulus
        """
        # Window around 250-400ms
        start_sample = int(0.25 * self.sampling_rate)
        end_sample = int(0.4 * self.sampling_rate)

        if len(data) > end_sample:
            window = data[start_sample:end_sample]
            p300_amplitude = np.max(window) - np.mean(data[:start_sample])
            return p300_amplitude
        return 0

    def calculate_love_score(self, channels_data):
        """
        Calculate "Love at First Sight" score based on:
        1. Frontal Alpha Asymmetry (FAA) - approach motivation
        2. Beta/Gamma power - arousal/excitement
        3. P300 amplitude - attention/significance
        """

        # Process each channel
        processed_channels = []
        for ch_data in channels_data:
            # Filter data
            filtered = self.bandpass_filter(ch_data)
            processed_channels.append(filtered)

        # 1. Frontal Alpha Asymmetry (Fp1 vs Fp2)
        faa = self.calculate_frontal_alpha_asymmetry(
            processed_channels[0],  # Fp1 (left frontal)
            processed_channels[1]   # Fp2 (right frontal)
        )

        # 2. Beta/Gamma arousal (average across all channels)
        total_arousal = 0
        for ch_data in processed_channels:
            band_powers = self.calculate_band_power(ch_data)
            arousal = band_powers['beta'] + band_powers['gamma']
            total_arousal += arousal
        avg_arousal = total_arousal / len(processed_channels)

        # 3. P300 from central channels (C3, C4)
        p300_c3 = self.detect_p300(processed_channels[2])
        p300_c4 = self.detect_p300(processed_channels[3])
        p300_amplitude = (p300_c3 + p300_c4) / 2

        # Normalize and weight components
        # Positive FAA indicates approach (attraction)
        faa_score = max(0, min(100, 50 + faa * 100))  # Scale to 0-100

        # Higher arousal = more excitement
        arousal_score = min(100, avg_arousal / 1000)  # Normalize

        # Higher P300 = more attention/significance
        p300_score = min(100, p300_amplitude * 10)  # Scale appropriately

        # Weighted combination
        weights = {
            'faa': 0.4,      # 40% - emotional approach
            'arousal': 0.3,  # 30% - excitement
            'p300': 0.3      # 30% - attention
        }

        love_score = (
            weights['faa'] * faa_score +
            weights['arousal'] * arousal_score +
            weights['p300'] * p300_score
        )

        # Categorize the response
        if love_score >= 80:
            category = "Love at First Sight! 💘"
        elif love_score >= 60:
            category = "Strong Attraction 💕"
        elif love_score >= 40:
            category = "Interested 💗"
        elif love_score >= 20:
            category = "Neutral 😐"
        else:
            category = "Not Interested 💔"

        return {
            'love_score': round(love_score, 2),
            'category': category,
            'components': {
                'frontal_asymmetry': round(faa_score, 2),
                'arousal': round(arousal_score, 2),
                'attention_p300': round(p300_score, 2)
            },
            'raw_values': {
                'faa': round(faa, 4),
                'avg_arousal': round(avg_arousal, 2),
                'p300_amplitude': round(p300_amplitude, 2)
            }
        }

    def get_frequency_summary(self, channels_data):
        """Get frequency band power for each channel"""
        summary = []

        for i, ch_data in enumerate(channels_data):
            # Filter and calculate band powers
            filtered = self.bandpass_filter(ch_data)
            band_powers = self.calculate_band_power(filtered)

            summary.append({
                'channel': self.channel_names[i] if i < len(self.channel_names) else f'Ch{i+1}',
                'bands': {
                    band: round(power, 2)
                    for band, power in band_powers.items()
                }
            })

        return summary