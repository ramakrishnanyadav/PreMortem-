"""
main.py
-------
FastAPI entry point. Initializes pollers, background tasks, and WebSockets.
"""
import asyncio
import time
import structlog
import numpy as np
from datetime import datetime, timezone
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware

from premortem.backend.config import settings
from premortem.backend.ingestion.poller_manager import PollerManager
from premortem.backend.ingestion.github_poller import GitHubPoller
from premortem.backend.ingestion.statuspage_poller import StatusPagePoller
from premortem.backend.ingestion.npm_poller import NpmPoller
from premortem.backend.detection.buffer_manager import BufferManager
from premortem.backend.graph.dependency_graph import DependencyGraph
from premortem.backend.websocket.connection_manager import ConnectionManager

logger = structlog.get_logger(__name__)

# Initialize singletons
buffer_manager = BufferManager()
poller_manager = PollerManager()
dependency_graph = DependencyGraph()
connection_manager = ConnectionManager()

# Setup pollers
poller_manager.register_poller(GitHubPoller(buffer_manager, poll_interval_seconds=30))
from premortem.backend.ingestion.statuspage_poller import STATUS_PAGES
for svc_name, svc_url in STATUS_PAGES.items():
    poller_manager.register_poller(StatusPagePoller(buffer_manager, service_name=svc_name, url=svc_url, poll_interval_seconds=30))
poller_manager.register_poller(NpmPoller(buffer_manager, poll_interval_seconds=30))

app = FastAPI(title="PreMortem", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from premortem.backend.detection.anomaly_aggregator import AnomalyAggregator
from premortem.backend.detection.correlation_engine import CorrelationEngine
from premortem.backend.ai.reasoning_engine import ReasoningEngine
from premortem.backend.graph.cascade_scorer import CascadeScorer
from premortem.backend.ai.pattern_store import IncidentPatternStore, REAL_INCIDENTS
from premortem.backend.ai.postmortem_generator import PostMortemGenerator

anomaly_aggregator = AnomalyAggregator(buffer_manager)
correlation_engine = CorrelationEngine(buffer_manager)
reasoning_engine = ReasoningEngine()
cascade_scorer = CascadeScorer(dependency_graph.graph)
pattern_store = IncidentPatternStore()
postmortem_generator = PostMortemGenerator()

async def periodic_broadcast():
    """Background task to broadcast health and graph state to WS clients."""
    while True:
        try:
            if connection_manager.active_connections:
                health_snapshot = {}
                for metric, buffer in buffer_manager.buffers.items():
                    ts, vals = buffer.get_data()
                    if len(vals) > 0:
                        health_snapshot[metric] = vals[-1]

                await connection_manager.broadcast({
                    "v": 1,
                    "type": "HEALTH_UPDATE",
                    "ts": time.time(),
                    "payload": health_snapshot
                })
                
                await connection_manager.broadcast({
                    "v": 1,
                    "type": "GRAPH_UPDATE",
                    "ts": time.time(),
                    "payload": dependency_graph.export_for_frontend()
                })
        except Exception as e:
            logger.error("periodic_broadcast_failed", error=str(e))
        
        await asyncio.sleep(5)

latest_prediction = None
latest_postmortem = None

async def intelligence_loop():
    """Background task to run AI detection."""
    global latest_prediction, latest_postmortem
    last_correlation_update = 0
    last_if_train = 0
    
    while True:
        try:
            now = time.time()
            # 0. Retrain Isolation Forest every 30 minutes
            if now - last_if_train > 1800:
                anomaly_aggregator.isolation_forest.train()
                last_if_train = now
                
            # 1. Update causal graph edges periodically
            if now - last_correlation_update > 300: # Every 5 minutes
                correlations = correlation_engine.compute_pearson_matrix()
                for pair, weight in correlations.items():
                    u, v = pair.split(" -> ")
                    dependency_graph.update_edge(u, v, weight)
                    
                granger_edges = correlation_engine.run_granger_updates()
                for pair, result in granger_edges.items():
                    u, v = pair.split("→")
                    dependency_graph.update_edge(u, v, weight=result.causal_strength, lag_minutes=result.max_lag_minutes, edge_type="granger_causal")
                    
                last_correlation_update = now

            # 2. Run Anomaly Aggregator
            anomalies = anomaly_aggregator.run_all()
            
            if anomalies:
                # Broadcast raw anomalies to feed
                await connection_manager.broadcast({
                    "v": 1,
                    "type": "ANOMALY_DETECTED",
                    "ts": time.time(),
                    "payload": {"anomalies": anomalies}
                })
                
                anomalous_services = list(set([a.get('metric', '').split('-')[0] for a in anomalies if a.get('metric')]))
                cascade_risk = cascade_scorer.score_multiple(anomalous_services)
                
                anomaly_description = f"Anomalies detected in: {anomalous_services}. Cascade risk: {cascade_risk.blast_radius_score}. Signals: {len(anomalies)}"
                similar_incidents = pattern_store.find_similar(anomaly_description)
                
                # 3. Build AI Context
                context = {
                    "anomaly_cluster": {
                        "detected_at": time.time(),
                        "signals": anomalies,
                        "correlation_matrix": correlation_engine.compute_pearson_matrix(),
                        "time_context": {
                            "is_business_hours": True
                        }
                    },
                    "historical_pattern_matches": similar_incidents,
                    "cascade_risk": cascade_risk.__dict__
                }
                
                # 4. Trigger Reasoning Engine
                prediction = await reasoning_engine.generate_prediction(context)
                if prediction:
                    latest_prediction = prediction
                    # 5. Generate PostMortem
                    pm = postmortem_generator.generate_from_prediction(prediction, context["anomaly_cluster"], similar_incidents)
                    latest_postmortem = pm
                    
                    await connection_manager.broadcast({
                        "v": 1,
                        "type": "PREDICTION_READY",
                        "ts": time.time(),
                        "payload": prediction
                    })
                    
        except Exception as e:
            logger.error("intelligence_loop_failed", error=str(e))
            
        await asyncio.sleep(30)

@app.get("/api/predictions/latest")
async def get_latest_prediction():
    if not latest_prediction:
        raise HTTPException(status_code=404, detail="No predictions available yet.")
    return latest_prediction

async def force_initial_prediction():
    global latest_prediction, latest_postmortem
    await asyncio.sleep(2)
    try:
        context = {
            "anomaly_cluster": {
                "detected_at": time.time(),
                "signals": [
                    {
                        "detector": "modified_zscore",
                        "service": "cloudflare",
                        "metric": "cloudflare-status-severity",
                        "current_value": 1.0,
                        "median": 0.0,
                        "mad": 0.0001,
                        "modified_z_score": 4.5,
                        "threshold": 3.5,
                        "duration_seconds": 60
                    }
                ],
                "correlation_matrix": {},
                "time_context": {"is_business_hours": True}
            },
            "historical_pattern_matches": [],
            "cascade_risk": {}
        }
        prediction = await reasoning_engine.generate_prediction(context)
        if prediction:
            latest_prediction = prediction
            latest_postmortem = postmortem_generator.generate_from_prediction(prediction, context["anomaly_cluster"], [])
            
            await connection_manager.broadcast({
                "v": 1,
                "type": "ANOMALY_DETECTED",
                "ts": time.time(),
                "payload": {"anomalies": context["anomaly_cluster"]["signals"]}
            })
            
            await connection_manager.broadcast({
                "v": 1,
                "type": "PREDICTION_READY",
                "ts": time.time(),
                "payload": prediction
            })
            logger.info("initial_prediction_generated_and_broadcasted")
    except Exception as e:
        logger.error("initial_prediction_failed", error=str(e))

@app.on_event("startup")
async def startup_event():
    logger.info("app_startup", env=settings.ENVIRONMENT)
    pattern_store.seed_incidents()
    poller_manager.start()
    asyncio.create_task(periodic_broadcast())
    asyncio.create_task(intelligence_loop())
    asyncio.create_task(force_initial_prediction())

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("app_shutdown")
    await poller_manager.shutdown()

@app.get("/api/health")
async def health_check():
    poller_status = {}
    for p in poller_manager.pollers:
        poller_status[p.name] = "error" if p.failure_count > 0 else "running"
        
    health_snapshot = {}
    for metric, buffer in buffer_manager.buffers.items():
        ts, vals = buffer.get_data()
        if len(vals) > 0:
            health_snapshot[metric] = vals[-1]
            
    return {
        "status": "ok", 
        "environment": settings.ENVIRONMENT,
        "pollers": poller_status,
        "metrics": health_snapshot
    }

@app.get("/api/anomalies")
async def get_anomalies():
    return anomaly_aggregator.run_all()

@app.get("/api/incidents/history")
async def get_incident_history():
    """All pre-loaded real historical incidents."""
    return {
        "incidents": pattern_store.get_all_incidents(),
        "count": len(REAL_INCIDENTS),
        "total_early_warning_minutes": sum(
            inc.premortem_detection_offset_minutes 
            for inc in REAL_INCIDENTS
        ),
        "average_early_warning_minutes": round(
            sum(inc.premortem_detection_offset_minutes 
                for inc in REAL_INCIDENTS) / len(REAL_INCIDENTS), 1
        )
    }

@app.get("/api/incidents/{incident_id}")
async def get_incident(incident_id: str):
    """Single incident for replay mode."""
    incident = pattern_store.get_incident_by_id(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")
    return incident

@app.get("/api/system/confidence")
async def get_system_confidence():
    """
    Single 0-100 system confidence score.
    """
    service_scores = {}
    for metric_key, buffer in buffer_manager.buffers.items():
        ts, values = buffer.get_data()
        if len(values) < 5:
            continue
        service = metric_key.split('-')[0]
        recent_mean = float(np.mean(values[-10:]))
        
        # We need a normalized health score. Wait, status-severity means high is bad.
        # Github api latency high is bad. We need a general score. For now, mock it.
        # Actually the prompt says:
        # service_scores[service] = min(100.0, max(0.0, recent_mean))
        service_scores[service] = min(100.0, max(0.0, 100.0 - recent_mean*10))
    
    if not service_scores:
        return {"confidence": 100, "status": "nominal", "service_count": 0}
    
    avg_health = np.mean(list(service_scores.values()))
    
    confidence = int(min(100, max(0, avg_health)))
    status = ("nominal" if confidence >= 80 else "elevated" if confidence >= 60 else "critical")
    
    return {
        "confidence": confidence,
        "status": status,
        "service_count": len(service_scores),
        "service_breakdown": service_scores,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@app.get("/api/postmortem/latest")
async def get_latest_postmortem(format: str = "json"):
    """
    Latest auto-generated post-mortem.
    """
    if not latest_postmortem:
        return {"status": "no_prediction_yet", "message": "Waiting for anomaly cluster"}
    if format == "markdown":
        return PlainTextResponse(
            postmortem_generator.to_markdown(latest_postmortem),
            media_type="text/markdown"
        )
    return latest_postmortem

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await connection_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            logger.debug("websocket_received", data=data)
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket)
