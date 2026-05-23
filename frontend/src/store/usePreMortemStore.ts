import { create } from 'zustand';
import { GraphState, AnomalyEvent } from '../types/events';

interface ServiceState {
  healthScore: number;
  primaryMetric: number;
  sparklineData: number[];
}

interface Prediction {
  confidence_score: number;
  time_to_impact_minutes: number;
  severity: string;
  root_cause_hypotheses: Array<{ hypothesis: string; confidence: number }>;
  blast_radius: { directly_affected: string[]; potentially_affected: string[]; estimated_users_impacted: string };
  remediation_steps: Array<{ priority: number; action: string; estimated_time_minutes: number; prevents: string }>;
}

interface PreMortemState {
  wsConnected: boolean;
  setConnected: (status: boolean) => void;
  
  systemStatus: 'nominal' | 'elevated' | 'critical';
  setSystemStatus: (status: 'nominal' | 'elevated' | 'critical') => void;
  
  services: Map<string, ServiceState>;
  updateService: (id: string, data: Partial<ServiceState>) => void;
  
  anomalies: AnomalyEvent[];
  addAnomaly: (anomaly: AnomalyEvent) => void;
  
  activePrediction: Prediction | null;
  setActivePrediction: (prediction: Prediction | null) => void;
  
  isReplaying: boolean;
  setReplaying: (status: boolean) => void;
  
  replayIncident: any | null;
  setReplayIncident: (incident: any) => void;
  
  incidentCount: number;
  incrementIncidentCount: () => void;
  
  graphState: GraphState;
  updateGraphState: (data: GraphState) => void;
}

export const usePreMortemStore = create<PreMortemState>((set) => ({
  wsConnected: false,
  setConnected: (status) => set({ wsConnected: status }),
  
  systemStatus: 'nominal',
  setSystemStatus: (status) => set({ systemStatus: status }),
  
  services: new Map(),
  updateService: (id, data) => set((state) => {
    const newServices = new Map(state.services);
    const existing = newServices.get(id) || { healthScore: 100, primaryMetric: 0, sparklineData: [] };
    
    // Manage sparkline data (keep last 20)
    let newSparkline = existing.sparklineData;
    if (data.primaryMetric !== undefined) {
      newSparkline = [...existing.sparklineData, data.primaryMetric].slice(-20);
    }
    
    newServices.set(id, { ...existing, ...data, sparklineData: newSparkline });
    return { services: newServices };
  }),
  
  anomalies: [],
  addAnomaly: (anomaly) => set((state) => ({ 
    anomalies: [anomaly, ...state.anomalies],
    systemStatus: anomaly.severity === 'CRITICAL' ? 'critical' : (state.systemStatus === 'critical' ? 'critical' : 'elevated')
  })),
  
  activePrediction: null,
  setActivePrediction: (prediction) => set({ activePrediction: prediction }),
  
  isReplaying: false,
  setReplaying: (status) => set({ isReplaying: status }),
  
  replayIncident: null,
  setReplayIncident: (incident) => set({ replayIncident: incident }),
  
  incidentCount: 0,
  incrementIncidentCount: () => set((state) => ({ incidentCount: state.incidentCount + 1 })),
  
  graphState: { nodes: [], links: [] },
  updateGraphState: (data) => set({ graphState: data }),
}));
