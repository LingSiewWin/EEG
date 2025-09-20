import React, { useState, useEffect, useRef } from 'react';

const EEGDashboard = () => {
  const [samples, setSamples] = useState([]);
  const [connectionStatus, setConnectionStatus] = useState('Disconnected');
  const [lastUpdate, setLastUpdate] = useState(null);
  const [totalSamples, setTotalSamples] = useState(0);
  const [isCapturing, setIsCapturing] = useState(false);
  const [capturedData, setCapturedData] = useState([]);
  const [loveScore, setLoveScore] = useState(null);
  const wsRef = useRef(null);

  useEffect(() => {
    // Connect to WebSocket server
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
            // Real-time EEG data from CORRECT_SCALE.py format
            const sample = {
              id: Date.now(),
              timestamp: data.timestamp,
              channels: data.channels,
              packet_num: data.packet_num
            };

            // Update samples display (keep last 10)
            setSamples(prev => [...prev, sample].slice(-10));
            setTotalSamples(data.packet_num);
            setLastUpdate(new Date());

            // If capturing for love detection
            if (isCapturing) {
              setCapturedData(prev => [...prev, sample]);
            }
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

        // Don't auto-reconnect - let user control connection
        // User can refresh page to reconnect
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

  const formatTimestamp = (timestamp) => {
    const date = new Date(timestamp * 1000);
    return date.toLocaleTimeString('en-US', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      fractionalSecondDigits: 3
    });
  };

  const getStatusColor = () => {
    switch (connectionStatus) {
      case 'Connected': return '#4CAF50';
      case 'Disconnected': return '#f44336';
      case 'Error': return '#ff9800';
      default: return '#9e9e9e';
    }
  };

  const startCapture = () => {
    setIsCapturing(true);
    setCapturedData([]);
    setLoveScore(null);

    // Capture for 5 seconds
    setTimeout(() => {
      setIsCapturing(false);
      analyzeLove();
    }, 5000);
  };

  const analyzeLove = () => {
    if (capturedData.length === 0) return;

    // Calculate average amplitude
    let totalAmp = 0;
    let count = 0;

    capturedData.forEach(sample => {
      sample.channels.forEach(ch => {
        totalAmp += Math.abs(ch);
        count++;
      });
    });

    const avgAmp = totalAmp / count;

    // Love score based on real μV ranges
    let score = 0;
    let status = '';

    if (avgAmp < 20) {
      score = 30;
      status = 'Calm/Neutral';
    } else if (avgAmp < 40) {
      score = 60;
      status = 'Interested';
    } else if (avgAmp < 60) {
      score = 80;
      status = 'Excited';
    } else {
      score = 95;
      status = 'Very Attracted!';
    }

    setLoveScore({
      score,
      status,
      avgAmplitude: avgAmp,
      packets: capturedData.length
    });
  };

  return (
    <div style={{ fontFamily: 'monospace', padding: '20px', backgroundColor: '#1e1e1e', color: '#fff', minHeight: '100vh' }}>
      <h1 style={{ color: '#4CAF50', marginBottom: '20px' }}>🧠 REAL OpenBCI Hardware Dashboard</h1>

      {/* Connection Status */}
      <div style={{ marginBottom: '20px', padding: '15px', backgroundColor: '#2a2a2a', borderRadius: '5px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
          <span>
            Status: <span style={{ color: getStatusColor(), fontWeight: 'bold' }}>{connectionStatus}</span>
          </span>
          <span>Packets: <span style={{ color: '#4CAF50' }}>{totalSamples}</span></span>
        </div>
        {lastUpdate && (
          <div>Last Update: {lastUpdate.toLocaleTimeString()}</div>
        )}
        <div style={{ marginTop: '10px' }}>
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
              fontWeight: 'bold'
            }}
          >
            {isCapturing ? 'CAPTURING...' : 'CAPTURE 5 SECONDS FOR LOVE DETECTION'}
          </button>
        </div>
      </div>

      {/* Love Score Display */}
      {loveScore && (
        <div style={{ marginBottom: '20px', padding: '15px', backgroundColor: '#2a2a2a', borderRadius: '5px', border: '2px solid #4CAF50' }}>
          <h2 style={{ color: '#4CAF50', marginBottom: '10px' }}>💕 Love at First Sight Analysis</h2>
          <div>Love Score: <span style={{ fontSize: '24px', color: '#4CAF50', fontWeight: 'bold' }}>{loveScore.score}%</span></div>
          <div>Status: {loveScore.status}</div>
          <div>Average Amplitude: {loveScore.avgAmplitude.toFixed(2)} μV</div>
          <div>Packets Analyzed: {loveScore.packets}</div>
        </div>
      )}

      {/* Data Table */}
      <div style={{ backgroundColor: '#2a2a2a', borderRadius: '5px', padding: '15px' }}>
        <h2 style={{ color: '#4CAF50', marginBottom: '15px' }}>📊 Live EEG Data (μV)</h2>

        {samples.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '40px', color: '#888' }}>
            Waiting for real hardware data...
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '2px solid #4CAF50' }}>
                  <th style={{ padding: '10px', textAlign: 'left' }}>Packet #</th>
                  <th style={{ padding: '10px', textAlign: 'left' }}>Timestamp</th>
                  {[...Array(8)].map((_, i) => (
                    <th key={i} style={{ padding: '10px', textAlign: 'right', color: i === 0 ? '#4CAF50' : '#888' }}>
                      Ch {i + 1} (μV)
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {samples.map((sample, idx) => (
                  <tr key={sample.id || idx} style={{ borderBottom: '1px solid #444' }}>
                    <td style={{ padding: '8px' }}>{sample.packet_num || idx + 1}</td>
                    <td style={{ padding: '8px', fontSize: '12px' }}>
                      {formatTimestamp(sample.timestamp)}
                    </td>
                    {sample.channels.slice(0, 8).map((value, i) => (
                      <td key={i} style={{
                        padding: '8px',
                        textAlign: 'right',
                        color: Math.abs(value) > 50 ? '#ff9800' : (Math.abs(value) > 20 ? '#4CAF50' : '#888'),
                        fontWeight: Math.abs(value) > 40 ? 'bold' : 'normal'
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

        <div style={{ marginTop: '15px', fontSize: '12px', color: '#888' }}>
          Showing last {samples.length} samples • Real-time EEG at correct μV scale (±50μV normal range)
        </div>
      </div>

      {/* Info Box */}
      <div style={{ marginTop: '20px', padding: '15px', backgroundColor: '#2a2a2a', borderRadius: '5px', fontSize: '12px' }}>
        <div style={{ color: '#4CAF50', marginBottom: '5px' }}>ℹ️ Hardware Info</div>
        <div>• Device: OpenBCI Cyton (8 channels active)</div>
        <div>• Port: /dev/cu.usbserial-DM01MV82</div>
        <div>• Baud: 115200</div>
        <div>• Scale: CORRECT (0.02235/1000 = real μV)</div>
        <div>• Data: REAL streaming packets (0xA0...0xC0)</div>
        <div style={{ marginTop: '10px', color: '#4CAF50' }}>
          ✓ NO FAKE DATA - This is your actual brain activity!
        </div>
      </div>
    </div>
  );
};

export default EEGDashboard;