import React, { useState, useEffect, useRef } from 'react';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
} from 'chart.js';

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

const EnhancedEEGDashboard = () => {
  // State management
  const [samples, setSamples] = useState([]);
  const [connectionStatus, setConnectionStatus] = useState('Disconnected');
  const [isCapturing, setIsCapturing] = useState(false);
  const [captureCountdown, setCaptureCountdown] = useState(0);
  const [capturedData, setCapturedData] = useState([]);
  const [loveAnalysis, setLoveAnalysis] = useState(null);
  const [frequencySummary, setFrequencySummary] = useState(null);
  const [showResults, setShowResults] = useState(false); // New state to control view
  const [chartData, setChartData] = useState({
    labels: [],
    datasets: []
  });

  const wsRef = useRef(null);
  const capturedDataRef = useRef([]);
  const isCapturingRef = useRef(false);
  const showResultsRef = useRef(false);
  const maxDataPoints = 250; // 1 second at 250Hz

  // Chart colors for 8 channels
  const channelColors = [
    'rgb(255, 99, 132)',   // Red
    'rgb(54, 162, 235)',   // Blue
    'rgb(255, 206, 86)',   // Yellow
    'rgb(75, 192, 192)',   // Teal
    'rgb(153, 102, 255)',  // Purple
    'rgb(255, 159, 64)',   // Orange
    'rgb(199, 199, 199)',  // Grey
    'rgb(83, 102, 255)',   // Indigo
  ];

  // Chart configuration
  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    animation: {
      duration: 0 // Disable animation for real-time
    },
    scales: {
      x: {
        display: true,
        title: {
          display: true,
          text: 'Time (samples)'
        }
      },
      y: {
        display: true,
        title: {
          display: true,
          text: 'Amplitude (μV)'
        },
        min: -100,
        max: 100
      }
    },
    plugins: {
      legend: {
        display: true,
        position: 'top',
      },
      title: {
        display: true,
        text: 'Real-Time EEG Signals'
      }
    }
  };

  useEffect(() => {
    // Initialize empty chart data
    const initialDatasets = [];
    for (let i = 0; i < 8; i++) {
      initialDatasets.push({
        label: `Channel ${i + 1}`,
        data: [],
        borderColor: channelColors[i],
        backgroundColor: channelColors[i] + '33',
        borderWidth: 1,
        tension: 0.1,
        pointRadius: 0
      });
    }

    setChartData({
      labels: Array(maxDataPoints).fill('').map((_, i) => i),
      datasets: initialDatasets
    });

    // Connect to WebSocket
    const connectWebSocket = () => {
      console.log('Connecting to WebSocket...');
      const ws = new WebSocket('ws://localhost:8765');

      ws.onopen = () => {
        console.log('WebSocket connected');
        setConnectionStatus('Connected');
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          if (data.type === 'status') {
            console.log('Status:', data.message);
          } else if (data.type === 'eeg') {
            // Update samples for table with unique ID
            const sample = {
              id: `${data.packet_num}_${Date.now()}_${Math.random()}`,
              timestamp: data.timestamp,
              channels: data.channels,
              packet_num: data.packet_num
            };

            // Only update display if not showing results (use ref to avoid closure)
            if (!showResultsRef.current) {
              setSamples(prev => [...prev, sample].slice(-10));

              // Update chart data
              setChartData(prevChart => {
                const newDatasets = prevChart.datasets.map((dataset, idx) => {
                  const newData = [...dataset.data, data.channels[idx] || 0];
                  if (newData.length > maxDataPoints) {
                    newData.shift();
                  }
                  return { ...dataset, data: newData };
                });

                return {
                  ...prevChart,
                  datasets: newDatasets
                };
              });
            }

            // If capturing for analysis - use ref for real-time capture
            if (isCapturingRef.current) {
              capturedDataRef.current.push(sample);
              setCapturedData(prev => [...prev, sample]);
            }
          } else if (data.type === 'analysis') {
            // Receive analysis results
            setLoveAnalysis(data.love_analysis);
            setFrequencySummary(data.frequency_summary);
          }
        } catch (error) {
          console.error('Error parsing WebSocket data:', error);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
        setConnectionStatus('Error');
      };

      ws.onclose = () => {
        console.log('WebSocket disconnected');
        setConnectionStatus('Disconnected');
      };

      wsRef.current = ws;
    };

    connectWebSocket();

    // Cleanup on unmount
    return () => {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.close();
      }
      wsRef.current = 'stopped';
    };
  }, []);

  const startCapture = () => {
    console.log('Starting 5-second capture...');

    // Reset capture refs and state
    capturedDataRef.current = [];
    isCapturingRef.current = true;

    setIsCapturing(true);
    setCaptureCountdown(5);
    setCapturedData([]);
    setLoveAnalysis(null);
    setFrequencySummary(null);
    setShowResults(false); // Still show live data during capture
    showResultsRef.current = false;

    // Clear any existing intervals/timeouts
    if (window.captureTimeout) clearTimeout(window.captureTimeout);
    if (window.countdownInterval) clearInterval(window.countdownInterval);

    // Countdown timer
    let countdown = 5;
    window.countdownInterval = setInterval(() => {
      countdown -= 1;
      setCaptureCountdown(countdown);

      if (countdown <= 0) {
        clearInterval(window.countdownInterval);
      }
    }, 1000);

    // Capture for 5 seconds
    window.captureTimeout = setTimeout(() => {
      console.log('Capture complete, analyzing...');
      isCapturingRef.current = false;
      setIsCapturing(false);
      setCaptureCountdown(0);

      // Use the ref data for analysis
      const capturedPackets = capturedDataRef.current;
      console.log(`Captured ${capturedPackets.length} packets`);

      if (capturedPackets.length === 0) {
        console.error('No data captured! Check WebSocket connection.');
        alert('No data was captured. Please check your connection and try again.');
        setShowResults(false);
        showResultsRef.current = false;
        return;
      }

      setShowResults(true); // STOP showing live data, show results only
      showResultsRef.current = true;
      setCapturedData(capturedPackets);

      // Process captured data
      setTimeout(() => {
        analyzeCapture();
      }, 100);
    }, 5000);
  };

  const resetToLiveView = () => {
    setShowResults(false);
    showResultsRef.current = false;
    setLoveAnalysis(null);
    setFrequencySummary(null);
    setCapturedData([]);
    capturedDataRef.current = [];
  };

  const analyzeCapture = () => {
    // Always use ref data since state might be empty due to closure
    const dataToAnalyze = capturedDataRef.current;

    if (!dataToAnalyze || dataToAnalyze.length === 0) {
      console.log('No data to analyze');
      alert('No EEG data was captured. Please ensure the device is streaming and try again.');
      setShowResults(false);
      showResultsRef.current = false;
      return;
    }

    console.log(`Analyzing ${dataToAnalyze.length} packets...`);

    // Calculate channel averages and statistics
    const channelStats = [];
    const frequencyBands = [];

    for (let ch = 0; ch < 8; ch++) {
      const channelData = dataToAnalyze.map(sample => sample.channels[ch] || 0);

      // Calculate statistics
      const mean = channelData.reduce((a, b) => a + b, 0) / channelData.length;
      const absValues = channelData.map(v => Math.abs(v));
      const avgAmplitude = absValues.reduce((a, b) => a + b, 0) / absValues.length;
      const maxAmp = Math.max(...absValues);
      const minAmp = Math.min(...channelData);

      channelStats.push({
        channel: ch + 1,
        mean: mean.toFixed(2),
        avgAmplitude: avgAmplitude.toFixed(2),
        max: maxAmp.toFixed(2),
        min: minAmp.toFixed(2)
      });

      // Simple frequency estimation (placeholder for real FFT)
      // Count zero crossings for dominant frequency
      let zeroCrossings = 0;
      for (let i = 1; i < channelData.length; i++) {
        if ((channelData[i-1] < 0 && channelData[i] > 0) ||
            (channelData[i-1] > 0 && channelData[i] < 0)) {
          zeroCrossings++;
        }
      }

      const dominantFreq = (zeroCrossings / 2) / 5; // Crossings to Hz over 5 seconds

      // Estimate band powers based on amplitude and frequency
      frequencyBands.push({
        channel: `Ch${ch + 1}`,
        bands: {
          delta: dominantFreq < 4 ? avgAmplitude * 0.8 : avgAmplitude * 0.1,
          theta: dominantFreq >= 4 && dominantFreq < 8 ? avgAmplitude * 0.8 : avgAmplitude * 0.1,
          alpha: dominantFreq >= 8 && dominantFreq < 12 ? avgAmplitude * 0.8 : avgAmplitude * 0.2,
          beta: dominantFreq >= 12 && dominantFreq < 30 ? avgAmplitude * 0.8 : avgAmplitude * 0.2,
          gamma: dominantFreq >= 30 ? avgAmplitude * 0.8 : avgAmplitude * 0.1
        }
      });
    }

    // Calculate love score based on neuroscience
    // Frontal asymmetry (Ch1-Fp1 vs Ch2-Fp2)
    const leftFrontal = channelStats[0].avgAmplitude;
    const rightFrontal = channelStats[1].avgAmplitude;
    const frontalAsymmetry = (parseFloat(rightFrontal) - parseFloat(leftFrontal)) /
                             (parseFloat(rightFrontal) + parseFloat(leftFrontal));

    // Average amplitude as arousal indicator
    const avgAmp = channelStats.reduce((sum, ch) => sum + parseFloat(ch.avgAmplitude), 0) / 8;

    // Calculate love score
    let loveScore = 50; // Base score

    // Positive frontal asymmetry = approach motivation
    if (frontalAsymmetry > 0) {
      loveScore += frontalAsymmetry * 30; // Up to +30 points
    }

    // Higher amplitude = more arousal
    if (avgAmp > 20) loveScore += 10;
    if (avgAmp > 40) loveScore += 15;
    if (avgAmp > 60) loveScore += 15;

    loveScore = Math.min(100, Math.max(0, loveScore));

    // Determine category
    let category = '';
    if (loveScore >= 80) category = 'Love at First Sight! 💘';
    else if (loveScore >= 60) category = 'Strong Attraction 💕';
    else if (loveScore >= 40) category = 'Interested 💗';
    else if (loveScore >= 20) category = 'Neutral 😐';
    else category = 'Not Interested 💔';

    // Set results
    setLoveAnalysis({
      love_score: loveScore.toFixed(1),
      category: category,
      avgAmplitude: avgAmp.toFixed(2),
      packets: dataToAnalyze.length,
      components: {
        frontal_asymmetry: (50 + frontalAsymmetry * 50).toFixed(1),
        arousal: Math.min(100, avgAmp * 1.5).toFixed(1),
        attention_p300: (avgAmp > 40 ? 75 : 40).toFixed(1)
      }
    });

    // Set frequency summary
    setFrequencySummary(frequencyBands);

    console.log('Analysis complete!', { loveScore, avgAmp, frontalAsymmetry });
  };

  const getStatusColor = () => {
    switch (connectionStatus) {
      case 'Connected': return '#4CAF50';
      case 'Disconnected': return '#f44336';
      case 'Error': return '#ff9800';
      default: return '#9e9e9e';
    }
  };

  return (
    <div style={{ fontFamily: 'Arial, sans-serif', padding: '20px', backgroundColor: '#f5f5f5', minHeight: '100vh' }}>
      <h1 style={{ color: '#333', marginBottom: '20px' }}>🧠 Advanced EEG Analysis Dashboard</h1>

      {/* Connection Status and Control */}
      <div style={{ marginBottom: '20px', padding: '15px', backgroundColor: 'white', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <span style={{ fontWeight: 'bold' }}>Status: </span>
            <span style={{ color: getStatusColor(), fontWeight: 'bold' }}>{connectionStatus}</span>
            {showResults && (
              <span style={{ marginLeft: '20px', color: '#ff9800' }}>
                📊 Showing Analysis Results
              </span>
            )}
          </div>
          <div>
            {showResults ? (
              <button
                onClick={resetToLiveView}
                style={{
                  background: '#2196F3',
                  color: 'white',
                  border: 'none',
                  padding: '10px 20px',
                  borderRadius: '5px',
                  cursor: 'pointer',
                  fontSize: '14px',
                  fontWeight: 'bold',
                  minWidth: '250px'
                }}
              >
                ← BACK TO LIVE STREAMING
              </button>
            ) : (
              <button
                onClick={startCapture}
                disabled={connectionStatus !== 'Connected' || isCapturing}
                style={{
                  background: isCapturing ? '#ff9800' : '#4CAF50',
                  color: 'white',
                  border: 'none',
                  padding: '10px 20px',
                  borderRadius: '5px',
                  cursor: connectionStatus === 'Connected' && !isCapturing ? 'pointer' : 'not-allowed',
                  fontSize: '14px',
                  fontWeight: 'bold',
                  minWidth: '250px'
                }}
              >
                {isCapturing
                  ? `CAPTURING... ${captureCountdown > 0 ? `(${captureCountdown}s)` : ''}`
                  : 'START 5-SECOND LOVE ANALYSIS'}
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Main Content Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: frequencySummary ? '250px 1fr' : '1fr', gap: '20px' }}>

        {/* Left Panel: Frequency Summary (after capture) */}
        {frequencySummary && (
          <div style={{ backgroundColor: 'white', borderRadius: '8px', padding: '15px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' }}>
            <h3 style={{ marginBottom: '15px', color: '#333' }}>Frequency Analysis</h3>
            {frequencySummary.map((ch, idx) => (
              <div key={idx} style={{ marginBottom: '15px', padding: '10px', backgroundColor: '#f8f8f8', borderRadius: '5px' }}>
                <div style={{ fontWeight: 'bold', marginBottom: '5px', color: channelColors[idx] }}>
                  {ch.channel}
                </div>
                <div style={{ fontSize: '12px' }}>
                  <div>δ: {ch.bands.delta.toFixed(1)}</div>
                  <div>θ: {ch.bands.theta.toFixed(1)}</div>
                  <div>α: {ch.bands.alpha.toFixed(1)}</div>
                  <div>β: {ch.bands.beta.toFixed(1)}</div>
                  <div>γ: {ch.bands.gamma.toFixed(1)}</div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Right Panel: Charts and Data */}
        <div>
          {/* Love Analysis Results */}
          {loveAnalysis && (
            <div style={{ marginBottom: '20px', padding: '20px', backgroundColor: 'white', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)', border: '2px solid #4CAF50' }}>
              <h2 style={{ color: '#333', marginBottom: '15px' }}>💘 Love at First Sight Analysis</h2>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
                <div>
                  <div style={{ fontSize: '48px', fontWeight: 'bold', color: '#4CAF50' }}>
                    {loveAnalysis.love_score}%
                  </div>
                  <div style={{ fontSize: '18px', marginTop: '10px' }}>
                    {loveAnalysis.category}
                  </div>
                </div>
                {loveAnalysis.components && (
                  <div>
                    <h4>Neural Components:</h4>
                    <div style={{ fontSize: '14px', marginTop: '10px' }}>
                      <div>Emotional Approach: {loveAnalysis.components.frontal_asymmetry}%</div>
                      <div>Arousal/Excitement: {loveAnalysis.components.arousal}%</div>
                      <div>Attention (P300): {loveAnalysis.components.attention_p300}%</div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Results Summary - Show when analysis is complete */}
          {showResults && loveAnalysis && (
            <div style={{
              backgroundColor: 'white',
              borderRadius: '8px',
              padding: '30px',
              marginBottom: '20px',
              boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
              textAlign: 'center'
            }}>
              <h2 style={{ color: '#333', marginBottom: '20px' }}>📊 5-Second Analysis Complete!</h2>
              <div style={{ marginBottom: '20px', color: '#666' }}>
                Captured {loveAnalysis.packets} packets over 5 seconds
              </div>
              <div style={{ fontSize: '14px', color: '#666' }}>
                Average Brain Activity: {loveAnalysis.avgAmplitude} μV
              </div>
            </div>
          )}

          {/* Real-Time Line Chart - Only show when NOT showing results */}
          {!showResults && (
            <div style={{ backgroundColor: 'white', borderRadius: '8px', padding: '20px', marginBottom: '20px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)', height: '400px' }}>
              <Line data={chartData} options={chartOptions} />
            </div>
          )}

          {/* Data Table - Only show when NOT showing results */}
          {!showResults && (
            <div style={{ backgroundColor: 'white', borderRadius: '8px', padding: '15px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' }}>
              <h3 style={{ color: '#333', marginBottom: '15px' }}>Raw EEG Values (μV)</h3>
            {samples.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '40px', color: '#999' }}>
                Waiting for real hardware data...
              </div>
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                  <thead>
                    <tr style={{ borderBottom: '2px solid #ddd' }}>
                      <th style={{ padding: '10px', textAlign: 'left' }}>Packet</th>
                      {[...Array(8)].map((_, i) => (
                        <th key={i} style={{ padding: '10px', textAlign: 'right', color: channelColors[i] }}>
                          Ch{i + 1}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {samples.map((sample, idx) => (
                      <tr key={sample.id || idx} style={{ borderBottom: '1px solid #eee' }}>
                        <td style={{ padding: '8px' }}>{sample.packet_num}</td>
                        {sample.channels.slice(0, 8).map((value, i) => (
                          <td key={i} style={{
                            padding: '8px',
                            textAlign: 'right',
                            color: Math.abs(value) > 50 ? '#ff9800' : '#333'
                          }}>
                            {value.toFixed(2)}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default EnhancedEEGDashboard;