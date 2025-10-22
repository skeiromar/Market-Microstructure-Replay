// /Users/omarm/My_Projects/trading/L2Replay/frontend/src/lib/utils/websocketStore.ts
import { browser } from '$app/environment';
// Import writable from svelte/store
import { writable } from 'svelte/store';
import type {
	L2State,
	Trade,
	BackendMessage,
	BackendCommand,
	ConnectionStatus,
	Level
} from '$lib/types';

// Configuration
const WEBSOCKET_URL = 'ws://localhost:8765';
const RECONNECT_DELAY_MS = 5000;
const MAX_TRADES_DISPLAY = 50;

// --- Internal State ---
let ws: WebSocket | undefined = undefined;
let reconnectTimeoutId: ReturnType<typeof setTimeout> | undefined = undefined;

// --- Use writable stores instead of $state ---
const connectionStatus = writable<ConnectionStatus>('connecting');
const l2Data = writable<L2State>({ bids: [], asks: [] });
const trades = writable<Trade[]>([]);
const latestTimestamp = writable<number | null>(null); // Store for nanosecond timestamp

// --- Helper Functions ---
function transformRawLevels(rawLevels: [string, number][]): Level[] {
	// ... (function remains the same)
	if (!Array.isArray(rawLevels)) return [];
	return rawLevels
		.map(([priceStr, volumeInt]) => ({
			price: parseFloat(priceStr),
			volume: volumeInt
		}))
		.filter((level) => !isNaN(level.price) && level.volume > 0);
}

async function parseMessage(data: string | Blob): Promise<BackendMessage | null> {
	// ... (function remains the same)
	let textData: string;
	try {
		if (data instanceof Blob) {
			console.debug('Received Blob data, converting to text...');
			textData = await data.text();
		} else if (typeof data === 'string') {
			textData = data;
		} else {
			console.warn('Received unexpected data type:', typeof data);
			return null;
		}
		return JSON.parse(textData) as BackendMessage;
	} catch (e) {
		console.error(
			'Failed to parse WebSocket message:',
			e,
			'Raw data:',
			data instanceof Blob ? '[Blob]' : textData!
		);
		return null;
	}
}

function handleIncomingMessage(message: BackendMessage) {
	switch (message.type) {
		case 'l2_update':
			// Use .set() to update writable store
			console.log(message.data)
			l2Data.set({
				bids: transformRawLevels(message.data.bids),
				asks: transformRawLevels(message.data.asks)
			});
			latestTimestamp.set(message.data.timestamp);
			break;
		case 'new_trade':
			// Use .update() for modifying array stores
			console.log(message.data)
			trades.update((currentTrades) => {
				const newTrades = [message.data, ...currentTrades];
				if (newTrades.length > MAX_TRADES_DISPLAY) {
					newTrades.length = MAX_TRADES_DISPLAY;
				}
				return newTrades;
			});
			break;
		case 'error':
			console.error('Backend Error Message:', message.message);
			break;
		default:
			console.warn('Received unknown message type:', message);
	}
}

function connect() {
	if (!browser) return;
	// Check store value using get() if needed outside component scope, but usually check ws state
	// if (get(connectionStatus) === 'connected' || get(connectionStatus) === 'connecting') return;
	if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) return;

	console.log(`Attempting to connect to ${WEBSOCKET_URL}...`);
	// Use .set() to update writable store
	connectionStatus.set('connecting');
	clearTimeout(reconnectTimeoutId);

	if (ws) {
		ws.onopen = null;
		ws.onmessage = null;
		ws.onerror = null;
		ws.onclose = null;
		ws.close();
	}

	ws = new WebSocket(WEBSOCKET_URL);

	ws.onopen = () => {
		console.log('WebSocket Connection opened');
		// Use .set()
		connectionStatus.set('connected');
	};

	ws.onerror = (error) => {
		console.error('WebSocket Error:', error);
		// Use .set()
		connectionStatus.set('error');
		ws?.close();
	};

	ws.onclose = (event) => {
		console.log('WebSocket Connection closed:', event.code, event.reason);
		ws = undefined;
		// Use .update() to check previous state if needed, or just set based on logic
		connectionStatus.update((currentStatus) => {
			if (currentStatus !== 'error') {
				// Use .set() inside update if logic is simple, or return new value
				connectionStatus.set('closed'); // Set directly before scheduling reconnect
			}
			// Schedule reconnect regardless of previous state if closed unexpectedly
			console.log(`Scheduling reconnect in ${RECONNECT_DELAY_MS / 1000}s...`);
			connectionStatus.set('reconnecting'); // Indicate reconnection attempt
			reconnectTimeoutId = setTimeout(connect, RECONNECT_DELAY_MS);
			return 'reconnecting'; // Return value for update if needed, but set is fine here
		});
	};

	ws.onmessage = async (event) => {
		const message = await parseMessage(event.data);
		if (message) {
			handleIncomingMessage(message);
		}
	};
}

function disconnect() {
	if (!browser) return;
	console.log('Manual disconnect requested.');
	clearTimeout(reconnectTimeoutId);
	if (ws) {
		ws.onclose = null;
		ws.close();
		ws = undefined;
	}
	// Use .set()
	connectionStatus.set('closed');
	// Optionally clear data
	// l2Data.set({ bids: [], asks: [] });
	// trades.set([]);
}

function sendCommand(command: BackendCommand) {
	// ... (function remains the same)
	if (ws && ws.readyState === WebSocket.OPEN) {
		try {
			ws.send(JSON.stringify(command));
		} catch (e) {
			console.error('Failed to send command:', command, e);
		}
	} else {
		console.error('WebSocket not connected. Cannot send command:', command);
	}
}

// --- Auto-connect on load ---
if (browser) {
	connect();
}

export { connectionStatus, l2Data, trades, latestTimestamp };
// Export the actions separately
export { sendCommand, connect, disconnect };

// Optional: Cleanup on HMR (Vite specific)
if (import.meta.hot) {
	import.meta.hot.dispose(() => {
		console.log('HMR Dispose: Closing WebSocket');
		disconnect();
	});
}
