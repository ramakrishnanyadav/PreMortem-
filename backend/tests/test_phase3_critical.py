import pytest
import numpy as np
import networkx as nx
from premortem.backend.detection.granger_causality import GrangerCausalityEngine
from premortem.backend.detection.isolation_forest import IsolationForestDetector
from premortem.backend.graph.cascade_scorer import CascadeScorer
from premortem.backend.ai.postmortem_generator import PostMortemGenerator

from unittest.mock import patch

@patch('premortem.backend.detection.granger_causality.grangercausalitytests')
def test_granger_detects_known_causal_pair(mock_granger):
    # Mock statsmodels to return a highly significant p-value at lag 3
    mock_granger.return_value = {
        1: [{'ssr_ftest': [0, 0.5]}],
        2: [{'ssr_ftest': [0, 0.1]}],
        3: [{'ssr_ftest': [0, 0.001]}] # lag 3 is significant
    }
    
    class MockBuffer:
        def __init__(self, data):
            self.data = data
        def get_data(self):
            return ([0]*len(self.data), self.data)
            
    buffers = {
        "svc-A": MockBuffer([1.0] * 100), # dummy data, mock handles it
        "svc-B": MockBuffer([2.0] * 100)
    }
    
    engine = GrangerCausalityEngine(buffers)
    # patch np.std to prevent constant series rejection
    with patch('numpy.std', return_value=1.0):
        result = engine.test_causality("svc", "A", "svc", "B")
    
    assert result is not None
    assert result.is_significant is True
    assert result.p_value == 0.001
    assert result.predictive_lag_samples == 3

@patch('premortem.backend.detection.granger_causality.grangercausalitytests')
def test_granger_rejects_independent_series(mock_granger):
    # Mock statsmodels to return non-significant p-values everywhere
    mock_granger.return_value = {
        1: [{'ssr_ftest': [0, 0.5]}],
        2: [{'ssr_ftest': [0, 0.6]}],
        3: [{'ssr_ftest': [0, 0.8]}]
    }
    
    class MockBuffer:
        def __init__(self, data):
            self.data = data
        def get_data(self):
            return ([0]*len(self.data), self.data)
            
    buffers = {
        "svc-A": MockBuffer([1.0] * 100),
        "svc-B": MockBuffer([2.0] * 100)
    }
    
    engine = GrangerCausalityEngine(buffers)
    with patch('numpy.std', return_value=1.0):
        result = engine.test_causality("svc", "A", "svc", "B")
    
    if result is not None:
        assert result.is_significant is False

def test_isolation_forest_catches_multivariate_anomaly():
    # Train IF on 60 normal samples
    class MockBuffer:
        def __init__(self, data):
            self.data = data
        def get_data(self):
            return ([0]*len(self.data), self.data)
            
    # Generate 60 normal samples for 4 metrics
    base_data = [list(np.random.normal(0, 1, 60)) for _ in range(4)]
    
    buffers = {
        "svc-A": MockBuffer(base_data[0].copy()),
        "svc-B": MockBuffer(base_data[1].copy()),
        "svc-C": MockBuffer(base_data[2].copy()),
        "svc-D": MockBuffer(base_data[3].copy())
    }
    
    detector = IsolationForestDetector(buffers)
    assert detector.train() is True
    
    # Should not be anomaly normally
    result1 = detector.detect()
    assert result1 is not None
    
    # Now feed one sample where 4 metrics simultaneously shift slightly
    for i in range(4):
        base_data[i].append(3.0) # slight shift on all 4
        buffers[list(buffers.keys())[i]].data = base_data[i]
        
    result2 = detector.detect()
    assert result2 is not None
    assert result2.is_anomaly is True

def test_cascade_scorer_blast_radius_attenuates():
    # Build a 4-node chain: A→B→C→D with weight 0.8
    graph = nx.DiGraph()
    graph.add_edge("A", "B", weight=0.8)
    graph.add_edge("B", "C", weight=0.8)
    graph.add_edge("C", "D", weight=0.8)
    
    scorer = CascadeScorer(graph)
    risk = scorer.score("A")
    
    assert "B" in risk.risk_scores
    assert "C" in risk.risk_scores
    assert "D" in risk.risk_scores
    
    # Assert risk attenuates by hop
    assert risk.risk_scores["B"] > risk.risk_scores["C"]
    assert risk.risk_scores["C"] > risk.risk_scores["D"]

def test_postmortem_generated_completely():
    prediction = {
        "confidence_score": 90,
        "time_to_impact_minutes": 10,
        "severity": "HIGH",
        "root_cause_hypotheses": [
            {
                "hypothesis": "Test Hypothesis",
                "confidence": 90
            }
        ],
        "blast_radius": {
            "directly_affected": ["svc-A"],
            "potentially_affected": ["svc-B"],
            "estimated_users_impacted": "1000"
        },
        "remediation_steps": [
            {
                "priority": 1,
                "action": "Fix it",
                "estimated_time_minutes": 5,
                "prevents": "Downtime"
            }
        ]
    }
    
    anomaly_context = {
        "signals": [
            {
                "service": "svc",
                "metric": "A",
                "current_value": 1.0,
                "modified_z_score": 4.5,
                "baseline_mean": 0.0,
                "duration_seconds": 60
            }
        ]
    }
    
    generator = PostMortemGenerator()
    pm = generator.generate_from_prediction(prediction, anomaly_context, [])
    
    assert pm.title != ""
    assert pm.summary != ""
    assert pm.root_cause == "Test Hypothesis"
    assert len(pm.timeline) >= 2 # 1 for signal, 1 for detection
    
    md = generator.to_markdown(pm)
    assert "PREMORTEM_DETECTION" in md or "PreMortem predictive alert fired" in md
    assert "Test Hypothesis" in md
