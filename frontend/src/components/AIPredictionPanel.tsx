import React, { useEffect, useState, useRef } from 'react';
import { usePreMortemStore } from '../store/usePreMortemStore';
import { THEME } from '../styles/theme';

const ConfidenceArc: React.FC<{ score: number }> = ({ score }) => {
  const [displayScore, setDisplayScore] = useState(0);
  const arcRef = useRef<SVGPathElement>(null);

  useEffect(() => {
    let startTimestamp: number | null = null;
    const duration = 1200; // 1.2s animation

    const step = (timestamp: number) => {
      if (!startTimestamp) startTimestamp = timestamp;
      const progress = Math.min((timestamp - startTimestamp) / duration, 1);
      
      // Easing function: easeOutQuart
      const easeProgress = 1 - Math.pow(1 - progress, 4);
      const currentScore = Math.round(easeProgress * score);
      
      setDisplayScore(currentScore);

      if (progress < 1) {
        requestAnimationFrame(step);
      }
    };

    requestAnimationFrame(step);
  }, [score]);

  // Determine color based on score
  let color = THEME.colors.critical;
  if (score > 80) color = THEME.colors.healthy;
  else if (score >= 60) color = THEME.colors.warning;

  // Arc math (0 to 180 degrees)
  const radius = 50;
  const strokeWidth = 8;
  const circumference = Math.PI * radius;
  const strokeDashoffset = circumference - (displayScore / 100) * circumference;

  return (
    <div className="flex flex-col items-center justify-center relative w-[120px] h-[70px]">
      <svg width="120" height="70" viewBox="0 0 120 70" className="absolute top-0">
        {/* Track */}
        <path 
          d="M 10 60 A 50 50 0 0 1 110 60" 
          fill="none" 
          stroke={THEME.colors.bgHover} 
          strokeWidth={strokeWidth} 
          strokeLinecap="round" 
        />
        {/* Fill */}
        <path 
          ref={arcRef}
          d="M 10 60 A 50 50 0 0 1 110 60" 
          fill="none" 
          stroke={color} 
          strokeWidth={strokeWidth} 
          strokeLinecap="round" 
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
        />
      </svg>
      <div className="absolute bottom-2 flex flex-col items-center">
        <span className="metric-value text-[32px] font-bold leading-none" style={{ color }}>{displayScore}</span>
        <span className="label-text text-[9px] text-textLabel uppercase tracking-widest mt-1">CONFIDENCE</span>
      </div>
    </div>
  );
};

const TypewriterText: React.FC<{ text: string }> = ({ text }) => {
  const [displayedText, setDisplayedText] = useState('');

  useEffect(() => {
    setDisplayedText('');
    let i = 0;
    const interval = setInterval(() => {
      if (i < text.length) {
        setDisplayedText(text.substring(0, i + 1));
        i++;
      } else {
        clearInterval(interval);
      }
    }, 30);
    return () => clearInterval(interval);
  }, [text]);

  return <span>{displayedText}</span>;
};

export const AIPredictionPanel: React.FC = () => {
  const { activePrediction } = usePreMortemStore();
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    if (activePrediction) {
      setIsVisible(true);
    } else {
      setIsVisible(false);
    }
  }, [activePrediction]);

  return (
    <div className="bg-bgPanel border-b border-borderTheme p-4 flex-none flex flex-col min-h-[200px]">
      {/* Header Row */}
      <div className="flex justify-between items-center mb-6">
        <span className="label-text text-[10px] text-textLabel uppercase tracking-[1.5px]">
          AI PREDICTION ENGINE
        </span>
        <div className="bg-bgHover border border-borderTheme rounded px-2 py-0.5">
          <span className="metric-value text-[9px] text-borderTheme">llama-3.3-70b via groq</span>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 flex flex-col justify-center relative">
        {!isVisible ? (
          /* IDLE STATE */
          <div className="flex flex-col items-center justify-center opacity-80">
            <svg width="24" height="24" viewBox="0 0 24 24" fill={THEME.colors.predicting} xmlns="http://www.w3.org/2000/svg" className="mb-4 animate-pulse">
              <path d="M12 2L22 7.7735V16.2265L12 22L2 16.2265V7.7735L12 2Z" />
            </svg>
            <span className="metric-value text-xs text-borderActive mb-1">Monitoring for anomaly clusters...</span>
            <span className="label-text text-[11px] text-borderTheme">Will activate when 2+ correlated signals detected</span>
          </div>
        ) : (
          /* ACTIVE STATE */
          <div className="flex flex-col transition-all duration-500 animate-in fade-in slide-in-from-bottom-2">
            
            <div className="flex justify-between items-center mb-6">
              {/* Confidence Arc */}
              <div className="flex-1 flex justify-center">
                <ConfidenceArc score={activePrediction!.confidence_score} />
              </div>
              
              {/* Time to Impact */}
              <div className="flex-1 flex flex-col items-center">
                <span className="label-text text-[10px] text-textLabel uppercase tracking-widest mb-1">ESTIMATED IMPACT IN</span>
                <span className={`metric-value text-2xl font-bold ${activePrediction!.time_to_impact_minutes < 15 ? 'text-critical animate-pulse' : 'text-warning'}`}>
                  {activePrediction!.time_to_impact_minutes} MIN
                </span>
              </div>
            </div>

            {/* Hypothesis */}
            <div className="border-t border-borderTheme pt-3 mb-4">
              <div className="flex justify-between items-center mb-1">
                <span className="label-text text-[10px] text-textLabel uppercase tracking-widest">ROOT CAUSE HYPOTHESIS #1</span>
                <span className="metric-value text-xs bg-healthy/15 text-healthy px-2 py-0.5 rounded-full border border-healthy/30">
                  {activePrediction!.root_cause_hypotheses[0]?.confidence || 0}%
                </span>
              </div>
              <p className="hypothesis-text text-[13px] text-textSecondary leading-relaxed h-[40px] overflow-hidden">
                <TypewriterText text={activePrediction!.root_cause_hypotheses[0]?.hypothesis || "Unknown cause."} />
              </p>
            </div>

            {/* Blast Radius */}
            <div className="mb-4">
              <div className="flex flex-wrap gap-2">
                {activePrediction!.blast_radius.potentially_affected.slice(0, 4).map(svc => (
                  <div key={svc} className="metric-value text-[10px] bg-critical/15 border border-critical/30 text-critical px-2 py-0.5 rounded truncate max-w-full" title={svc}>
                    {svc}
                  </div>
                ))}
              </div>
            </div>

            {/* Action Button */}
            <button className="w-full bg-predicting/15 border border-predicting/40 text-predicting font-mono text-xs py-2 hover:bg-predicting/25 transition-colors">
              VIEW FULL ANALYSIS + POST-MORTEM
            </button>
          </div>
        )}
      </div>
    </div>
  );
};
