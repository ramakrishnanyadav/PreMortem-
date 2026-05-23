import React, { useEffect, useState } from 'react';
import { usePreMortemStore } from '../store/usePreMortemStore';
import { ShieldAlert, TerminalSquare, AlertTriangle } from 'lucide-react';

export const PredictionCard: React.FC = () => {
  const [prediction, setPrediction] = useState<any>(null);

  // In a real app we'd have a prediction store updated via WS
  // For the hackathon, we simulate picking it up if it arrives
  useEffect(() => {
    // Listen for custom event or Zustand state update
    const handlePrediction = (e: any) => setPrediction(e.detail);
    window.addEventListener('prediction_ready', handlePrediction);
    return () => window.removeEventListener('prediction_ready', handlePrediction);
  }, []);

  if (!prediction) {
    return (
      <div className="glass-panel p-4 h-full flex flex-col items-center justify-center text-gray-500">
        <ShieldAlert className="w-12 h-12 mb-2 opacity-20" />
        <p>AI Reasoning Engine Standby</p>
        <p className="text-xs mt-1">Monitoring baseline signals...</p>
      </div>
    );
  }

  const { confidence_score, severity, time_to_impact_minutes, root_cause_hypotheses, remediation_steps } = prediction;
  const mainHypothesis = root_cause_hypotheses[0];

  return (
    <div className="glass-panel p-4 h-full flex flex-col border-l-4 border-danger">
      <div className="flex justify-between items-start mb-4">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center gap-2">
            <AlertTriangle className="text-danger" /> 
            Predicted Incident
          </h2>
          <p className="text-sm text-gray-400 mt-1">Impact expected in {time_to_impact_minutes} minutes</p>
        </div>
        <div className="bg-danger/20 text-danger px-3 py-1 rounded-full text-sm font-bold border border-danger/50">
          {severity}
        </div>
      </div>

      <div className="mb-4">
        <h3 className="text-sm text-gray-400 mb-1">Root Cause Hypothesis (Confidence: {confidence_score}%)</h3>
        <p className="text-white bg-surface p-3 rounded-lg border border-white/5">{mainHypothesis.hypothesis}</p>
      </div>

      <div className="flex-1">
        <h3 className="text-sm text-gray-400 mb-1">Recommended Remediation</h3>
        <div className="space-y-2">
          {remediation_steps.slice(0, 2).map((step: any, i: number) => (
            <div key={i} className="bg-surface p-3 rounded-lg border border-white/5">
              <p className="text-sm text-white mb-2"><span className="text-primary font-bold">{i + 1}.</span> {step.action}</p>
              {step.command && (
                <div className="flex items-center gap-2 bg-black/50 p-2 rounded text-xs font-mono text-green-400 border border-green-900/30">
                  <TerminalSquare className="w-4 h-4" />
                  {step.command}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
