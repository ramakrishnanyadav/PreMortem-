"""
reasoning_engine.py
-------------------
AI reasoning engine powered by Groq.
Receives anomaly cluster and graph context, outputs a structured JSON prediction.
"""
import json
import structlog
from groq import AsyncGroq
from typing import Dict, Any, Optional

from premortem.backend.config import settings
from premortem.backend.ai.schema import AIPredictionSchema

logger = structlog.get_logger(__name__)

class ReasoningEngine:
    def __init__(self):
        # Only initialize if key is present
        self.client = None
        if settings.GROQ_API_KEY:
            self.client = AsyncGroq(api_key=settings.GROQ_API_KEY)
        else:
            logger.warning("groq_api_key_missing", status="ai_engine_disabled")
            
        self.model = "llama-3.3-70b-versatile" # Groq's fast reasoning model

    async def generate_prediction(self, context_payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Takes the assembled anomaly context and asks the AI to generate a prediction.
        """
        if not self.client:
            logger.error("reasoning_engine_disabled", reason="no_api_key")
            return None

        prompt = f"""
You are an elite Principal Staff Engineer at Google SRE / Netflix Chaos Engineering.
You think in systems, not features. You anticipate failure modes before they happen.

Analyze the following infrastructure anomaly cluster and causal graph context.
Your goal is to detect an impending incident BEFORE it affects users.

CONTEXT:
{json.dumps(context_payload, indent=2)}

OUTPUT REQUIREMENT:
You MUST respond with valid JSON strictly matching this schema. Do not include markdown blocks or any other text.
{{
  "prediction": {{
    "confidence_score": 87,
    "time_to_impact_minutes": 23,
    "severity": "HIGH|MEDIUM|LOW|INFO",
    "root_cause_hypotheses": [
      {{
        "rank": 1,
        "hypothesis": "string",
        "confidence": 87,
        "evidence": ["signal1"],
        "supporting_historical_incident": "string"
      }}
    ],
    "blast_radius": {{
      "directly_affected": ["service"],
      "potentially_affected": ["service"],
      "estimated_users_impacted": "string"
    }},
    "remediation_steps": [
      {{
        "priority": 1,
        "action": "string",
        "command": "string",
        "estimated_time_minutes": 5,
        "prevents": "string"
      }}
    ],
    "reasoning_chain": "string",
    "confidence_reasoning": "string",
    "watch_signals": ["string"]
  }},
  "postmortem_draft": {{
    "title": "string",
    "summary": "string",
    "timeline": ["string"],
    "impact": "string",
    "root_cause": "string",
    "remediation": "string",
    "prevention": "string"
  }}
}}
"""
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
                response_format={"type": "json_object"}
            )
            
            raw_json = response.choices[0].message.content
            parsed = json.loads(raw_json)
            
            # Validate with Pydantic
            validated = AIPredictionSchema(**parsed)
            return validated.dict()
            
        except Exception as e:
            logger.error("reasoning_engine_failure", error=str(e))
            return None
