import { useRef, useEffect, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'motion/react';
import Markdown from 'react-markdown';
import { useChat } from './hooks/useChat.js';
import './App.css';

function useTheme() {
  const [theme, setTheme] = useState(() => {
    if (typeof window === 'undefined') return 'light';
    return localStorage.getItem('theme') || 'light';
  });

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('theme', theme);
  }, [theme]);

  const toggle = useCallback(() => {
    setTheme((t) => (t === 'dark' ? 'light' : 'dark'));
  }, []);

  return { theme, toggle };
}

function ShimmerSkeleton() {
  return (
    <div className="shimmer-skeleton" aria-label="Loading response">
      <div className="shimmer-line" />
      <div className="shimmer-line" />
      <div className="shimmer-line" />
    </div>
  );
}

function SseLogPanel({ events, isOpen, ttfb, ttfc }) {
  const logEndRef = useRef(null);
  const [expanded, setExpanded] = useState(false);
  const startTime = events.length > 0 ? events[0].time : null;

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [events]);

  if (!isOpen) return null;

  return (
    <div className={`sse-log-panel${expanded ? ' sse-log-panel--expanded' : ''}`}>
      <div className="sse-log-header">
        <span className="sse-log-count">{events.length} event{events.length !== 1 ? 's' : ''}</span>
        <div className="sse-log-stats">
          {ttfb != null && events.length > 0 && (
            <span className="sse-log-badge sse-log-badge--ttfb" data-tooltip="Time to first byte">TTFB {ttfb} ms</span>
          )}
          {ttfc != null && (
            <span className="sse-log-badge sse-log-badge--ttfc" data-tooltip="Time to full completion">TTFC {(ttfc / 1000).toFixed(2)} s</span>
          )}
          <button
            className="sse-log-expand"
            onClick={() => setExpanded((v) => !v)}
            aria-label={expanded ? 'Collapse SSE log' : 'Expand SSE log'}
            data-tooltip={expanded ? 'Collapse' : 'Expand'}
          >
            {expanded ? '↓' : '↑'}
          </button>
        </div>
      </div>
      <div className="sse-log-body">
        {events.length === 0 ? (
          <div className="sse-log-empty">Send a message to see raw SSE events</div>
        ) : (
          events.map((evt, i) => (
            <div key={i} className={`sse-log-entry${i % 2 === 0 ? '' : ' sse-log-entry--alt'}`}>
              <span className="sse-log-ts">
                +{startTime ? ((evt.time - startTime) / 1000).toFixed(3) : '0.000'}s
              </span>
              <span className="sse-log-data">{evt.data}</span>
            </div>
          ))
        )}
        <div ref={logEndRef} />
      </div>
    </div>
  );
}

export default function App() {
  const { messages, isStreaming, error, ttfb, ttfc, ttfbMap, sseEvents, sendMessage, clearMessages, retry } = useChat();
  const [input, setInput] = useState('');
  const [showSseLog, setShowSseLog] = useState(false);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const { theme, toggle: toggleTheme } = useTheme();
  const prevCountRef = useRef(0);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const isFirstBatch = prevCountRef.current === 0 && messages.length > 0;
  useEffect(() => {
    prevCountRef.current = messages.length;
  }, [messages.length]);

  // Refocus input when streaming finishes so the cursor stays in the text field
  useEffect(() => {
    if (!isStreaming) {
      inputRef.current?.focus();
    }
  }, [isStreaming]);

  const handleSubmit = (e) => {
    e.preventDefault();
    const text = input.trim();
    if (!text) return;
    sendMessage(text);
    setInput('');
  };

  // Detect if the last assistant message is still empty (waiting for first chunk)
  const lastMsg = messages[messages.length - 1];
  const isWaitingForFirstChunk = isStreaming && lastMsg?.role === 'assistant' && !lastMsg.content;

  const quickPrompts = [
    'Explain Lambda response streaming in 3 sentences',
    'What is Server-Sent Events (SSE)?',
    'Compare REST vs WebSocket vs SSE',
  ];

  return (
    <div className="shell">
      <header className="header">
        <div className="header-brand">
          <span className="header-mark">λ</span>
          <h1 className="title">Lambda SSE</h1>
        </div>
        <div className="header-actions">
          {messages.length > 0 && (
            <motion.button
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              onClick={clearMessages}
              disabled={isStreaming}
              className="btn-ghost"
              aria-label="Clear conversation"
            >
              Clear
            </motion.button>
          )}
          <button
            onClick={() => setShowSseLog((v) => !v)}
            className={`btn-ghost sse-log-toggle${showSseLog ? ' sse-log-toggle--active' : ''}`}
            aria-label="Toggle SSE event log"
            title="Toggle raw SSE event log"
          >
            SSE Log
          </button>
          <button
            onClick={toggleTheme}
            className="btn-ghost theme-btn"
            aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}
            data-tooltip={theme === 'dark' ? 'Light theme' : 'Dark theme'}
            data-tooltip-pos="bottom"
          >
            {theme === 'dark' ? '☀' : '☽'}
          </button>
        </div>
      </header>

      <div className="message-area" role="log" aria-live="polite">
        <AnimatePresence mode="popLayout">
          {messages.length === 0 ? (
            <motion.div
              key="empty"
              className="empty-state"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0, transition: { duration: 0.15 } }}
            >
              <div className="empty-glyph" aria-hidden="true">λ</div>
              <p className="empty-text">What would you like to know?</p>
              <div className="quick-prompts">
                {quickPrompts.map((prompt, i) => (
                  <motion.button
                    key={prompt}
                    className="quick-prompt-btn"
                    onClick={() => sendMessage(prompt)}
                    disabled={isStreaming}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.1 + i * 0.08, duration: 0.3 }}
                  >
                    {prompt}
                  </motion.button>
                ))}
              </div>
            </motion.div>
          ) : (
            <motion.div
              key="conversation"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ duration: 0.2, delay: 0.1 }}
              style={{ display: 'contents' }}
            >
              {messages.map((msg, i) => {
                // Skip rendering the empty assistant placeholder — show shimmer instead
                if (msg.role === 'assistant' && !msg.content && isWaitingForFirstChunk && i === messages.length - 1) {
                  return null;
                }

                const msgTtfb = msg.role === 'assistant' ? ttfbMap[i] : null;

                return (
                  <motion.div
                    key={i}
                    className={`message ${
                      msg.role === 'user' ? 'message--user' : 'message--assistant'
                    }`}
                    initial={isFirstBatch ? { opacity: 0 } : { opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.2 }}
                  >
                    <span className="message-role">
                      {msg.role === 'user' ? 'You' : 'Assistant'}
                    </span>
                    {msg.role === 'assistant' ? (
                      <div className="message-markdown">
                        <Markdown>{msg.content || '\u00A0'}</Markdown>
                      </div>
                    ) : (
                      <p className="message-content">{msg.content || '\u00A0'}</p>
                    )}
                    {msgTtfb != null && (
                      <span className="ttfb-badge" data-tooltip="Time to first byte">TTFB {msgTtfb} ms</span>
                    )}
                  </motion.div>
                );
              })}

              {isWaitingForFirstChunk && (
                <motion.div
                  initial={{ opacity: 0, y: 4 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.2 }}
                >
                  <ShimmerSkeleton />
                </motion.div>
              )}

              {isStreaming && !isWaitingForFirstChunk && (
                <div className="streaming-indicator">
                  <div className="streaming-dots">
                    <span className="streaming-dot" />
                    <span className="streaming-dot" />
                    <span className="streaming-dot" />
                  </div>
                  Streaming…
                </div>
              )}
              <div ref={messagesEndRef} />
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {error && (
        <div className="error-bar" role="alert">
          <span>Error: {error}</span>
          <button onClick={retry} className="retry-btn" disabled={isStreaming}>
            Retry
          </button>
        </div>
      )}

      <form onSubmit={handleSubmit} className="input-bar">
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask anything…"
          disabled={isStreaming}
          className="input-field"
          aria-label="Chat message input"
        />
        <button
          type="submit"
          disabled={isStreaming || !input.trim()}
          className="send-btn"
        >
          Send
        </button>
      </form>

      <SseLogPanel events={sseEvents} isOpen={showSseLog} ttfb={ttfb} ttfc={ttfc} />

      <div className="footer" aria-hidden="true">
        <span>SSE</span>
        <span className="footer-sep">·</span>
        <span>Bedrock</span>
        <span className="footer-sep">·</span>
        <span>Nova Lite</span>
      </div>
    </div>
  );
}
