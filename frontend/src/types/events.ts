export type WebSocketEventType = 
  | 'HEALTH_UPDATE'
  | 'ANOMALY_DETECTED'
  | 'PREDICTION_READY'
  | 'GRAPH_UPDATE'
  | 'SYSTEM_STATUS';

export interface WebSocketMessage<T = any> {
  v: number;
  type: WebSocketEventType;
  ts: number;
  payload: T;
}

export interface GraphNode {
  id: string;
  group: number;
  fx?: number;
  fy?: number;
}

export interface GraphLink {
  source: string;
  target: string;
  value: number;
}

export interface GraphState {
  nodes: GraphNode[];
  links: GraphLink[];
}

export interface AnomalyEvent {
  service: string;
  metric: string;
  timestamp: string;
  severity: 'INFO' | 'WARNING' | 'CRITICAL';
  current_value: number;
  z_score?: number;
  cusum_alert?: boolean;
}
