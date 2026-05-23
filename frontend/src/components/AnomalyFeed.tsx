import React, { useEffect, useRef } from 'react';
import { usePreMortemStore } from '../store/usePreMortemStore';
import { THEME } from '../styles/theme';

export const AnomalyFeed: React.FC = () => {
  const { anomalies } = usePreMortemStore();
  const listRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to top when new anomaly arrives (since new ones are at index 0)
  // Actually, wait, if new ones are pushed to top, scroll to top is good.
  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = 0;
    }
  }, [anomalies.length]);

  return (
    <div className="bg-bgDark flex-1 flex flex-col overflow-hidden">
      {/* Header */}
      <div className="flex justify-between items-center px-4 py-3 border-b border-bgPanel shrink-0">
        <span className="label-text text-[10px] text-textLabel uppercase tracking-[1.5px]">
          ANOMALY EVENT STREAM
        </span>
        <div className="bg-bgPanel px-2 py-0.5 rounded">
          <span className="metric-value text-[11px] text-textLabel">
            #{anomalies.length} events
          </span>
        </div>
      </div>

      {/* List */}
      <div 
        ref={listRef} 
        className="flex-1 overflow-y-auto overflow-x-hidden"
      >
        {anomalies.length === 0 ? (
          <div className="h-full flex items-center justify-center text-textMuted text-xs font-mono">
            Waiting for telemetry data...
          </div>
        ) : (
          anomalies.map((anomaly, idx) => {
            const isCrit = anomaly.severity === 'CRITICAL';
            const isWarn = anomaly.severity === 'WARNING';
            
            const color = isCrit ? THEME.colors.critical : isWarn ? THEME.colors.warning : THEME.colors.healthy;
            const bgClass = isCrit ? 'bg-critical' : isWarn ? 'bg-warning' : 'bg-healthy';
            const textClass = isCrit ? 'text-critical' : isWarn ? 'text-warning' : 'text-healthy';
            
            // Format timestamp "HH:MM:SS.MMM"
            const date = new Date(anomaly.timestamp);
            const ts = `${String(date.getUTCHours()).padStart(2, '0')}:${String(date.getUTCMinutes()).padStart(2, '0')}:${String(date.getUTCSeconds()).padStart(2, '0')}.${String(date.getUTCMilliseconds()).padStart(3, '0')}`;

            return (
              <div 
                key={`${anomaly.timestamp}-${idx}`} 
                className="relative h-[56px] border-b border-bgPanel px-4 py-2.5 flex flex-col justify-between animate-in slide-in-from-right-4 fade-in duration-300"
              >
                {/* Left Strip */}
                <div className={`absolute left-0 top-0 bottom-0 w-[3px] ${bgClass}`}></div>
                
                {/* Row 1 */}
                <div className="flex justify-between items-center pl-1">
                  <div className="flex items-center gap-2">
                    <span className={`metric-value text-[9px] uppercase px-1.5 py-[1px] rounded-[3px] font-bold ${bgClass}/20 ${textClass}`}>
                      {isCrit ? 'CRIT' : isWarn ? 'WARN' : 'INFO'}
                    </span>
                    <span className="metric-value text-xs text-textPrimary font-medium">
                      {anomaly.service}
                    </span>
                  </div>
                  <span className="metric-value text-[11px] text-textLabel">
                    {ts}
                  </span>
                </div>

                {/* Row 2 */}
                <div className="flex justify-between items-center pl-1 mt-1">
                  <span className="label-text text-xs text-textMuted">
                    {anomaly.metric}: {anomaly.current_value.toFixed(1)}ms → <span className={`event-sigma ${textClass}`}>{anomaly.z_score?.toFixed(1) || '0.0'}σ</span>
                  </span>
                  {anomaly.cusum_alert && (
                    <span className="label-text text-[9px] uppercase tracking-wider bg-warning/15 border border-warning/30 text-warning px-1.5 py-[1px] rounded">
                      DRIFT
                    </span>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
