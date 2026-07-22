'use client';
import { useEffect, useRef, useCallback, useState } from 'react';
import { useStore } from '@/store/useStore';
import { showToast } from '@/components/Toast';

type EventHandler = (event: SSEEvent) => void;

interface SSEEvent {
  type: string;
  payload?: Record<string, any>;
  timestamp?: string;
  id?: string;
}

interface UseRealtimeOptions {
  autoReconnect?: boolean;
  reconnectDelay?: number;
  maxRetries?: number;
  onEvent?: EventHandler;
  eventTypes?: string[]; // Filter — only fire handler for these types
}

/**
 * useRealtime — SSE hook for real-time event streaming from budos API.
 * 
 * Connects to /api/v2/events/stream, auto-reconnects, dispatches events.
 * Use eventTypes filter to only listen for specific event types.
 * 
 * @example
 * const { connected, lastEvent } = useRealtime({
 *   eventTypes: ['tender.new', 'pipeline.changed'],
 *   onEvent: (evt) => { refetch(); }
 * });
 */
export function useRealtime(options: UseRealtimeOptions = {}) {
  const {
    autoReconnect = true,
    reconnectDelay = 3000,
    maxRetries = 10,
    onEvent,
    eventTypes,
  } = options;

  const [connected, setConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState<SSEEvent | null>(null);
  const [retryCount, setRetryCount] = useState(0);
  const eventSourceRef = useRef<EventSource | null>(null);
  const retryTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const onEventRef = useRef(onEvent);
  useEffect(() => { onEventRef.current = onEvent; });

  const connect = useCallback(() => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    try {
      const es = new EventSource('/api/v2/events/stream');
      eventSourceRef.current = es;

      es.onopen = () => {
        setConnected(true);
        setRetryCount(0);
      };

      es.onmessage = (event) => {
        try {
          const data: SSEEvent = JSON.parse(event.data);
          
          // Filter by event types if specified
          if (eventTypes && eventTypes.length > 0 && !eventTypes.includes(data.type)) {
            return;
          }

          setLastEvent(data);
          onEventRef.current?.(data);

          // Global notifications for important events
          if (data.type === 'tender.new') {
            showToast('info', `Nowy przetarg: ${data.payload?.title?.slice(0, 40) || ''}`);
          } else if (data.type === 'alert.deadline') {
            showToast('warning', `Deadline: ${data.payload?.title?.slice(0, 40) || ''}`);
          }
        } catch {
          // Ignore parse errors (heartbeat messages etc)
        }
      };

      es.onerror = () => {
        setConnected(false);
        es.close();
        eventSourceRef.current = null;

        if (autoReconnect && retryCount < maxRetries) {
          retryTimeoutRef.current = setTimeout(() => {
            setRetryCount(prev => prev + 1);
            connect();
          }, reconnectDelay * Math.min(retryCount + 1, 5)); // Exponential backoff capped at 5x
        }
      };
    } catch {
      setConnected(false);
    }
  }, [autoReconnect, reconnectDelay, maxRetries, retryCount, eventTypes]);

  useEffect(() => {
    connect();
    return () => {
      eventSourceRef.current?.close();
      if (retryTimeoutRef.current) clearTimeout(retryTimeoutRef.current);
    };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const disconnect = useCallback(() => {
    eventSourceRef.current?.close();
    eventSourceRef.current = null;
    setConnected(false);
    if (retryTimeoutRef.current) clearTimeout(retryTimeoutRef.current);
  }, []);

  return { connected, lastEvent, retryCount, disconnect, reconnect: connect };
}

/**
 * useNotificationCount — live unread notification count.
 * Polls /api/v2/notifications?unread_only=true every 30s + updates on SSE events.
 */
export function useNotificationCount() {
  const [count, setCount] = useState(0);

  // SSE listener for notification events
  useRealtime({
    eventTypes: ['alert.deadline', 'tender.new', 'agent.done'],
    onEvent: () => setCount(prev => prev + 1),
  });

  // Initial fetch + periodic poll
  useEffect(() => {
    const fetchCount = async () => {
      try {
        const res = await fetch('/api/v2/notifications?unread_only=true&limit=100');
        if (res.ok) {
          const data = await res.json();
          setCount(Array.isArray(data) ? data.length : 0);
        }
      } catch {}
    };

    fetchCount();
    const interval = setInterval(fetchCount, 30_000);
    return () => clearInterval(interval);
  }, []);

  return count;
}
