import React from 'react';

interface ConfidenceMeterProps {
  score: number;
}

export const ConfidenceMeter: React.FC<ConfidenceMeterProps> = ({ score }) => {
  // SVG Arc calculation
  const radius = 40;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (score / 100) * circumference;

  let color = '#10b981'; // success
  if (score > 60) color = '#f59e0b'; // warning
  if (score > 85) color = '#ef4444'; // danger

  return (
    <div className="relative flex items-center justify-center w-24 h-24">
      <svg className="transform -rotate-90 w-24 h-24">
        <circle
          cx="48"
          cy="48"
          r={radius}
          stroke="currentColor"
          strokeWidth="8"
          fill="transparent"
          className="text-gray-800"
        />
        <circle
          cx="48"
          cy="48"
          r={radius}
          stroke={color}
          strokeWidth="8"
          fill="transparent"
          strokeDasharray={circumference}
          strokeDashoffset={strokeDashoffset}
          className="transition-all duration-1000 ease-in-out"
        />
      </svg>
      <div className="absolute flex flex-col items-center justify-center">
        <span className="text-xl font-bold text-white">{score}%</span>
      </div>
    </div>
  );
};
