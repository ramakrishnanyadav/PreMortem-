import React, { useEffect, useState } from 'react';
import { usePreMortemStore } from '../store/usePreMortemStore';

export const TopBar: React.FC = () => {
  const { wsConnected, systemStatus, incidentCount } = usePreMortemStore();
  const [timeStr, setTimeStr] = useState<string>('');

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      const h = String(now.getUTCHours()).padStart(2, '0');
      const m = String(now.getUTCMinutes()).padStart(2, '0');
      const s = String(now.getUTCSeconds()).padStart(2, '0');
      setTimeStr(`UTC ${h}:${m}:${s}`);
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  const getStatusConfig = () => {
    if (!wsConnected) {
      return {
        text: "RECONNECTING...",
        bgClass: "bg-gray-800",
        borderClass: "border-gray-600",
        textClass: "text-gray-400",
        dotClass: "bg-gray-400 animate-pulse"
      };
    }
    
    switch (systemStatus) {
      case 'nominal':
        return {
          text: "ALL SYSTEMS NOMINAL",
          bgClass: "bg-healthy/15",
          borderClass: "border-healthy/40",
          textClass: "text-healthy",
          dotClass: "bg-healthy animate-pulse-fast"
        };
      case 'elevated':
        return {
          text: "ELEVATED RISK DETECTED",
          bgClass: "bg-warning/15",
          borderClass: "border-warning/40",
          textClass: "text-warning",
          dotClass: "bg-warning animate-pulse-fast"
        };
      case 'critical':
        return {
          text: "ACTIVE INCIDENT DETECTED",
          bgClass: "bg-critical/15",
          borderClass: "border-critical/40",
          textClass: "text-critical",
          dotClass: "bg-critical animate-pulse-fast"
        };
      default:
        return {
          text: "UNKNOWN STATUS",
          bgClass: "bg-unknown/15",
          borderClass: "border-unknown/40",
          textClass: "text-unknown",
          dotClass: "bg-unknown"
        };
    }
  };

  const statusConfig = getStatusConfig();
  
  const incidentColor = incidentCount === 0 ? 'text-healthy' : incidentCount <= 2 ? 'text-warning' : 'text-critical';

  return (
    <div id="topbar" className="flex items-center justify-between px-6 bg-bgDark border-b border-borderTheme h-12 w-full">
      {/* Left Side */}
      <div className="flex items-center">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="#6366f1" xmlns="http://www.w3.org/2000/svg" className="mr-2">
          <path d="M12 2L22 7.7735V16.2265L12 22L2 16.2265V7.7735L12 2Z" />
        </svg>
        <div className="logo-text text-base flex">
          <span className="font-bold text-white">PRE</span>
          <span className="font-normal text-predicting">MORTEM</span>
        </div>
        <div className="label-text text-[11px] text-textLabel ml-3 pl-3 border-l border-borderTheme uppercase tracking-wider">
          Predictive Infrastructure Intelligence
        </div>
      </div>

      {/* Center */}
      <div className="flex items-center">
        <div className={`flex items-center px-4 py-1 rounded-full border ${statusConfig.bgClass} ${statusConfig.borderClass}`}>
          <div className={`w-2 h-2 rounded-full mr-2 ${statusConfig.dotClass}`}></div>
          <span className={`label-text text-xs tracking-wider font-medium ${statusConfig.textClass}`}>
            {statusConfig.text}
          </span>
        </div>
      </div>

      {/* Right Side */}
      <div className="flex items-center">
        <div className="metric-value text-[13px] text-healthy tracking-wider">
          {timeStr}
        </div>
        
        <div className="w-[1px] h-5 bg-borderTheme mx-4"></div>
        
        <div className="flex flex-col items-center">
          <span className="label-text text-[10px] text-textLabel uppercase tracking-[1px] leading-tight">
            INCIDENTS
          </span>
          <span className={`metric-value text-xl font-bold leading-none ${incidentColor}`}>
            {incidentCount}
          </span>
        </div>
      </div>
    </div>
  );
};
