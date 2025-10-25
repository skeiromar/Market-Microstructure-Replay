import type { BackendCommand } from "$lib/types";

export function formatTimestamp(ns: number | null): string {
    if (ns === null) return '--:--:--.---';
    const date = new Date(ns / 1e6); // Convert ns to ms for Date object
    const hours = String(date.getUTCHours()).padStart(2, '0'); // Use UTC to avoid timezone issues
    const minutes = String(date.getUTCMinutes()).padStart(2, '0');
    const seconds = String(date.getUTCSeconds()).padStart(2, '0');
    const milliseconds = String(date.getUTCMilliseconds()).padStart(3, '0');
    return `${hours}:${minutes}:${seconds}.${milliseconds}`;
}

// Preceding context: formatTimestamp function definition
// export function formatTimestamp(ns: number | null): string { ... }

// ADD the seek function here
/**
 * Parses a datetime-local input string and sends a seek command.
 * @param dateTimeLocalString Value from <input type="datetime-local"> (e.g., "2025-03-25T23:56:52.504")
 * @param sendCommandFn The function to call to send the command to the backend.
 */
export function seekToTimestamp(dateTimeLocalString: string, sendCommandFn: (command: BackendCommand) => void) {
    if (!dateTimeLocalString) {
        alert('Please select a date and time.');
        return;
    }
    try {
        // datetime-local gives time in the user's LOCAL timezone.
        // We need to convert it to a UTC timestamp to match the backend's ts_event.
        // 1. Create a Date object. The browser interprets the string as local time.
        const localDate = new Date(dateTimeLocalString);
        if (isNaN(localDate.getTime())) {
            throw new Error('Invalid date/time value selected');
        }

        // 2. Get the timestamp in milliseconds since epoch (this value is inherently UTC).
        const timestampMs = localDate.getTime();

        // 3. Convert milliseconds to nanoseconds for the backend.
        const target_ns = timestampMs * 1e6;

        if (isNaN(target_ns) || target_ns < 0) {
            throw new Error('Parsed timestamp is invalid');
        }

        console.log(`Sending seek command for local time ${dateTimeLocalString}, UTC ns: ${target_ns}`);
        sendCommandFn({ command: 'seek', timestamp_ns: target_ns });

    } catch (e: any) {
        alert(`Error processing seek time: ${e.message}.`);
        console.error("Timestamp parsing error:", e);
    }
}
