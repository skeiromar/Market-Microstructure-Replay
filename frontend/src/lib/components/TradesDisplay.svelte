<!-- /Users/omarm/My_Projects/trading/L2Replay/frontend/src/lib/components/TradesDisplay.svelte -->
<script lang="ts">
    // Import the trades store and relevant types
    import { trades } from '$lib/utils/websocketStore';
    import type { Trade } from '$lib/types';
    console.log($trades)
    // Helper function to format timestamp (could be moved to a shared utils file later)
    function formatTimestamp(ns: number | null): string {
        if (ns === null) return '--:--:--.---';
        const date = new Date(ns / 1e6); // Convert ns to ms
        const hours = String(date.getUTCHours()).padStart(2, '0');
        const minutes = String(date.getUTCMinutes()).padStart(2, '0');
        const seconds = String(date.getUTCSeconds()).padStart(2, '0');
        const milliseconds = String(date.getUTCMilliseconds()).padStart(3, '0');
        return `${hours}:${minutes}:${seconds}.${milliseconds}`;
    }

    // Helper function to determine color based on trade side
    function getSideColor(side: string): string {
        switch (side) {
            case 'B': return '#4CAF50'; // Green for Buy aggressor
            case 'A': return '#F44336'; // Red for Sell aggressor
            default: return '#cccccc';  // Grey/White for None or unknown
        }
    }
</script>

<div class="trades-container">
    <h2>Time & Sales</h2>
    <div class="trades-list-wrapper">
        <ul class="trades-list">
            <!-- Use $trades store directly with auto-subscription -->
            {#each $trades as trade (trade.timestamp + '-' + trade.sequence)}
                <li class="trade-item" style="color: {getSideColor(trade.side)};">
                    <span class="trade-time">{formatTimestamp(trade.timestamp)}</span>
                    <span class="trade-price">{trade.price}</span>
                    <span class="trade-size">{trade.size.toLocaleString()}</span>
                    <!-- Optional: Display side explicitly if needed -->
                    <!-- <span class="trade-side">{trade.side}</span> -->
                </li>
            {:else}
                <li class="no-trades">(Waiting for trades...)</li>
            {/each}
        </ul>
    </div>
</div>

<style>
    .trades-container {
        border: 1px solid #444;
        background-color: #1a1a1a;
        padding: 0.5rem 1rem 1rem 1rem; /* Less top padding */
        color: #e0e0e0;
        display: flex;
        flex-direction: column;
    }

    h2 {
        margin-top: 0;
        margin-bottom: 0.5rem;
        text-align: center;
        color: #aaa;
        font-size: 1.1em;
    }

    .trades-list-wrapper {
        max-height: 250px; /* Or desired height */
        overflow-y: auto; /* Enable vertical scrolling */
        border: 1px solid #333;
        background-color: #111; /* Slightly darker background for list */
    }

    /* Custom scrollbar styling (optional, WebKit browsers) */
    .trades-list-wrapper::-webkit-scrollbar {
        width: 8px;
    }
    .trades-list-wrapper::-webkit-scrollbar-track {
        background: #2a2a2a;
    }
    .trades-list-wrapper::-webkit-scrollbar-thumb {
        background-color: #555;
        border-radius: 4px;
        border: 2px solid #2a2a2a;
    }

    .trades-list {
        list-style: none;
        padding: 0.25rem 0.5rem;
        margin: 0;
        font-family: 'Courier New', Courier, monospace;
        font-size: 0.9em;
    }

    .trade-item {
        display: flex;
        justify-content: space-between;
        padding: 1px 0; /* Minimal vertical padding */
        border-bottom: 1px dotted #2a2a2a; /* Subtle separator */
    }
    .trade-item:last-child {
        border-bottom: none;
    }

    .trade-time {
        width: 110px; /* Fixed width for time */
        color: #ccc; /* Slightly dimmer color for time */
    }

    .trade-price {
        width: 110px; /* Fixed width for price */
        text-align: right;
        font-weight: bold;
    }

    .trade-size {
        width: 80px; /* Fixed width for size */
        text-align: right;
    }

    /* Optional: Style for explicit side display */
    /* .trade-side { width: 20px; text-align: center; } */

    .no-trades {
        color: #666;
        text-align: center;
        padding: 1rem;
        font-style: italic;
    }
</style>
