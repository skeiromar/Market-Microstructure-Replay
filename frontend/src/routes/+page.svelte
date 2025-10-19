<!-- /Users/omarm/My_Projects/trading/L2Replay/frontend/src/routes/+page.svelte -->
<script lang="ts">
	import { onDestroy } from 'svelte';
	import L2Display from '$lib/components/L2Display.svelte';
	import TradesDisplay from '$lib/components/TradesDisplay.svelte';
	import {
		connectionStatus, // The store itself
		l2Data, // The store itself
		trades, // The store itself
		latestTimestamp,
		sendCommand, // Action
		disconnect // Action
	} from '$lib/utils/websocketStore';
	import { formatTimestamp, seekToTimestamp } from '$lib/utils/helpers';

	// --- Local State for Seek Input ---
  let seekDateTimeInput = ''; // For datetime-local input binding

	// --- Lifecycle ---
	onDestroy(() => {
		// disconnect(); // Optional disconnect
	});

	// --- Control Functions ---
	const play = () => sendCommand({ command: 'play' });
	const pause = () => sendCommand({ command: 'pause' });
	const setSpeed = (speed: number) => sendCommand({ command: 'set_speed', value: speed });
</script>

<main class="container">
	<h1>Market Replay</h1>
	<!-- Use $ prefix for reactive access to store values -->
	<div class="status-bar">
		<!-- ADD wrapper div -->
		<p>Status: {$connectionStatus}</p>
		<!-- ADD Timestamp Display -->
		<p class="timestamp">Replay Time: {formatTimestamp($latestTimestamp)}</p>
	</div>

	{#if $connectionStatus === 'connected'}
		<div class="data-display-area">
			<!-- ADD wrapper for L2 and Trades -->
			<L2Display bids={$l2Data.bids} asks={$l2Data.asks} />
			<TradesDisplay />
		</div>
		<div class="controls-placeholder">
			<h2>Controls</h2>
			<button onclick={play}>Play</button>
			<button onclick={pause}>Pause</button>
			<button onclick={() => setSpeed(0.5)}>Speed 0.5x</button>
			<button onclick={() => setSpeed(1.0)}>Speed 1x</button>
			<button onclick={() => setSpeed(2.0)}>Speed 2x</button>
		</div>
    <div class="seek-controls">
      <input
          type="datetime-local"
          bind:value={seekDateTimeInput}
          aria-label="Seek Timestamp"
          step="0.001"
      />
      <!-- UPDATE button's on:click handler -->
      <button onclick={() => seekToTimestamp(seekDateTimeInput, sendCommand)}>Seek</button>
  </div>
	{:else if $connectionStatus === 'connecting' || $connectionStatus === 'reconnecting'}
		<p>
			{$connectionStatus === 'connecting' ? 'Connecting' : 'Reconnecting'} to replay server (ws://localhost:8765)...
		</p>
	{:else if $connectionStatus === 'error'}
		<p class="error-message">
			Connection error. Please ensure the backend server (main.py) is running and check console
			logs.
		</p>
		<!-- <button on:click={connect}>Retry Connection</button> -->
	{:else}
		<!-- closed -->
		<p>Connection closed.</p>
		<!-- <button on:click={connect}>Reconnect</button> -->
	{/if}
</main>

<style>
	/* Styles remain the same */
	.container {
		max-width: 1000px;
		margin: 1rem auto;
		padding: 1rem;
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}
	h1 {
		text-align: center;
		color: #eee;
	}
	p {
		color: #ccc;
	}
	.status-bar {
		display: flex;
		justify-content: space-between;
		align-items: center;
		background-color: #2a2a2a;
		padding: 0.25rem 0.75rem;
		border-radius: 4px;
		font-size: 0.9em;
	}
	.status-bar p {
		margin: 0;
		color: #ccc;
	}
	.timestamp {
		font-family: 'Courier New', Courier, monospace;
		color: #eee;
		font-weight: bold;
	}
	.error-message {
		color: #e74c3c;
		font-weight: bold;
	}
	.data-display-area {
		display: grid;
		grid-template-columns: 2fr 1fr; /* L2 takes more space */
		gap: 1rem; /* Gap between L2 and Trades */
		align-items: start; /* Align items to the top */
	}
	.controls-placeholder button {
		margin-right: 5px;
		padding: 5px 10px;
		background-color: #333;
		color: #eee;
		border: 1px solid #555;
		cursor: pointer;
	}
	.controls-placeholder button:hover {
		background-color: #444;
	}
	:global(body) {
		background-color: #121212;
		color: #e0e0e0;
	}
</style>
