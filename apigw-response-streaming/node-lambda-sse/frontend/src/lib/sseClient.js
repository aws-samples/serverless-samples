/**
 * Sends a POST request and consumes the SSE response stream.
 * @param {string} url - The API endpoint URL
 * @param {Array} messages - Conversation history
 * @param {object} callbacks
 * @param {function} callbacks.onChunk - Called with each text chunk as it arrives
 * @param {function} callbacks.onDone - Called when the [DONE] event is received
 * @param {function} callbacks.onError - Called on fetch failure or non-200 status
 * @returns {Promise<void>}
 */
export async function streamChat(url, messages, { onChunk, onDone, onError, onFirstChunk, onRawEvent }) {
  let response;
  try {
    response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages }),
    });
  } catch {
    onError('Network error — please check your connection');
    return;
  }

  if (!response.ok) {
    let errorMessage = `HTTP ${response.status}`;
    try {
      const body = await response.text();
      if (body) {
        errorMessage = body;
      }
    } catch {
      // use default error message
    }
    onError(errorMessage);
    return;
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';
  let firstChunkFired = false;

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // Split on double-newline SSE boundaries
      const parts = buffer.split('\n\n');
      // Last element is either empty or a partial event — keep it in the buffer
      buffer = parts.pop();

      for (const part of parts) {
        const trimmed = part.trim();
        if (!trimmed) continue;

        if (!trimmed.startsWith('data: ')) continue;

        const payload = trimmed.slice(6); // strip "data: " prefix

        if (payload === '[DONE]') {
          onRawEvent?.(`data: [DONE]`);
          onDone();
          return;
        }

        try {
          const parsed = JSON.parse(payload);

          onRawEvent?.(`data: ${payload}`);

          if (parsed.error) {
            onError(parsed.error);
            continue;
          }

          if (typeof parsed.text === 'string') {
            if (!firstChunkFired) {
              firstChunkFired = true;
              onFirstChunk?.();
            }
            onChunk(parsed.text);
          }
        } catch {
          console.warn('Skipping malformed SSE data:', payload);
        }
      }
    }
  } catch {
    onError('Network error — please check your connection');
  }
}
