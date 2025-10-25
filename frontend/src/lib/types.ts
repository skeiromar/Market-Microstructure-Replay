// --- General Market Data Types ---

// Represents a single price level in the order book
// Used as input prop for L2Display and internal state
export type Level = {
  price: number; // Numeric price (transformed from string)
  volume: number;
};

// Represents the overall L2 order book state
export type L2State = {
  bids: Level[];
  asks: Level[];
};

// Represents a single trade event (matches backend structure)
export type Trade = {
  timestamp: number; // Nanoseconds since epoch
  price: string;     // Price as string (matching backend)
  size: number;
  side: string;      // Aggressor side ('A', 'B', 'N')
  flags: number | null;
  sequence: number | null;
};

// --- WebSocket Specific Types ---

// Defines the structure of messages received from the backend WebSocket
export type BackendMessage =
  | { type: 'l2_update'; data: { timestamp: number; bids: [string, number][]; asks: [string, number][] } }
  | { type: 'new_trade'; data: Trade }
  | { type: 'error'; message: string }; // Example error message type

// Defines the structure for commands sent TO the backend
export type BackendCommand =
  | { command: 'play' }
  | { command: 'pause' }
  | { command: 'set_speed'; value: number }
  | { command: 'seek'; timestamp_ns: number };

// Represents the connection status of the WebSocket
export type ConnectionStatus = 'connecting' | 'connected' | 'error' | 'closed' | 'reconnecting';


// --- L2 Display Specific Types ---

// Represents a processed level with calculated cumulative volume and formatted price
// Used internally within L2Display component
export type ProcessedLevel = Level & {
  cumulativeVolume: number;
  formattedPrice: string;
};
