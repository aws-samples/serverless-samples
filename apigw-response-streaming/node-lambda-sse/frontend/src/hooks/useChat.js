import { useState, useCallback, useRef } from 'react';
import { streamChat } from '../lib/sseClient.js';

const API_URL = import.meta.env.VITE_API_URL;

/**
 * React hook that manages conversation state and orchestrates streaming.
 */
export function useChat() {
  const [messages, setMessages] = useState([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState(null);
  const [ttfb, setTtfb] = useState(null);
  const [ttfc, setTtfc] = useState(null);
  const [sseEvents, setSseEvents] = useState([]);
  const [ttfbMap, setTtfbMap] = useState({});
  const isStreamingRef = useRef(false);
  const lastFailedTextRef = useRef(null);
  const streamStartRef = useRef(null);
  const assistantIndexRef = useRef(null);

  const doSend = useCallback((text, existingMessages) => {
    if (isStreamingRef.current) return;

    setError(null);
    setTtfb(null);
    setTtfc(null);
    setSseEvents([]);
    lastFailedTextRef.current = text;

    const userMessage = { role: 'user', content: text };
    const assistantMessage = { role: 'assistant', content: '' };
    const messagesForApi = [...existingMessages, userMessage];

    setMessages([...existingMessages, userMessage, assistantMessage]);

    const assistantIdx = existingMessages.length + 1;
    assistantIndexRef.current = assistantIdx;

    isStreamingRef.current = true;
    setIsStreaming(true);
    streamStartRef.current = performance.now();

    streamChat(API_URL, messagesForApi, {
      onRawEvent: (raw) => {
        setSseEvents((prev) => [...prev, { time: Date.now(), data: raw }]);
      },
      onFirstChunk: () => {
        const elapsed = performance.now() - streamStartRef.current;
        const ms = Math.round(elapsed);
        setTtfb(ms);
        setTtfbMap((prev) => ({ ...prev, [assistantIndexRef.current]: ms }));
      },
      onChunk: (chunk) => {
        setMessages((current) => {
          const next = [...current];
          const last = next[next.length - 1];
          next[next.length - 1] = { ...last, content: last.content + chunk };
          return next;
        });
      },
      onDone: () => {
        const elapsed = performance.now() - streamStartRef.current;
        setTtfc(Math.round(elapsed));
        lastFailedTextRef.current = null;
        isStreamingRef.current = false;
        setIsStreaming(false);
      },
      onError: (errorMessage) => {
        setError(errorMessage);
        // Remove the empty assistant placeholder on error
        setMessages((current) => {
          const last = current[current.length - 1];
          if (last?.role === 'assistant' && !last.content) {
            return current.slice(0, -1);
          }
          return current;
        });
        isStreamingRef.current = false;
        setIsStreaming(false);
      },
    });
  }, []);

  const sendMessage = useCallback((text) => {
    doSend(text, messages);
  }, [messages, doSend]);

  const retry = useCallback(() => {
    const failedText = lastFailedTextRef.current;
    if (!failedText || isStreamingRef.current) return;
    // Remove the failed user message before resending
    const withoutLast = messages.filter((_, i) => {
      // Remove the last user message that matches the failed text
      if (i === messages.length - 1 && messages[i].role === 'user' && messages[i].content === failedText) {
        return false;
      }
      return true;
    });
    doSend(failedText, withoutLast);
  }, [messages, doSend]);

  const clearMessages = useCallback(() => {
    if (isStreamingRef.current) return;
    setMessages([]);
    setError(null);
    setTtfb(null);
    setTtfc(null);
    setSseEvents([]);
    setTtfbMap({});
    lastFailedTextRef.current = null;
  }, []);

  return { messages, isStreaming, error, ttfb, ttfc, ttfbMap, sseEvents, sendMessage, clearMessages, retry };
}
