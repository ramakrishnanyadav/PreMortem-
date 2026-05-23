from dataclasses import dataclass
from datetime import datetime, timezone
import json
from typing import Optional
import structlog

log = structlog.get_logger()

@dataclass
class PostMortem:
    title: str
    generated_at: str
    status: str              # "PREDICTED" | "CONFIRMED" | "RESOLVED"
    severity: str
    summary: str
    detection_method: str
    timeline: list[dict]
    impact: dict
    root_cause: str
    contributing_factors: list[str]
    remediation_steps: list[dict]
    prevention_recommendations: list[dict]
    metrics_at_detection: dict
    affected_services: list[str]
    estimated_users_impacted: str
    confidence_score: int
    similar_past_incidents: list[str]

class PostMortemGenerator:
    """
    Converts AI prediction output into a structured post-mortem
    document. Generated BEFORE the incident happens — a predictive
    post-mortem. This is the feature no competitor has.
    
    The document is immediately shareable with engineering teams,
    management, and customers. Saves 2-4 hours of incident
    documentation work. Generated in under 10 seconds.
    """
    
    def generate_from_prediction(
        self,
        prediction: dict,
        anomaly_context: dict,
        similar_incidents: list[dict]
    ) -> PostMortem:
        """
        Generate complete post-mortem from AI prediction output.
        All fields populated — nothing left blank.
        """
        now_utc = datetime.now(timezone.utc)
        
        # Build timeline from precursor signals in anomaly context
        timeline = self._build_timeline(anomaly_context, now_utc)
        
        # Build prevention recommendations from remediation steps
        prevention = self._build_prevention(
            prediction.get('remediation_steps', []),
            similar_incidents
        )
        
        # Extract metrics snapshot at detection time
        metrics_snapshot = {
            signal['service'] + '/' + signal['metric']: {
                'value': signal.get('current_value'),
                'z_score': signal.get('modified_z_score'),
                'baseline': signal.get('baseline_mean'),
            }
            for signal in anomaly_context.get('signals', [])
            if 'service' in signal and 'metric' in signal
        }
        
        similar_refs = [
            f"{inc['name']} ({inc['date']}) — {inc['root_cause'][:60]}..."
            for inc in similar_incidents[:3]
        ]
        
        hypotheses = prediction.get('root_cause_hypotheses', [])
        primary_hypothesis = hypotheses[0].get('hypothesis', 'Infrastructure Anomaly') if hypotheses else 'Infrastructure Anomaly'
        
        postmortem = PostMortem(
            title=f"[PREDICTED] {primary_hypothesis[:80]}",
            generated_at=now_utc.isoformat(),
            status="PREDICTED",
            severity=prediction.get('severity', 'MEDIUM'),
            summary=(
                f"PreMortem detected anomaly precursors at "
                f"{now_utc.strftime('%H:%M UTC')} with "
                f"{prediction.get('confidence_score', 0)}% confidence. "
                f"Estimated user-visible impact in "
                f"{prediction.get('time_to_impact_minutes', '?')} minutes "
                f"if unaddressed. Automated analysis identified "
                f"{len(hypotheses)} "
                f"probable root cause hypotheses."
            ),
            detection_method=(
                "Automated — PreMortem ensemble anomaly detection "
                "(Z-Score + CUSUM + Isolation Forest) with Granger "
                "causal correlation and Groq LLaMA-3.3-70b reasoning"
            ),
            timeline=timeline,
            impact={
                "users_affected": prediction.get(
                    'blast_radius', {}
                ).get('estimated_users_impacted', 'TBD'),
                "services_directly_affected": prediction.get(
                    'blast_radius', {}
                ).get('directly_affected', []),
                "services_potentially_affected": prediction.get(
                    'blast_radius', {}
                ).get('potentially_affected', []),
                "business_impact": "Potential CI/CD pipeline "
                    "disruption for engineering teams globally"
                    if 'github' in str(anomaly_context).lower()
                    else "Service degradation for dependent systems",
            },
            root_cause=primary_hypothesis,
            contributing_factors=[
                h.get('hypothesis', '') 
                for h in hypotheses[1:4]
            ],
            remediation_steps=prediction.get('remediation_steps', []),
            prevention_recommendations=prevention,
            metrics_at_detection=metrics_snapshot,
            affected_services=prediction.get(
                'blast_radius', {}
            ).get('directly_affected', []),
            estimated_users_impacted=prediction.get(
                'blast_radius', {}
            ).get('estimated_users_impacted', 'Unknown'),
            confidence_score=prediction.get('confidence_score', 0),
            similar_past_incidents=similar_refs,
        )
        
        log.info("postmortem_generated",
                title=postmortem.title[:60],
                severity=postmortem.severity,
                confidence=postmortem.confidence_score)
        
        return postmortem
    
    def _build_timeline(
        self, anomaly_context: dict, now: datetime
    ) -> list[dict]:
        """Build chronological timeline from anomaly signals."""
        from datetime import timedelta
        
        timeline = []
        signals = sorted(
            anomaly_context.get('signals', []),
            key=lambda s: s.get('duration_seconds', 0),
            reverse=True
        )
        
        for signal in signals:
            if 'service' not in signal or 'metric' not in signal:
                continue
                
            duration = signal.get('duration_seconds', 0)
            signal_time = now - timedelta(seconds=duration)
            timeline.append({
                "time": signal_time.strftime('%H:%M:%S UTC'),
                "event": (
                    f"{signal['service']} {signal['metric']} "
                    f"elevated to {signal.get('current_value', '?')} "
                    f"({signal.get('modified_z_score', '?')}σ above baseline)"
                ),
                "severity": (
                    "CRITICAL" if signal.get('modified_z_score', 0) > 5
                    else "WARNING" if signal.get('modified_z_score', 0) > 3
                    else "INFO"
                )
            })
        
        # Add PreMortem detection event at now
        timeline.append({
            "time": now.strftime('%H:%M:%S UTC'),
            "event": "PreMortem predictive alert fired",
            "severity": "PREMORTEM_DETECTION"
        })
        
        return sorted(timeline, key=lambda e: e['time'])
    
    def _build_prevention(
        self,
        remediation_steps: list[dict],
        similar_incidents: list[dict]
    ) -> list[dict]:
        """Derive prevention recommendations from remediation + history."""
        prevention = []
        
        for step in remediation_steps[:3]:
            prevention.append({
                "priority": step.get('priority', 1),
                "recommendation": (
                    f"Automate: {step.get('action', '')}"
                ),
                "rationale": step.get('prevents', ''),
                "effort": "LOW" if step.get(
                    'estimated_time_minutes', 60
                ) < 30 else "MEDIUM",
                "type": "AUTOMATION"
            })
        
        for incident in similar_incidents[:2]:
            prevention.append({
                "priority": len(prevention) + 1,
                "recommendation": (
                    f"Based on {incident['name']} ({incident['date']}): "
                    f"add runbook for {incident['root_cause'][:60]}"
                ),
                "rationale": (
                    f"Similar incident took "
                    f"{incident['resolution_minutes']}min to resolve"
                ),
                "effort": "MEDIUM",
                "type": "RUNBOOK"
            })
        
        return prevention
    
    def to_markdown(self, pm: PostMortem) -> str:
        """Export post-mortem as formatted Markdown string."""
        lines = [
            f"# {pm.title}",
            f"",
            f"**Generated:** {pm.generated_at}  ",
            f"**Status:** {pm.status}  ",
            f"**Severity:** {pm.severity}  ",
            f"**Detection Confidence:** {pm.confidence_score}%  ",
            f"**Detection Method:** {pm.detection_method}",
            f"",
            f"## Summary",
            f"{pm.summary}",
            f"",
            f"## Impact",
            f"- **Users affected:** {pm.estimated_users_impacted}",
            f"- **Services directly affected:** "
            f"{', '.join(pm.affected_services) if pm.affected_services else 'TBD'}",
            f"",
            f"## Timeline",
        ]
        
        for event in pm.timeline:
            severity_icon = {
                "CRITICAL": "🔴",
                "WARNING": "🟡", 
                "INFO": "🔵",
                "PREMORTEM_DETECTION": "🟣"
            }.get(event['severity'], "⚪")
            lines.append(
                f"- `{event['time']}` {severity_icon} {event['event']}"
            )
        
        lines += [
            f"",
            f"## Root Cause",
            f"{pm.root_cause}",
            f"",
            f"## Contributing Factors",
        ]
        for factor in pm.contributing_factors:
            if factor:
                lines.append(f"- {factor}")
        
        lines += [f"", f"## Remediation Steps"]
        for step in pm.remediation_steps:
            lines.append(
                f"{step.get('priority', '?')}. **{step.get('action', '')}**"
            )
            if step.get('command'):
                lines.append(f"   ```\n   {step['command']}\n   ```")
        
        lines += [f"", f"## Prevention Recommendations"]
        for rec in pm.prevention_recommendations:
            lines.append(f"- [{rec['effort']}] {rec['recommendation']}")
        
        lines += [
            f"",
            f"## Similar Past Incidents",
        ]
        for ref in pm.similar_past_incidents:
            lines.append(f"- {ref}")
        
        lines += [
            f"",
            f"---",
            f"*Generated automatically by PreMortem v1.0*  ",
            f"*Detection method: ensemble anomaly detection + "
            f"Granger causal analysis + LLM reasoning*",
        ]
        
        return "\n".join(lines)
