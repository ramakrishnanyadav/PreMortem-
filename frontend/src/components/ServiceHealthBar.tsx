import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';
import { usePreMortemStore } from '../store/usePreMortemStore';
import { THEME } from '../styles/theme';

const Sparkline: React.FC<{ data: number[], color: string }> = ({ data, color }) => {
  const svgRef = useRef<SVGSVGElement>(null);

  useEffect(() => {
    if (!svgRef.current || data.length === 0) return;
    
    const svg = d3.select(svgRef.current);
    svg.selectAll('*').remove();
    
    const width = 80;
    const height = 24;
    
    const margin = { top: 2, right: 0, bottom: 2, left: 0 };
    const innerWidth = width - margin.left - margin.right;
    const innerHeight = height - margin.top - margin.bottom;
    
    const min = d3.min(data) || 0;
    const max = d3.max(data) || 10;
    const padding = (max - min) * 0.1 || 1;
    
    const xScale = d3.scaleLinear()
      .domain([0, 19]) // Always show last 20 points
      .range([0, innerWidth]);
      
    const yScale = d3.scaleLinear()
      .domain([min - padding, max + padding])
      .range([innerHeight, 0]);
      
    const line = d3.line<number>()
      .x((_, i) => xScale(i + (20 - data.length))) // Shift right if not full
      .y(d => yScale(d))
      .curve(d3.curveMonotoneX);
      
    const area = d3.area<number>()
      .x((_, i) => xScale(i + (20 - data.length)))
      .y0(innerHeight)
      .y1(d => yScale(d))
      .curve(d3.curveMonotoneX);

    const g = svg.append('g').attr('transform', `translate(${margin.left},${margin.top})`);
    
    // Area fill
    g.append('path')
      .datum(data)
      .attr('fill', color)
      .attr('opacity', 0.1)
      .attr('d', area);
      
    // Line
    g.append('path')
      .datum(data)
      .attr('fill', 'none')
      .attr('stroke', color)
      .attr('stroke-width', 1.5)
      .attr('d', line);
      
  }, [data, color]);

  return <svg ref={svgRef} width="80" height="24" className="overflow-hidden" />;
};

export const ServiceHealthBar: React.FC = () => {
  const { services } = usePreMortemStore();
  const serviceArray = Array.from(services.entries());

  return (
    <div id="healthbar" className="bg-bgPanel border-t border-borderTheme px-2 grid grid-flow-col auto-cols-fr gap-0 h-[120px]">
      {serviceArray.map(([id, state]) => {
        let color = THEME.colors.healthy;
        if (state.healthScore < 50) color = THEME.colors.critical;
        else if (state.healthScore < 90) color = THEME.colors.warning;
        
        const isAnomaly = state.healthScore < 50;

        return (
          <div key={id} className="group border-r border-bgHover p-3 cursor-pointer hover:bg-bgHover transition-colors duration-150 flex flex-col justify-between">
            {/* Row 1: Name and Status Dot */}
            <div className="flex items-center space-x-2">
              <div className={`w-1.5 h-1.5 rounded-full ${isAnomaly ? 'animate-pulse-fast' : ''}`} style={{ backgroundColor: color }}></div>
              <span className="metric-value text-[11px] uppercase text-textMuted">{id}</span>
            </div>
            
            {/* Row 2: Metric Value */}
            <div className="metric-value text-xl font-bold mt-2" style={{ color }}>
              {state.primaryMetric ? Math.round(state.primaryMetric) : 0}<span className="text-[12px] ml-1">ms</span>
            </div>
            
            {/* Row 3: Sparkline */}
            <div className="mt-2 h-6 flex items-end">
              <Sparkline data={state.sparklineData} color={color} />
            </div>
          </div>
        );
      })}
    </div>
  );
};
