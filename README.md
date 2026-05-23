<div align="center">
  <h1>PreMortem™</h1>
  <p><b>Enterprise-Grade Predictive Infrastructure Intelligence Platform</b></p>
  
  [![Status](https://img.shields.io/badge/Release-Production--Ready-success.svg)]()
  [![Frontend](https://img.shields.io/badge/Frontend-React%20%7C%20Vite%20%7C%20D3.js-blue.svg)]()
  [![Backend](https://img.shields.io/badge/Backend-FastAPI%20%7C%20Python-green.svg)]()
  [![AI](https://img.shields.io/badge/Reasoning-Llama--3.3--70b%20%7C%20Groq%20%7C%20ChromaDB-purple.svg)]()
</div>

<br/>

## Executive Summary

Modern distributed infrastructure operates at a scale where traditional, reactive observability is no longer sufficient. Static alerting thresholds generate extreme operational noise and, fundamentally, only notify Site Reliability Engineering (SRE) teams *after* a critical P0 incident has already impacted the end-user.

**PreMortem™** fundamentally transforms infrastructure observability from a reactive debugging process into a predictive intelligence system. By combining high-frequency telemetry ingestion with a mathematical anomaly ensemble and deterministic causal graphing, PreMortem triggers an AI reasoning layer to predict catastrophic failures **before** they propagate to the end-user.

We provide enterprise engineering teams with the ultimate operational advantage: **The Early Warning Gap.**

---

## Core Capabilities

### 1. The Statistical Ensemble Engine
Static thresholds fail in dynamic, noisy cloud environments. PreMortem utilizes a composite mathematical engine to detect true causal drift:
*   **Modified Z-Score:** Calculates volatility using Median Absolute Deviation (MAD), rendering it highly resilient against extreme, non-actionable outliers.
*   **CUSUM (Cumulative Sum):** Detects slow, sustained systemic degradation (e.g., slow memory leaks, creeping API latency) that fly under standard deviation alerts.
*   **Isolation Forest:** An unsupervised machine learning algorithm deployed to detect multivariate anomaly clusters across disparate infrastructure boundaries.

### 2. Causal Intelligence Topology
Correlation does not equal causation. PreMortem implements a rigorous **Granger Causality** algorithm to mathematically prove *directional causation* (e.g., establishing that a spike in Database Latency is actively causing a downstream spike in API Latency). Coupled with a **Cascade BFS Scorer**, the system automatically calculates the exact "blast radius" of an impending failure.

### 3. Grounded AI Reasoning (Llama 3.3 70B)
PreMortem does not utilize AI as a generic chatbot. The reasoning layer is only triggered when mathematical thresholds validate a causal anomaly cluster.
*   **Zero-Hallucination Pipeline:** The AI is strictly grounded against a `ChromaDB` vector store containing historical, verified incident patterns.
*   **Automated Root Cause Analysis:** Generates structured JSON predicting the Root Cause, Time to Impact, and Blast Radius.
*   **Actionable Remediation:** Automatically issues a PreMortem document containing immediate remediation procedures before the system fully degrades.

### 4. Zero-Scroll Operational War Room
*   **Fixed-Grid Architecture:** A strict, overflow-hidden CSS-Grid layout designed specifically for high-stress SRE operations. No scrolling, no context switching, zero cognitive overload.
*   **Real-Time D3.js Force Simulation:** Renders the causal dependency graph in real-time at 60 FPS, providing immediate visual tracking of cascading failures.
*   **Incident Replay Engine:** A powerful training utility driven by `requestAnimationFrame` that allows engineering teams to securely replay and analyze historical outages at variable speeds.

---

## System Architecture

The platform operates on a decoupled, asynchronous, real-time architecture optimized for continuous stream processing.

1. **Ingestion Layer:** Actively polls telemetry via robust background workers.
2. **Buffer Management:** Streams data into fixed-size, thread-safe `CircularBuffers` to guarantee a constant `O(1)` memory footprint during extreme ingestion spikes.
3. **Intelligence Loop:** Periodically computes Pearson matrices and Granger updates.
4. **WebSocket Broadcaster:** Streams delta updates, AI predictions, and anomaly logs to connected client interfaces via an exponential backoff connection manager.

---

## Deployment Instructions

### Prerequisites
* Python 3.10+
* Node.js 18+
* Redis (Optional: for advanced pub/sub scaling)

### Backend Services Initialization
```bash
cd premortem/backend
python -m venv .venv

# Activate Virtual Environment
source .venv/bin/activate        # Unix/macOS
.venv\Scripts\activate           # Windows

# Install Dependencies
pip install -r requirements.txt

# Secure API Configuration
echo "GROQ_API_KEY=your_production_key_here" > .env

# Launch Uvicorn ASGI Server
uvicorn main:app --reload --port 8000
```

### Frontend War Room Initialization
```bash
cd premortem/frontend
npm install

# Launch Vite Development Server
npm run dev
```

---

## Operational Guide

1.  **Production Monitoring:** Navigate to the local port specified by Vite (default: `http://localhost:5173`). The dashboard instantly establishes a WebSocket connection and will display "ALL SYSTEMS NOMINAL" under healthy telemetry.
2.  **Incident Replay Activation:** To train on historical degradation, press the **`R`** key to trigger the Incident Replay Engine. Select an incident, engage playback, and observe the system detect and predict the failure prior to the User Impact marker.

---

*Designed and engineered for highly available, mission-critical infrastructure. Engineered for Indianext.*
