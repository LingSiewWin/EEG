import React, { useState, useEffect, useRef } from 'react';

const EEGDashboard = () => {
  const [samples, setSamples] = useState([]);
  const [connectionStatus, setConnectionStatus] = useState('Disconnected');
  const [lastUpdate, setLastUpdate] = useState(null);
  const [totalSamples, setTotalSamples] = useState(0);
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
            setTotalSamples(data.total_samples || 0);
          } else if (data.type === 'eeg_data') {
            console.log(`Received ${data.sample_count} samples`);

            // Add new samples to display (keep last 10)
            setSamples(prev => {
              const newSamples = data.samples.map((sample, idx) => ({
                ...sample,
                id: Date.now() + idx,
                sampleNum: totalSamples + idx + 1
              }));
              return [...prev, ...newSamples].slice(-10);
            });

            setTotalSamples(prev => prev + data.sample_count);
            setLastUpdate(new Date());
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

        // Reconnect after 3 seconds
        setTimeout(() => {
          if (wsRef.current !== 'stopped') {
            connectWebSocket();
          }
        }, 3000);
      };

      wsRef.current = ws;
    };

    connectWebSocket();

    // Cleanup on unmount
    return () => {
      wsRef.current = 'stopped';
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.close();
      }
    };
  }, [totalSamples]);

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

  return (
    <div style={{ fontFamily: 'monospace', padding: '20px', backgroundColor: '#1e1e1e', color: '#fff', minHeight: '100vh' }}>
      <h1 style={{ color: '#4CAF50', marginBottom: '20px' }}>🧠 REAL OpenBCI Hardware Dashboard</h1>

      {/* Connection Status */}
      <div style={{ marginBottom: '20px', padding: '15px', backgroundColor: '#2a2a2a', borderRadius: '5px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '10px' }}>
          <span>
            Status: <span style={{ color: getStatusColor(), fontWeight: 'bold' }}>{connectionStatus}</span>
          </span>
          <span>Total Samples: <span style={{ color: '#4CAF50' }}>{totalSamples}</span></span>
        </div>
        {lastUpdate && (
          <div>Last Update: {lastUpdate.toLocaleTimeString()}</div>
        )}
        <div style={{ marginTop: '5px', fontSize: '12px', color: '#888' }}>
          Source: authentic_openbci_hardware (b'\xff' packets → 12.7 μV)
        </div>
      </div>

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
                  <th style={{ padding: '10px', textAlign: 'left' }}>Sample #</th>
                  <th style={{ padding: '10px', textAlign: 'left' }}>Timestamp</th>
                  <th style={{ padding: '10px', textAlign: 'right', color: '#4CAF50' }}>Ch 1 (μV)</th>
                  {[...Array(15)].map((_, i) => (
                    <th key={i} style={{ padding: '10px', textAlign: 'right', color: '#666' }}>
                      Ch {i + 2}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {samples.map((sample, idx) => (
                  <tr key={sample.id || idx} style={{ borderBottom: '1px solid #444' }}>
                    <td style={{ padding: '8px' }}>{sample.sampleNum || idx + 1}</td>
                    <td style={{ padding: '8px', fontSize: '12px' }}>
                      {formatTimestamp(sample.timestamp)}
                    </td>
                    <td style={{
                      padding: '8px',
                      textAlign: 'right',
                      color: sample.channels[0] === 12.7 ? '#4CAF50' : '#fff',
                      fontWeight: sample.channels[0] === 12.7 ? 'bold' : 'normal'
                    }}>
                      {sample.channels[0].toFixed(1)}
                    </td>
                    {sample.channels.slice(1).map((value, i) => (
                      <td key={i} style={{ padding: '8px', textAlign: 'right', color: '#666' }}>
                        {value.toFixed(1)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <div style={{ marginTop: '15px', fontSize: '12px', color: '#888' }}>
          Showing last {samples.length} samples • Channel 1 shows real hardware value (12.7 μV from b'\xff')
        </div>
      </div>

      {/* Info Box */}
      <div style={{ marginTop: '20px', padding: '15px', backgroundColor: '#2a2a2a', borderRadius: '5px', fontSize: '12px' }}>
        <div style={{ color: '#4CAF50', marginBottom: '5px' }}>ℹ️ Hardware Info</div>
        <div>• Device: OpenBCI Cyton+Daisy (16 channels)</div>
        <div>• Port: /dev/cu.usbserial-DM01MV82</div>
        <div>• Baud: 230400</div>
        <div>• Mode: Listen-only (no commands sent)</div>
        <div>• Data: Real b'\xff' acknowledgment packets</div>
      </div>
    </div>
  );
};

export default EEGDashboard;