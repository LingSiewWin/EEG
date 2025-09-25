// WebSocket Message Types
export interface EEGData {
  type: 'eeg';
  timestamp: number;
  packet_num: number;
  channels: number[];
  status: 'streaming';
}

export interface StatusMessage {
  type: 'status';
  message: string;
}

export interface AnalysisMessage {
  type: 'analysis';
  love_analysis: LoveAnalysis;
  frequency_summary: FrequencyBand[];
}

export type WebSocketMessage = EEGData | StatusMessage | AnalysisMessage;

// EEG Sample Types
export interface EEGSample {
  id: string;
  timestamp: number;
  channels: number[];
  packet_num: number;
}

// Love Analysis Types
export interface LoveAnalysisComponents {
  frontal_asymmetry: string;
  arousal: string;
  attention_p300: string;
}

export interface LoveAnalysis {
  love_score: string;
  category: string;
  avgAmplitude: string;
  packets: number;
  components: LoveAnalysisComponents;
}

// Frequency Analysis Types
export interface FrequencyBands {
  delta: number;
  theta: number;
  alpha: number;
  beta: number;
  gamma: number;
}

export interface FrequencyBand {
  channel: string;
  bands: FrequencyBands;
}

// Chart.js Types
export interface ChartDataset {
  label: string;
  data: number[];
  borderColor: string;
  backgroundColor: string;
  borderWidth: number;
  tension: number;
  pointRadius: number;
}

export interface ChartData {
  labels: (string | number)[];
  datasets: ChartDataset[];
}

// Connection Status
export type ConnectionStatus = 'Connected' | 'Disconnected' | 'Error';

// Image Analysis Types
export interface ImageResult {
  imageIndex: number;
  imagePath: string;
  loveScore: string;
  category: string;
  avgAmplitude?: string;
  frontalAsymmetry?: string;
  packets: number;
}

// Channel Statistics Types
export interface ChannelStats {
  channel: number;
  mean?: string;
  avgAmplitude: number;
  max?: string;
  min?: string;
}

// Component Props Types
export interface EEGDashboardProps {}

export interface ImageLoveAnalysisProps {}

// Ref Types
export interface CapturedDataRef {
  [imageIndex: number]: EEGSample[];
}