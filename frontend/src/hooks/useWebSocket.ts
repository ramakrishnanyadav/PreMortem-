import { useEffect, useRef } from 'react';
import { usePreMortemStore } from '../store/usePreMortemStore';
import { WebSocketMessage } from '../types/events';

export const useWebSocket = (url: string) => {
  const ws = useRef<WebSocket | null>(null);
  const { setConnected, updateService, updateGraphState, addAnomaly, setActivePrediction, incrementIncidentCount } = usePreMortemStore();

  useEffect(() => {
    let reconnectTimeout: ReturnType<typeof setTimeout>;
    let backoff = 1000;
    const maxBackoff = 30000;

    const connect = () => {
      ws.current = new WebSocket(url);

      ws.current.onopen = () => {
        setConnected(true);
        backoff = 1000; // reset backoff
      };

      ws.current.onmessage = (event) => {
        try {
          const msg: WebSocketMessage = JSON.parse(event.data);
          
          if (msg.type === 'HEALTH_UPDATE') {
            Object.entries(msg.payload).forEach(([serviceId, value]) => {
              updateService(serviceId, { primaryMetric: value as number, healthScore: 100 });
            });
          } else if (msg.type === 'GRAPH_UPDATE') {
            updateGraphState(msg.payload);
            // Derive health scores from graph nodes if present
            msg.payload.nodes?.forEach((node: any) => {
              if (node.health_score !== undefined) {
                updateService(node.id, { healthScore: node.health_score });
              }
            });
          } else if (msg.type === 'PREDICTION_READY') {
            setActivePrediction(msg.payload.prediction);
          } else if (msg.type === 'ANOMALY_DETECTED') {
            addAnomaly(msg.payload);
            if (msg.payload.severity === 'CRITICAL') {
              incrementIncidentCount();
            }
          }
        } catch (err) {
          console.error("Failed to parse WS message", err);
        }
      };

      ws.current.onclose = () => {
        setConnected(false);
        // Exponential backoff reconnect
        reconnectTimeout = setTimeout(connect, backoff);
        backoff = Math.min(backoff * 2, maxBackoff);
      };
    };

    connect();

    return () => {
      clearTimeout(reconnectTimeout);
      if (ws.current) {
        ws.current.close();
      }
    };
  }, [url, setConnected, updateService, updateGraphState, addAnomaly, setActivePrediction, incrementIncidentCount]);

  return ws.current;
};
