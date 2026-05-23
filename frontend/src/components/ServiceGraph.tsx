import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import { usePreMortemStore } from '../store/usePreMortemStore';
import { THEME } from '../styles/theme';

function hexPath(cx: number, cy: number, r: number) {
  const pts = Array.from({length: 6}, (_, i) => {
    const angle = (Math.PI / 180) * (60 * i - 30);
    return [cx + r * Math.cos(angle), cy + r * Math.sin(angle)];
  });
  return `M ${pts.map(p => p.join(',')).join(' L ')} Z`;
}

export const ServiceGraph: React.FC = () => {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const { graphState, services, anomalies } = usePreMortemStore();
  const [selectedNode, setSelectedNode] = useState<string | null>(null);

  // Resize observer to get dynamic width/height
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });

  useEffect(() => {
    if (!containerRef.current) return;
    const resizeObserver = new ResizeObserver(entries => {
      if (entries[0]) {
        setDimensions({
          width: entries[0].contentRect.width,
          height: entries[0].contentRect.height
        });
      }
    });
    resizeObserver.observe(containerRef.current);
    return () => resizeObserver.disconnect();
  }, []);

  useEffect(() => {
    if (!svgRef.current || graphState.nodes.length === 0) return;

    const { width, height } = dimensions;
    const svg = d3.select(svgRef.current);
    svg.selectAll("*").remove(); // Clear on re-render

    // Define defs for animations
    const defs = svg.append('defs');
    
    // Create container group for zoom/pan
    const g = svg.append('g').attr('class', 'graph-container');

    // Setup force simulation
    const simulation = d3.forceSimulation(graphState.nodes as d3.SimulationNodeDatum[])
      .force("link", d3.forceLink(graphState.links).id((d: any) => d.id).distance(120).strength(0.8))
      .force("charge", d3.forceManyBody().strength(-400))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide().radius(50));

    // Edges
    const linkGroup = g.append("g").attr("class", "links");
    const link = linkGroup.selectAll("g.link")
      .data(graphState.links)
      .join("g")
      .attr("class", "link");

    const line = link.append("line")
      .attr("stroke", (d: any) => d.value > 0.7 ? THEME.colors.predicting : THEME.colors.border)
      .attr("stroke-width", (d: any) => d.value > 0.7 ? 2 : 1)
      .attr("stroke-opacity", (d: any) => d.value > 0.7 ? 0.8 : 0.6)
      .attr("stroke-dasharray", (d: any) => d.value > 0.7 ? "4,4" : "none");

    // Add animation to high-value links (causal edges)
    line.filter((d: any) => d.value > 0.7)
      .append("animate")
      .attr("attributeName", "stroke-dashoffset")
      .attr("values", "20;0")
      .attr("dur", "1s")
      .attr("repeatCount", "indefinite");

    const edgeLabels = link.filter((d: any) => d.value > 0.7)
      .append("text")
      .attr("class", "metric-value")
      .attr("font-size", 9)
      .attr("fill", THEME.colors.predicting)
      .attr("dy", -4)
      .attr("text-anchor", "middle")
      .text((d: any) => `r=${d.value.toFixed(2)}`);

    // Nodes
    const nodeGroup = g.append("g").attr("class", "nodes");
    const node = nodeGroup.selectAll("g.node")
      .data(graphState.nodes)
      .join("g")
      .attr("class", "node")
      .style("cursor", "pointer")
      .on("click", (event, d: any) => {
        setSelectedNode(d.id === selectedNode ? null : d.id);
        event.stopPropagation();
      })
      .call(drag(simulation) as any);

    // Click outside to deselect
    svg.on("click", () => setSelectedNode(null));

    // Render Hexagons
    node.each(function(d: any) {
      const el = d3.select(this);
      const serviceState = services.get(d.id);
      const score = serviceState?.healthScore ?? 100;
      const isAnomaly = anomalies.some(a => a.service === d.id && (Date.now() - new Date(a.timestamp).getTime() < 60000));
      
      const r = isAnomaly ? 36 : 28;
      
      let fill = THEME.colors.healthy + '15';
      let stroke = THEME.colors.healthy;
      let strokeWidth = 1.5;

      if (score < 50) {
        fill = THEME.colors.critical + '30';
        stroke = THEME.colors.critical;
        strokeWidth = 2.5;
      } else if (score < 70) {
        fill = THEME.colors.critical + '15';
        stroke = THEME.colors.critical;
        strokeWidth = 2;
      } else if (score < 90) {
        fill = THEME.colors.warning + '15';
        stroke = THEME.colors.warning;
        strokeWidth = 1.5;
      }

      // Anomaly Pulse Ring
      if (isAnomaly || score < 50) {
        el.append('circle')
          .attr('r', r + 8)
          .attr('fill', 'none')
          .attr('stroke', THEME.colors.critical)
          .attr('stroke-width', 1)
          .attr('opacity', 0.6)
          .append('animate')
          .attr('attributeName', 'r')
          .attr('values', `36;52;36`)
          .attr('dur', '2s')
          .attr('repeatCount', 'indefinite');
          
        el.select('circle').append('animate')
          .attr('attributeName', 'opacity')
          .attr('values', '0.6;0;0.6')
          .attr('dur', '2s')
          .attr('repeatCount', 'indefinite');
      }

      el.append('path')
        .attr('d', hexPath(0, 0, r))
        .attr('fill', fill)
        .attr('stroke', stroke)
        .attr('stroke-width', strokeWidth);

      // Node label
      el.append('text')
        .attr('class', 'metric-value')
        .attr('font-size', 11)
        .attr('fill', isAnomaly ? '#ffffff' : THEME.colors.textMuted)
        .attr('text-anchor', 'middle')
        .attr('dy', r + 14)
        .text(d.id);

      // Node metric inside
      if (serviceState?.primaryMetric !== undefined) {
        el.append('text')
          .attr('class', 'metric-value')
          .attr('font-size', 9)
          .attr('fill', stroke)
          .attr('text-anchor', 'middle')
          .attr('dy', 3)
          .text(`${Math.round(serviceState.primaryMetric)}ms`);
      }
    });

    // Handle Selection Focus
    if (selectedNode) {
      node.transition().duration(300).style("opacity", (d: any) => {
        // Is selected or directly connected?
        const isConnected = graphState.links.some(l => 
          (l.source.id === selectedNode && l.target.id === d.id) ||
          (l.target.id === selectedNode && l.source.id === d.id)
        );
        return d.id === selectedNode || isConnected ? 1 : 0.3;
      });
      
      node.filter((d: any) => d.id === selectedNode)
        .transition().duration(300)
        .attr("transform", (d: any) => `translate(${d.x},${d.y}) scale(1.2)`);
        
      link.transition().duration(300).style("opacity", (d: any) => {
        return d.source.id === selectedNode || d.target.id === selectedNode ? 1 : 0.1;
      });
    } else {
      node.transition().duration(300).style("opacity", 1).attr("transform", (d: any) => `translate(${d.x},${d.y}) scale(1)`);
      link.transition().duration(300).style("opacity", 1);
    }

    // Tick update
    simulation.on("tick", () => {
      line
        .attr("x1", (d: any) => d.source.x)
        .attr("y1", (d: any) => d.source.y)
        .attr("x2", (d: any) => d.target.x)
        .attr("y2", (d: any) => d.target.y);
        
      edgeLabels
        .attr("x", (d: any) => (d.source.x + d.target.x) / 2)
        .attr("y", (d: any) => (d.source.y + d.target.y) / 2);

      node.attr("transform", (d: any) => {
        // don't override the scale if it's selected
        const scale = d.id === selectedNode ? 1.2 : 1;
        return `translate(${d.x},${d.y}) scale(${scale})`;
      });
    });

    // Minimap (Bottom Right)
    const minimapWidth = 120;
    const minimapHeight = 80;
    const minimapPadding = 16;
    
    const minimap = svg.append("g")
      .attr("class", "minimap")
      .attr("transform", `translate(${width - minimapWidth - minimapPadding}, ${height - minimapHeight - minimapPadding})`);
      
    minimap.append("rect")
      .attr("width", minimapWidth)
      .attr("height", minimapHeight)
      .attr("fill", THEME.colors.bgPanel)
      .attr("stroke", THEME.colors.border)
      .attr("stroke-width", 1);
      
    // Scale for minimap
    const scaleX = d3.scaleLinear().domain([0, width]).range([0, minimapWidth]);
    const scaleY = d3.scaleLinear().domain([0, height]).range([0, minimapHeight]);
    
    // Minimap nodes
    simulation.on("tick.minimap", () => {
      const miniNodes = minimap.selectAll("circle").data(graphState.nodes);
      miniNodes.join("circle")
        .attr("cx", (d: any) => scaleX(d.x || width/2))
        .attr("cy", (d: any) => scaleY(d.y || height/2))
        .attr("r", 3)
        .attr("fill", (d: any) => {
           const s = services.get(d.id)?.healthScore ?? 100;
           return s < 50 ? THEME.colors.critical : s < 90 ? THEME.colors.warning : THEME.colors.healthy;
        });
    });

    return () => {
      simulation.stop();
    };
  }, [graphState, dimensions, services, anomalies, selectedNode]);

  const drag = (simulation: any) => {
    function dragstarted(event: any) {
      if (!event.active) simulation.alphaTarget(0.3).restart();
      event.subject.fx = event.subject.x;
      event.subject.fy = event.subject.y;
    }
    function dragged(event: any) {
      event.subject.fx = event.x;
      event.subject.fy = event.y;
    }
    function dragended(event: any) {
      if (!event.active) simulation.alphaTarget(0);
      event.subject.fx = null;
      event.subject.fy = null;
    }
    return d3.drag()
      .on("start", dragstarted)
      .on("drag", dragged)
      .on("end", dragended);
  };

  return (
    <div ref={containerRef} id="graph" className="w-full h-full relative bg-bgDark">
      <div className="absolute top-4 left-6 z-10">
        <span className="label-text text-[10px] text-borderTheme uppercase tracking-[2px] font-bold">
          CAUSAL DEPENDENCY GRAPH
        </span>
      </div>
      <svg ref={svgRef} className="w-full h-full" />
    </div>
  );
};
