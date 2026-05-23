import React, { useState, useEffect, useRef } from 'react';
import { THEME } from '../styles/theme';

type ReplayState = 'idle' | 'selecting' | 'playing' | 'paused' | 'complete';

interface Incident {
  id: string;
  name: string;
  date: string;
  resolution_minutes: number;
  root_cause: string;
  precursor_signals: {
    t_minus_minutes: number;
    description: string;
    service: string;
  }[];
  premortem_detection_offset_minutes: number;
}

export const IncidentReplay: React.FC = () => {
  const [state, setState] = useState<ReplayState>('idle');
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [selectedIncident, setSelectedIncident] = useState<Incident | null>(null);
  const [currentMinute, setCurrentMinute] = useState<number>(0);
  const [speed, setSpeed] = useState<number>(1);
  const [events, setEvents] = useState<{time: number, msg: string, type: 'normal'|'premortem'|'impact'}[]>([]);
  
  const animationRef = useRef<number | null>(null);
  const lastTimeRef = useRef<number>(0);
  const lastProcessedMinuteRef = useRef<number | null>(null);
  const eventsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'r' || e.key === 'R') {
        if (state === 'idle') {
          fetchIncidents();
          setState('selecting');
        }
      }
      if (state !== 'idle' && state !== 'selecting') {
        if (e.key === ' ') {
          setState(s => s === 'playing' ? 'paused' : 'playing');
        } else if (e.key === 'Escape') {
          closeReplay();
        } else if (e.key === '1') setSpeed(1);
        else if (e.key === '5') setSpeed(5);
        else if (e.key === '3') setSpeed(30);
        else if (e.key === '6') setSpeed(60);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [state]);

  const fetchIncidents = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/incidents/history');
      const data = await res.json();
      setIncidents(data.incidents);
    } catch (e) {
      console.error(e);
    }
  };

  const startReplay = (incident: Incident) => {
    setSelectedIncident(incident);
    const startMin = -Math.max(...incident.precursor_signals.map(s => s.t_minus_minutes), incident.premortem_detection_offset_minutes);
    setCurrentMinute(startMin);
    lastProcessedMinuteRef.current = startMin - 1;
    setEvents([]);
    setState('playing');
  };

  const closeReplay = () => {
    if (animationRef.current) cancelAnimationFrame(animationRef.current);
    setState('idle');
    setSelectedIncident(null);
  };

  useEffect(() => {
    const tick = (time: number) => {
      if (!lastTimeRef.current) lastTimeRef.current = time;
      const deltaTime = time - lastTimeRef.current;
      lastTimeRef.current = time;

      if (state === 'playing') {
        const minutesToAdvance = (deltaTime * speed) / 1000;
        setCurrentMinute(prev => {
          const next = prev + minutesToAdvance;
          if (next > 5) {
            setState('complete');
            return 5;
          }
          return next;
        });
      }
      animationRef.current = requestAnimationFrame(tick);
    };

    if (state === 'playing') {
      lastTimeRef.current = performance.now();
      animationRef.current = requestAnimationFrame(tick);
    } else {
      if (animationRef.current) cancelAnimationFrame(animationRef.current);
    }

    return () => {
      if (animationRef.current) cancelAnimationFrame(animationRef.current);
    };
  }, [state, speed]);

  useEffect(() => {
    if (!selectedIncident || state === 'idle' || state === 'selecting') return;
    
    const currentInt = Math.floor(currentMinute);
    if (lastProcessedMinuteRef.current === currentInt) return;
    
    const newEvents: typeof events = [];
    const startProcess = lastProcessedMinuteRef.current !== null ? lastProcessedMinuteRef.current + 1 : currentInt;

    for (let m = startProcess; m <= currentInt; m++) {
      const signals = selectedIncident.precursor_signals.filter(s => s.t_minus_minutes === -m);
      signals.forEach(s => {
        newEvents.push({ time: m, msg: `[${s.service}] ${s.description}`, type: 'normal' });
      });

      if (m === -selectedIncident.premortem_detection_offset_minutes) {
        newEvents.push({ time: m, msg: `PREMORTEM ALERT: Root cause identified → ${selectedIncident.root_cause.substring(0, 50)}...`, type: 'premortem' });
      }

      if (m === 0) {
        newEvents.push({ time: m, msg: `USER IMPACT: Users are now experiencing degradation.`, type: 'impact' });
      }
    }

    if (newEvents.length > 0) {
      setEvents(prev => [...prev, ...newEvents]);
    }
    lastProcessedMinuteRef.current = currentInt;
  }, [currentMinute, selectedIncident, state]);

  useEffect(() => {
    eventsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [events]);

  if (state === 'idle') return null;

  const minTime = selectedIncident ? -Math.max(...selectedIncident.precursor_signals.map(s => s.t_minus_minutes), selectedIncident.premortem_detection_offset_minutes) : -60;
  const maxTime = 5;
  const totalDuration = maxTime - minTime;
  const progressPercent = Math.max(0, Math.min(100, ((currentMinute - minTime) / totalDuration) * 100));

  const alertOffset = selectedIncident ? selectedIncident.premortem_detection_offset_minutes : 0;
  const alertPercent = selectedIncident ? Math.max(0, Math.min(100, ((-alertOffset - minTime) / totalDuration) * 100)) : 0;
  const impactPercent = selectedIncident ? Math.max(0, Math.min(100, ((0 - minTime) / totalDuration) * 100)) : 0;

  return (
    <div className="fixed inset-0 bg-[#05081099] backdrop-blur-[2px] z-50 flex items-center justify-center p-8">
      <div className="bg-bgPanel border border-borderActive rounded-lg w-full max-w-[720px] max-h-[80vh] flex flex-col shadow-2xl">
        
        {/* Header */}
        <div className="px-6 py-4 border-b border-borderTheme flex justify-between items-center">
          <span className="metric-value text-[14px] text-predicting">INCIDENT REPLAY MODE</span>
          <div className="flex items-center gap-4">
            <span className="label-text text-[10px] text-textLabel uppercase tracking-[1.5px]">ESC TO CLOSE</span>
            <button onClick={closeReplay} className="text-textMuted hover:text-white">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="18" y1="6" x2="6" y2="18"></line>
                <line x1="6" y1="6" x2="18" y2="18"></line>
              </svg>
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-hidden flex flex-col p-6">
          {state === 'selecting' ? (
            <div className="flex flex-col gap-3 overflow-y-auto pr-2">
              <span className="label-text text-xs text-textSecondary uppercase tracking-wider mb-2">Select Historical Incident</span>
              {incidents.map(inc => (
                <div 
                  key={inc.id} 
                  onClick={() => startReplay(inc)}
                  className="bg-bgHover border border-borderTheme p-4 cursor-pointer hover:border-predicting transition-colors"
                >
                  <div className="flex justify-between items-center">
                    <span className="metric-value text-[13px] text-white">{inc.name}</span>
                    <span className="metric-value text-[11px] text-predicting">PLAY ⏵</span>
                  </div>
                  <div className="mt-2 flex gap-4 label-text text-[11px] text-textLabel">
                    <span>DATE: {inc.date}</span>
                    <span>EARLY WARNING: {inc.premortem_detection_offset_minutes}m</span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex flex-col h-full gap-6">
              
              {/* TIMELINE SCRUBBER */}
              <div className="relative pt-6 pb-8">
                <div className="h-1 w-full bg-bgDark rounded-full relative">
                  {/* Progress Fill */}
                  <div 
                    className="absolute top-0 left-0 bottom-0 bg-predicting rounded-full transition-all ease-linear"
                    style={{ width: `${progressPercent}%`, transitionDuration: state === 'playing' ? `${1000/speed}ms` : '0ms' }}
                  ></div>
                  
                  {/* Thumb */}
                  <div 
                    className="absolute top-1/2 -translate-y-1/2 w-3 h-3 bg-predicting rounded-full transition-all ease-linear shadow-[0_0_8px_#6366f1]"
                    style={{ left: `${progressPercent}%`, transitionDuration: state === 'playing' ? `${1000/speed}ms` : '0ms' }}
                  >
                    <div className="absolute -top-6 left-1/2 -translate-x-1/2 metric-value text-[10px] text-white whitespace-nowrap">
                      T{currentMinute <= 0 ? currentMinute : `+${currentMinute}`}
                    </div>
                  </div>

                  {/* PreMortem Alert Marker */}
                  <div 
                    className="absolute top-1/2 -translate-y-1/2 w-1 h-3 bg-predicting z-10"
                    style={{ left: `${alertPercent}%` }}
                  >
                    <div className="absolute top-4 left-1/2 -translate-x-1/2 metric-value text-[9px] text-predicting whitespace-nowrap">PREMORTEM ALERT</div>
                  </div>

                  {/* User Impact Marker */}
                  <div 
                    className="absolute top-1/2 -translate-y-1/2 w-1 h-3 bg-critical z-10"
                    style={{ left: `${impactPercent}%` }}
                  >
                    <div className="absolute top-4 left-1/2 -translate-x-1/2 metric-value text-[9px] text-critical whitespace-nowrap">USER IMPACT</div>
                  </div>

                  {/* Early Warning Gap Label */}
                  {currentMinute >= -alertOffset && (
                    <div 
                      className="absolute top-10 flex flex-col items-center justify-center animate-pulse-fast"
                      style={{ left: `${(alertPercent + impactPercent) / 2}%`, transform: 'translateX(-50%)' }}
                    >
                      <span className="metric-value text-[11px] text-healthy whitespace-nowrap bg-healthy/10 px-2 py-0.5 rounded border border-healthy/30">
                        {alertOffset} MIN EARLY WARNING
                      </span>
                    </div>
                  )}
                </div>
              </div>

              {/* LIVE COMMENTARY BOX */}
              <div className="flex-1 bg-bgDark border-l-4 border-predicting p-4 overflow-y-auto flex flex-col gap-2 relative">
                <span className="absolute top-2 right-4 label-text text-[9px] text-textLabel uppercase tracking-widest">LIVE COMMENTARY</span>
                <div className="mt-4 flex flex-col gap-3">
                  {events.map((e, i) => (
                    <div key={i} className="flex gap-4">
                      <span className="metric-value text-[11px] text-textMuted shrink-0 w-12">
                        T{e.time <= 0 ? e.time : `+${e.time}`}
                      </span>
                      <span className={`metric-value text-[12px] leading-relaxed ${e.type === 'premortem' ? 'text-predicting font-bold' : e.type === 'impact' ? 'text-critical font-bold' : 'text-textSecondary'}`}>
                        {e.msg}
                      </span>
                    </div>
                  ))}
                  <div ref={eventsEndRef} />
                </div>
              </div>

              {/* CONTROLS */}
              <div className="flex justify-between items-center bg-bgDark p-2 border border-borderTheme">
                <button 
                  onClick={() => setState(s => s === 'playing' ? 'paused' : 'playing')}
                  className="metric-value text-[11px] bg-bgHover text-white px-4 py-1.5 hover:bg-borderTheme transition-colors w-24"
                >
                  {state === 'playing' ? 'PAUSE' : state === 'complete' ? 'RESET' : 'PLAY'}
                </button>

                <div className="flex gap-1 bg-bgHover p-1">
                  <span className="label-text text-[9px] text-textLabel px-2 flex items-center">SPEED</span>
                  {[1, 5, 30].map(s => (
                    <button 
                      key={s} 
                      onClick={() => setSpeed(s)}
                      className={`metric-value text-[10px] px-3 py-1 ${speed === s ? 'bg-borderTheme text-white' : 'text-textMuted hover:text-white'}`}
                    >
                      {s}x
                    </button>
                  ))}
                </div>
              </div>

            </div>
          )}
        </div>
      </div>
    </div>
  );
};
