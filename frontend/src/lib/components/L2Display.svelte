<!-- /Users/omarm/My_Projects/trading/L2Replay/frontend/src/lib/components/L2Display.svelte -->
<script lang="ts">
	import type { Level, ProcessedLevel } from '$lib/types';

	type Props = {
		bids: Level[];
		asks: Level[];
	};

	let { bids = [], asks = [] }: Props = $props();
	// Remove the explicit cast 'as ProcessedLevel[]'
	// TypeScript should infer the return type of the function inside $derived
	const processedBids = $derived(() => {
		let cumulativeVolume = 0;
		const sortedBids = [...bids].sort((a, b) => b.price - a.price);
		// The return value here IS ProcessedLevel[]
		return sortedBids.map((bid): ProcessedLevel => {
			// Optional: Add return type hint to map lambda
			cumulativeVolume += bid.volume;
			return {
				...bid,
				cumulativeVolume: cumulativeVolume,
				formattedPrice: bid.price.toFixed(9)
			};
		});
	}); // <-- Removed cast

    // $effect(() => {
    //     console.log('processedBids updated:', processedBids());
    // });

	// Remove the explicit cast 'as ProcessedLevel[]'
	const processedAsks = $derived(() => {
		let cumulativeVolume = 0;
		const sortedAsks = [...asks].sort((a, b) => a.price - b.price);
		// The return value here IS ProcessedLevel[]
		return sortedAsks.map((ask): ProcessedLevel => {
			// Optional: Add return type hint to map lambda
			cumulativeVolume += ask.volume;
			return {
				...ask,
				cumulativeVolume: cumulativeVolume,
				formattedPrice: ask.price.toFixed(9)
			};
		});
	}); // <-- Removed cast

	const maxCumulativeVolume = $derived(() => {
		// Access the derived arrays directly. Svelte's reactivity tracks these.
		// Assigning them to intermediate constants might help TS, but direct access should work.
		const bidsArray: ProcessedLevel[] = processedBids();
		const asksArray: ProcessedLevel[] = processedAsks();

		// Get the last element safely
		const lastBid = bidsArray[bidsArray.length - 1];
		const lastAsk = asksArray[asksArray.length - 1];

		// Calculate cumulative volumes (same as before)
		const lastBidCumulative = lastBid?.cumulativeVolume ?? 0;
		const lastAskCumulative = lastAsk?.cumulativeVolume ?? 0;

		// Return the max value - this is the actual number result
		return Math.max(lastBidCumulative, lastAskCumulative, 1);
	});

       // Calculate total volume visible in this component instance
       const totalVisibleVolume = $derived(() => {
        const bidsVol = processedBids().reduce((sum, level) => sum + level.volume, 0);
        const asksVol = processedAsks().reduce((sum, level) => sum + level.volume, 0);
        return Math.max(bidsVol + asksVol, 1); // Ensure at least 1 to avoid division by zero
    });
</script>

<!-- Template remains the same -->
<div class="l2-container">
	<!-- Bids Column -->
	<div class="l2-column bids-column">
		<table class="l2-table">
			<thead>
				<tr>
					<th class="cumulative">C</th>
					<th class="volume">T</th>
					<th class="price">Bid</th>
				</tr>
			</thead>
			<tbody>
				<!-- Access derived value directly in template -->
				{#each processedBids() as bid (bid.price)}
					<tr class="l2-row bid-row">
						<td class="cumulative">{bid.cumulativeVolume.toLocaleString()}</td>
						<td class="volume">{bid.volume.toLocaleString()}</td>
						<td class="price">{bid.formattedPrice}</td>
						<td class="volume-bar-container">
							<div
								class="volume-bar bid-bar"
								style:width={`${(bid.volume / totalVisibleVolume()) * 500}%`}
							></div>
						</td>
					</tr>
				{:else}
					<tr><td colspan="4" class="no-data">No bid data</td></tr>
				{/each}
			</tbody>
		</table>
	</div>

	<!-- Asks Column -->
	<div class="l2-column asks-column">
		<table class="l2-table">
			<thead>
				<tr>
					<th class="price">Ask</th>
					<th class="volume">T</th>
					<th class="cumulative">C</th>
				</tr>
			</thead>
			<tbody>
				<!-- Access derived value directly in template -->
				{#each processedAsks() as ask (ask.price)}
					<tr class="l2-row ask-row">
						<td class="price">{ask.formattedPrice}</td>
						<td class="volume">{ask.volume.toLocaleString()}</td>
						<td class="cumulative">{ask.cumulativeVolume.toLocaleString()}</td>
						<td class="volume-bar-container">
							<div
								class="volume-bar ask-bar"
								style:width={`${(ask.volume / totalVisibleVolume()) * 500}%`}
							></div>
						</td>
					</tr>
				{:else}
					<tr><td colspan="4" class="no-data">No ask data</td></tr>
				{/each}
			</tbody>
		</table>
	</div>
</div>

<!-- Styles remain the same -->
<style>
	/* Styles remain the same */
	.l2-container {
		display: flex;
		gap: 5px;
		font-family: 'Courier New', Courier, monospace;
		font-size: 0.9em;
		background-color: #1a1a1a;
		color: #e0e0e0;
		padding: 5px;
		border: 1px solid #444;
		min-height: 300px;
	}
	.l2-column {
		flex: 1;
	}
	.l2-table {
		width: 100%;
		border-collapse: collapse;
		table-layout: fixed;
	}
	th,
	td {
		padding: 1px 4px;
		text-align: right;
		position: relative;
		z-index: 2;
		white-space: nowrap;
	}
	th {
		font-weight: bold;
		color: #aaa;
		border-bottom: 1px solid #444;
		text-transform: uppercase;
		font-size: 0.8em;
	}
	.l2-row {
		position: relative;
		height: 1.2em;
	}
	.l2-row:hover {
		background-color: #333;
	}
	.price {
		width: 38%;
	}
	.volume {
		width: 28%;
	}
	.cumulative {
		width: 28%;
		color: #ccc;
	}
	.volume-bar-container {
		width: 100%;
		padding: 0;
		position: absolute;
		top: 0;
		left: 0;
		height: 100%;
		z-index: 1;
		overflow: hidden;
	}
	.bid-row .price,
	.bid-row .volume {
		color: #4caf50;
	}
	.ask-row .price,
	.ask-row .volume {
		color: #f44336;
	}
	.no-data {
		text-align: center;
		color: #666;
		font-style: italic;
		padding: 10px;
	}
	.volume-bar {
		position: absolute;
		top: 0;
		height: 100%;
		opacity: 0.15;
	}
	.bid-bar {
		background-color: #4caf50;
		right: 0;
		left: auto;
	}
	.ask-bar {
		background-color: #f44336;
		left: 0;
		right: auto;
	}
	.bids-column th.price,
	.bids-column td.price {
		text-align: right;
	}
	.asks-column th.price,
	.asks-column td.price {
		text-align: left;
	}
	.bids-column th.cumulative,
	.bids-column td.cumulative {
		text-align: left;
	}
	.asks-column th.cumulative,
	.asks-column td.cumulative {
		text-align: right;
	}
	.bids-column th.volume,
	.bids-column td.volume {
		text-align: right;
	}
	.asks-column th.volume,
	.asks-column td.volume {
		text-align: right;
	}
</style>
