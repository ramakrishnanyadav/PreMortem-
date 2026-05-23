from pydantic import BaseModel, Field
from typing import List, Optional

class RootCauseHypothesis(BaseModel):
    rank: int
    hypothesis: str
    confidence: int
    evidence: List[str]
    supporting_historical_incident: Optional[str] = None

class BlastRadius(BaseModel):
    directly_affected: List[str]
    potentially_affected: List[str]
    estimated_users_impacted: str

class RemediationStep(BaseModel):
    priority: int
    action: str
    command: Optional[str] = None
    estimated_time_minutes: int
    prevents: str

class PredictionDetails(BaseModel):
    confidence_score: int
    time_to_impact_minutes: int
    severity: str
    root_cause_hypotheses: List[RootCauseHypothesis]
    blast_radius: BlastRadius
    remediation_steps: List[RemediationStep]
    reasoning_chain: str
    confidence_reasoning: str
    watch_signals: List[str]

class PostmortemDraft(BaseModel):
    title: str
    summary: str
    timeline: List[str]
    impact: str
    root_cause: str
    remediation: str
    prevention: str

class AIPredictionSchema(BaseModel):
    prediction: PredictionDetails
    postmortem_draft: PostmortemDraft
