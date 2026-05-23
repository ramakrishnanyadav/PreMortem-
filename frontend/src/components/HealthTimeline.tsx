import React from 'react';
import { usePreMortemStore } from '../store/usePreMortemStore';
import { Activity } from 'lucide-react';

export const HealthTimeline: React.FC = () => {
  const { healthData } = usePreMortemStore();

  const metrics = Object.entries(healthData);

  return (
    <div className="glass-panel p-4 w-full h-full flex flex-col">
      <h2 className="text-xl font-semibold text-gray-200 mb-4 flex items-center gap-2">
        <Activity className="text-primary" /> Live Telemetry
      </h2>
      
      {metrics.length === 0 ? (
        <div className="text-gray-500 text-sm italic">Waiting for telemetry data...</div>
      ) : (
        <div className="grid grid-cols-2 gap-4 overflow-y-auto pr-2">
          {metrics.map(([key, val]) => (
            <div key={key} className="bg-surface p-3 rounded-lg border border-white/5 flex flex-col">
              <span className="text-xs text-gray-400 mb-1 truncate" title={key}>{key}</span>
              <span className="text-lg font-mono text-white">{typeof val === 'number' ? val.toFixed(2) : val}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
