import pytest
import numpy as np
from premortem.backend.detection.cusum_detector import CUSUMDetector
from premortem.backend.detection.correlation_engine import CorrelationEngine
from premortem.backend.ai.schema import AIPredictionSchema
from pydantic import ValidationError

def test_cusum_resets_after_alert():
    """Prove alarm fatigue prevention actually works by asserting S_pos resets to 0."""
    detector = CUSUMDetector(metric_name="test_metric", window_size=5)
    
    # Baseline: flat
    baseline = [10.0, 10.0, 10.0, 10.0, 10.0]
    # Anomaly: massive spike
    spike = [10.0, 10.0, 10.0, 10.0, 100.0]
    
    # Should trigger
    alert = detector.detect(np.array(spike))
    
    # Assert alert was generated
    assert alert is not None
    assert alert["drift_direction"] == "upward"
    
    # Assert accumulator is reset to 0 to prevent alarm fatigue
    assert detector.S_pos == 0.0

def test_correlation_handles_flat_line():
    """Prove NaN guard on zero-variance signal works (division by zero prevention)."""
    class MockBufferManager:
        def __init__(self):
            self.buffers = {
                "metric_A": self.MockBuffer([1.0] * 40), # Flat line (0 variance)
                "metric_B": self.MockBuffer([float(i) for i in range(40)]) # Moving line
            }
            
        class MockBuffer:
            def __init__(self, data):
                self.data = data
            def get_data(self):
                # Return mock timestamps and values
                return ([0]*len(self.data), self.data)
                
    engine = CorrelationEngine(MockBufferManager())
    matrix = engine.compute_pearson_matrix()
    
    # Correlation against a flat line should be ignored/filtered, not NaN
    assert len(matrix) == 0

def test_prediction_schema_validates():
    """Prove malformed Groq response doesn't crash the server, validation schema is strict."""
    valid_payload = {
        "prediction": {
            "confidence_score": 90,
            "time_to_impact_minutes": 10,
            "severity": "HIGH",
            "root_cause_hypotheses": [
                {
                    "rank": 1,
                    "hypothesis": "Test",
                    "confidence": 90,
                    "evidence": ["Test"]
                }
            ],
            "blast_radius": {
                "directly_affected": ["Test"],
                "potentially_affected": ["Test"],
                "estimated_users_impacted": "100"
            },
            "remediation_steps": [
                {
                    "priority": 1,
                    "action": "Fix",
                    "estimated_time_minutes": 5,
                    "prevents": "Outage"
                }
            ],
            "reasoning_chain": "Test",
            "confidence_reasoning": "Test",
            "watch_signals": ["Test"]
        },
        "postmortem_draft": {
            "title": "Test",
            "summary": "Test",
            "timeline": ["Test"],
            "impact": "Test",
            "root_cause": "Test",
            "remediation": "Test",
            "prevention": "Test"
        }
    }
    
    # Should parse without exception
    validated = AIPredictionSchema(**valid_payload)
    assert validated.prediction.confidence_score == 90
    
    # Prove malformed payload raises ValidationError
    malformed_payload = {"prediction": {}}
    with pytest.raises(ValidationError):
        AIPredictionSchema(**malformed_payload)
