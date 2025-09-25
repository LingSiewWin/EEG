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
import type {
  EEGSample,
  ConnectionStatus,
  ChartData,
  ChartDataset,
  ImageResult,
  WebSocketMessage,
  EEGData,
  ChannelStats,
  CapturedDataRef,
  ImageLoveAnalysisProps
} from '../types';

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

const ImageLoveAnalysis: React.FC<ImageLoveAnalysisProps> = () => {
  // State management
  const [samples, setSamples] = useState<EEGSample[]>([]);
  const [connectionStatus, setConnectionStatus] = useState<ConnectionStatus>('Disconnected');
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [currentImageIndex, setCurrentImageIndex] = useState<number>(-1);
  const [countdown, setCountdown] = useState<number>(0);
  const [showInitialCountdown, setShowInitialCountdown] = useState<boolean>(false);
  const [imageResults, setImageResults] = useState<ImageResult[]>([]);
  const [showFinalResults, setShowFinalResults] = useState<boolean>(false);
  const [chartData, setChartData] = useState<ChartData>({
    labels: [],
    datasets: []
  });

  // Refs
  const wsRef = useRef<WebSocket | null>(null);
  const capturedDataRef = useRef<CapturedDataRef>({});
  const isCapturingRef = useRef<boolean>(false);
  const currentImageRef = useRef<number>(-1);
  const maxDataPoints = 250; // 1 second at 250Hz

  // Image paths - using the 5 images you provided
  const images: string[] = [
    '/photo/1.png',
    '/photo/2.jpeg',
    '/photo/3.jpeg',
    '/photo/4.jpeg',
    '/photo/5.png'
  ];

  // Chart colors for 8 channels
  const channelColors: string[] = [
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
      duration: 0
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
        position: 'top' as const,
      },
      title: {
        display: true,
        text: 'Real-Time EEG Signals'
      }
    }
  };

  useEffect(() => {
    // Initialize chart data
    const initialDatasets: ChartDataset[] = [];
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
      console.log('Connecting to WebSocket for image analysis...');
      const ws = new WebSocket('ws://localhost:8765');

      ws.onopen = () => {
        console.log('WebSocket connected for image love analysis');
        setConnectionStatus('Connected');
      };

      ws.onmessage = (event: MessageEvent) => {
        try {
          const data: WebSocketMessage = JSON.parse(event.data);

          if (data.type === 'status') {
            console.log('Status:', data.message);
          } else if (data.type === 'eeg') {
            const sample: EEGSample = {
              id: `${data.packet_num}_${Date.now()}_${Math.random()}`,
              timestamp: data.timestamp,
              channels: data.channels,
              packet_num: data.packet_num
            };

            // Update live view
            if (!showFinalResults) {
              setSamples(prev => [...prev, sample].slice(-10));

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

            // Capture data for current image
            if (isCapturingRef.current && currentImageRef.current >= 0) {
              const imageIdx = currentImageRef.current;
              if (!capturedDataRef.current[imageIdx]) {
                capturedDataRef.current[imageIdx] = [];
              }
              capturedDataRef.current[imageIdx].push(sample);
            }
          }
        } catch (error) {
          console.error('Error parsing WebSocket data:', error);
        }
      };

      ws.onerror = (error: Event) => {
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

    return () => {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.close();
      }
    };
  }, [showFinalResults]);

  const startImageAnalysis = () => {
    console.log('Starting image-based love analysis...');

    // Reset everything
    capturedDataRef.current = {};
    setImageResults([]);
    setShowFinalResults(false);
    setIsAnalyzing(true);
    setShowInitialCountdown(true);
    setCountdown(5);

    // Initial countdown (5,4,3,2,1)
    let initialCount = 5;
    const countInterval = setInterval(() => {
      initialCount--;
      setCountdown(initialCount);

      if (initialCount === 0) {
        clearInterval(countInterval);
        setShowInitialCountdown(false);
        // Start showing images
        showNextImage(0);
      }
    }, 1000);
  };

  const showNextImage = (imageIndex: number) => {
    if (imageIndex >= images.length) {
      // All images shown, analyze results
      analyzeAllImages();
      return;
    }

    console.log(`Showing image ${imageIndex + 1} of ${images.length}`);
    setCurrentImageIndex(imageIndex);
    currentImageRef.current = imageIndex;
    isCapturingRef.current = true;
    setCountdown(5);

    // Countdown for this image
    let imgCountdown = 5;
    const imgInterval = setInterval(() => {
      imgCountdown--;
      setCountdown(imgCountdown);

      if (imgCountdown === 0) {
        clearInterval(imgInterval);
        isCapturingRef.current = false;

        // Analyze this image's data
        const imageData = capturedDataRef.current[imageIndex] || [];
        console.log(`Image ${imageIndex + 1}: Captured ${imageData.length} packets`);

        // Move to next image
        setTimeout(() => {
          showNextImage(imageIndex + 1);
        }, 500);
      }
    }, 1000);
  };

  const analyzeAllImages = () => {
    console.log('Analyzing all images...');
    const results: ImageResult[] = [];

    for (let i = 0; i < images.length; i++) {
      const imageData = capturedDataRef.current[i] || [];

      if (imageData.length === 0) {
        results.push({
          imageIndex: i,
          imagePath: images[i],
          loveScore: '0',
          category: 'No data',
          packets: 0
        });
        continue;
      }

      // Analyze each image's EEG data
      const analysis = analyzeImageData(imageData, i);
      results.push(analysis);
    }

    // Find winner
    const winner = results.reduce((max, curr) =>
      parseFloat(curr.loveScore) > parseFloat(max.loveScore) ? curr : max, results[0]);

    setImageResults(results);
    setCurrentImageIndex(-1);
    setIsAnalyzing(false);
    setShowFinalResults(true);

    console.log('Analysis complete!', results);
    console.log('Winner:', winner);
  };

  const analyzeImageData = (imageData: EEGSample[], imageIndex: number): ImageResult => {
    // Calculate statistics for this image
    const channelStats: ChannelStats[] = [];

    for (let ch = 0; ch < 8; ch++) {
      const channelData = imageData.map(sample => sample.channels[ch] || 0);

      const mean = channelData.reduce((a, b) => a + b, 0) / channelData.length;
      const absValues = channelData.map(v => Math.abs(v));
      const avgAmplitude = absValues.reduce((a, b) => a + b, 0) / absValues.length;

      channelStats.push({
        channel: ch + 1,
        avgAmplitude: avgAmplitude
      });
    }

    // Frontal asymmetry (Ch1-Fp1 vs Ch2-Fp2)
    const leftFrontal = channelStats[0].avgAmplitude;
    const rightFrontal = channelStats[1].avgAmplitude;
    const frontalAsymmetry = (rightFrontal - leftFrontal) / (rightFrontal + leftFrontal);

    // Average amplitude as arousal
    const avgAmp = channelStats.reduce((sum, ch) => sum + ch.avgAmplitude, 0) / 8;

    // Calculate love score
    let loveScore = 50;

    // Positive frontal asymmetry = approach motivation
    if (frontalAsymmetry > 0) {
      loveScore += frontalAsymmetry * 30;
    }

    // Higher amplitude = more arousal/interest
    if (avgAmp > 20) loveScore += 10;
    if (avgAmp > 40) loveScore += 15;
    if (avgAmp > 60) loveScore += 15;

    loveScore = Math.min(100, Math.max(0, loveScore));

    // Category
    let category = '';
    if (loveScore >= 80) category = 'Love at First Sight! 💘';
    else if (loveScore >= 60) category = 'Strong Attraction 💕';
    else if (loveScore >= 40) category = 'Interested 💗';
    else if (loveScore >= 20) category = 'Neutral 😐';
    else category = 'Not Interested 💔';

    return {
      imageIndex: imageIndex,
      imagePath: images[imageIndex],
      loveScore: loveScore.toFixed(1),
      category: category,
      avgAmplitude: avgAmp.toFixed(2),
      frontalAsymmetry: (50 + frontalAsymmetry * 50).toFixed(1),
      packets: imageData.length
    };
  };

  const getStatusColor = (): string => {
    switch (connectionStatus) {
      case 'Connected': return '#4CAF50';
      case 'Disconnected': return '#f44336';
      case 'Error': return '#ff9800';
      default: return '#9e9e9e';
    }
  };

  return (
    <div style={{ fontFamily: 'Arial, sans-serif', padding: '20px', backgroundColor: '#f5f5f5', minHeight: '100vh' }}>
      <h1 style={{ color: '#333', marginBottom: '20px' }}>💘 Image-Based Love Detection System</h1>

      {/* Connection Status */}
      <div style={{ marginBottom: '20px', padding: '15px', backgroundColor: 'white', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <span style={{ fontWeight: 'bold' }}>Status: </span>
            <span style={{ color: getStatusColor(), fontWeight: 'bold' }}>{connectionStatus}</span>
          </div>
          <button
            onClick={startImageAnalysis}
            disabled={connectionStatus !== 'Connected' || isAnalyzing}
            style={{
              background: isAnalyzing ? '#ff9800' : '#4CAF50',
              color: 'white',
              border: 'none',
              padding: '10px 20px',
              borderRadius: '5px',
              cursor: connectionStatus === 'Connected' && !isAnalyzing ? 'pointer' : 'not-allowed',
              fontSize: '14px',
              fontWeight: 'bold',
              minWidth: '250px'
            }}
          >
            {isAnalyzing ? 'ANALYZING...' : 'START IMAGE LOVE ANALYSIS'}
          </button>
        </div>
      </div>

      {/* Initial Countdown Overlay */}
      {showInitialCountdown && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.8)',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          zIndex: 1000
        }}>
          <div style={{ color: 'white', fontSize: '48px', marginBottom: '20px' }}>
            Get Ready!
          </div>
          <div style={{ color: 'white', fontSize: '120px', fontWeight: 'bold' }}>
            {countdown}
          </div>
        </div>
      )}

      {/* Image Display with Countdown */}
      {currentImageIndex >= 0 && !showInitialCountdown && (
        <div style={{
          position: 'fixed',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          backgroundColor: 'rgba(0,0,0,0.9)',
          display: 'flex',
          flexDirection: 'column',
          justifyContent: 'center',
          alignItems: 'center',
          zIndex: 999
        }}>
          <div style={{
            position: 'absolute',
            top: '20px',
            right: '20px',
            color: 'white',
            fontSize: '36px',
            fontWeight: 'bold',
            backgroundColor: 'rgba(255,0,0,0.5)',
            padding: '10px 20px',
            borderRadius: '10px'
          }}>
            {countdown}
          </div>
          <div style={{
            position: 'absolute',
            top: '20px',
            left: '20px',
            color: 'white',
            fontSize: '24px',
            backgroundColor: 'rgba(0,0,0,0.5)',
            padding: '10px',
            borderRadius: '5px'
          }}>
            Image {currentImageIndex + 1} of {images.length}
          </div>
          <img
            src={images[currentImageIndex]}
            alt={`Test image ${currentImageIndex + 1}`}
            style={{
              maxWidth: '80%',
              maxHeight: '80%',
              objectFit: 'contain',
              borderRadius: '10px',
              boxShadow: '0 4px 20px rgba(0,0,0,0.5)'
            }}
          />
          <div style={{
            position: 'absolute',
            bottom: '20px',
            color: 'white',
            fontSize: '18px',
            backgroundColor: 'rgba(0,0,0,0.5)',
            padding: '10px 20px',
            borderRadius: '5px'
          }}>
            Recording EEG response...
          </div>
        </div>
      )}

      {/* Final Results */}
      {showFinalResults && imageResults.length > 0 && (
        <div style={{ marginBottom: '20px' }}>
          <div style={{ backgroundColor: 'white', borderRadius: '8px', padding: '20px', marginBottom: '20px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' }}>
            <h2 style={{ color: '#333', marginBottom: '20px' }}>🏆 Analysis Results - Which Image Won Your Heart?</h2>

            {/* Winner Highlight */}
            {(() => {
              const winner = imageResults.reduce((max, curr) =>
                parseFloat(curr.loveScore) > parseFloat(max.loveScore) ? curr : max, imageResults[0]);

              return (
                <div style={{
                  backgroundColor: '#4CAF50',
                  color: 'white',
                  padding: '20px',
                  borderRadius: '10px',
                  marginBottom: '30px',
                  textAlign: 'center'
                }}>
                  <h3 style={{ margin: '0 0 10px 0' }}>🎉 WINNER: Image {winner.imageIndex + 1}</h3>
                  <div style={{ fontSize: '48px', fontWeight: 'bold' }}>{winner.loveScore}%</div>
                  <div style={{ fontSize: '24px' }}>{winner.category}</div>
                  <img
                    src={winner.imagePath}
                    alt="Winner"
                    style={{
                      width: '200px',
                      height: '200px',
                      objectFit: 'cover',
                      borderRadius: '10px',
                      marginTop: '20px',
                      border: '3px solid white'
                    }}
                  />
                </div>
              );
            })()}

            {/* All Results Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '20px' }}>
              {imageResults.map((result, idx) => (
                <div key={idx} style={{
                  padding: '15px',
                  backgroundColor: '#f8f8f8',
                  borderRadius: '10px',
                  textAlign: 'center',
                  border: parseFloat(result.loveScore) === Math.max(...imageResults.map(r => parseFloat(r.loveScore))) ? '3px solid #4CAF50' : '1px solid #ddd'
                }}>
                  <img
                    src={result.imagePath}
                    alt={`Image ${idx + 1}`}
                    style={{
                      width: '100%',
                      height: '150px',
                      objectFit: 'cover',
                      borderRadius: '8px',
                      marginBottom: '10px'
                    }}
                  />
                  <div style={{ fontWeight: 'bold', marginBottom: '5px' }}>
                    Image {idx + 1}
                  </div>
                  <div style={{ fontSize: '24px', color: '#4CAF50', fontWeight: 'bold' }}>
                    {result.loveScore}%
                  </div>
                  <div style={{ fontSize: '12px', marginTop: '5px' }}>
                    {result.category}
                  </div>
                  <div style={{ fontSize: '11px', color: '#666', marginTop: '5px' }}>
                    Avg: {result.avgAmplitude}μV | FA: {result.frontalAsymmetry}%
                  </div>
                </div>
              ))}
            </div>

            {/* Restart Button */}
            <div style={{ textAlign: 'center', marginTop: '30px' }}>
              <button
                onClick={() => {
                  setShowFinalResults(false);
                  setImageResults([]);
                  setCurrentImageIndex(-1);
                }}
                style={{
                  background: '#2196F3',
                  color: 'white',
                  border: 'none',
                  padding: '12px 30px',
                  borderRadius: '5px',
                  cursor: 'pointer',
                  fontSize: '16px',
                  fontWeight: 'bold'
                }}
              >
                RETURN TO LIVE VIEW
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Live EEG Chart (in background) */}
      {!showFinalResults && (
        <div style={{ backgroundColor: 'white', borderRadius: '8px', padding: '20px', marginBottom: '20px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)', height: '400px' }}>
          <Line data={chartData} options={chartOptions} />
        </div>
      )}

      {/* Live Data Table */}
      {!showFinalResults && (
        <div style={{ backgroundColor: 'white', borderRadius: '8px', padding: '15px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)' }}>
          <h3 style={{ color: '#333', marginBottom: '15px' }}>Live EEG Values (μV)</h3>
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
  );
};

export default ImageLoveAnalysis;