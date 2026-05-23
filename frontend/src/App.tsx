import React from 'react';
import { useWebSocket } from './hooks/useWebSocket';
import { TopBar } from './components/TopBar';
import { ServiceGraph } from './components/ServiceGraph';
import { AIPredictionPanel } from './components/AIPredictionPanel';
import { AnomalyFeed } from './components/AnomalyFeed';
import { ServiceHealthBar } from './components/ServiceHealthBar';
import { IncidentReplay } from './components/IncidentReplay';

function App() {
  // Connect to the FastAPI WebSocket
  useWebSocket('ws://localhost:8000/ws');

  return (
    <div id="app-grid">
      {/* TopBar spans entire top row */}
      <div className="col-span-2 row-start-1">
        <TopBar />
      </div>
      
      {/* Causal Dependency Graph takes up left column (flex: 1) */}
      <div className="col-start-1 row-start-2 overflow-hidden border-r border-borderTheme">
        <ServiceGraph />
      </div>
      
      {/* Right Sidebar takes up right column (380px fixed via CSS) */}
      <div className="col-start-2 row-start-2 flex flex-col overflow-hidden bg-bgDark">
        <AIPredictionPanel />
        <AnomalyFeed />
      </div>
      
      {/* Service Health Bar spans entire bottom row */}
      <div className="col-span-2 row-start-3">
        <ServiceHealthBar />
      </div>

      {/* Overlays */}
      <IncidentReplay />
    </div>
  );
}

export default App;
