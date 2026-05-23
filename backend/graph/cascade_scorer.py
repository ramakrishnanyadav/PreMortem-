import networkx as nx
from dataclasses import dataclass
import structlog

log = structlog.get_logger()

@dataclass
class CascadeRisk:
    origin_service: str
    blast_radius_score: float       # 0-1, total systemic risk
    directly_affected: list[str]    # 1 hop away
    potentially_affected: list[str] # 2+ hops away  
    risk_scores: dict[str, float]   # per-service risk probability
    max_cascade_depth: int
    estimated_services_at_risk: int

class CascadeScorer:
    """
    BFS traversal from anomalous origin node.
    Risk attenuates with graph distance and edge weight.
    
    Risk propagation formula:
      child_risk = parent_risk × edge_weight × DEPTH_DECAY
    
    Where:
      edge_weight = Granger causal strength (0-1)
                    or hardcoded weight for Phase 1 edges
      DEPTH_DECAY = 0.7 per hop (failures attenuate with distance)
    
    Services with blast_radius_score > 0.6 are CRITICAL.
    Services with blast_radius_score > 0.3 are WARNING.
    """
    
    DEPTH_DECAY = 0.7
    DIRECT_THRESHOLD = 0.6
    INDIRECT_THRESHOLD = 0.3
    MAX_DEPTH = 5  # prevent infinite traversal on cyclic graphs
    
    def __init__(self, graph: nx.DiGraph):
        self.graph = graph
    
    def score(self, origin_service: str) -> CascadeRisk:
        """
        Calculate cascade risk from a single origin service.
        Uses BFS with risk propagation through edge weights.
        """
        if origin_service not in self.graph:
            log.warning("cascade_origin_not_in_graph",
                       origin=origin_service)
            return CascadeRisk(
                origin_service=origin_service,
                blast_radius_score=0.0,
                directly_affected=[],
                potentially_affected=[],
                risk_scores={},
                max_cascade_depth=0,
                estimated_services_at_risk=0
            )
        
        risk_scores: dict[str, float] = {}
        visited: set[str] = {origin_service}
        queue: list[tuple[str, float, int]] = []
        
        # Seed direct neighbors with full initial risk
        for neighbor in self.graph.successors(origin_service):
            edge_data = self.graph.edges[origin_service, neighbor]
            edge_weight = edge_data.get('weight', 0.5)
            initial_risk = 1.0 * edge_weight * self.DEPTH_DECAY
            queue.append((neighbor, initial_risk, 1))
        
        max_depth_reached = 0
        
        while queue:
            service, risk, depth = queue.pop(0)
            
            if service in visited or depth > self.MAX_DEPTH:
                continue
                
            visited.add(service)
            risk_scores[service] = round(risk, 4)
            max_depth_reached = max(max_depth_reached, depth)
            
            # Propagate to successors with decay
            for neighbor in self.graph.successors(service):
                if neighbor not in visited:
                    edge_data = self.graph.edges[service, neighbor]
                    edge_weight = edge_data.get('weight', 0.5)
                    propagated_risk = risk * edge_weight * self.DEPTH_DECAY
                    
                    if propagated_risk > 0.05:  # prune negligible risk
                        queue.append((neighbor, propagated_risk, depth+1))
        
        # Classify by risk level and hop distance
        directly_affected = [
            svc for svc, score in risk_scores.items()
            if score >= self.DIRECT_THRESHOLD
        ]
        potentially_affected = [
            svc for svc, score in risk_scores.items()
            if self.INDIRECT_THRESHOLD <= score < self.DIRECT_THRESHOLD
        ]
        
        # Overall blast radius: weighted sum normalized to 0-1
        total_risk = sum(risk_scores.values())
        max_possible = len(self.graph.nodes) * 1.0
        blast_radius_score = min(1.0, total_risk / max(max_possible, 1))
        
        result = CascadeRisk(
            origin_service=origin_service,
            blast_radius_score=round(blast_radius_score, 4),
            directly_affected=directly_affected,
            potentially_affected=potentially_affected,
            risk_scores=risk_scores,
            max_cascade_depth=max_depth_reached,
            estimated_services_at_risk=len(risk_scores)
        )
        
        log.info("cascade_risk_scored",
                origin=origin_service,
                blast_radius=blast_radius_score,
                services_at_risk=len(risk_scores),
                depth=max_depth_reached)
        
        return result
    
    def score_multiple(
        self, anomalous_services: list[str]
    ) -> CascadeRisk:
        """
        Score combined blast radius for multiple simultaneous
        anomalies. Risk scores are merged with max() per service
        (not additive — prevents double-counting).
        """
        if not anomalous_services:
            return CascadeRisk("combined", 0.0, [], [], {}, 0, 0)
        
        if len(anomalous_services) == 1:
            return self.score(anomalous_services[0])
        
        individual_results = [
            self.score(svc) for svc in anomalous_services
        ]
        
        # Merge risk scores using max per service
        merged_scores: dict[str, float] = {}
        for result in individual_results:
            for svc, score in result.risk_scores.items():
                merged_scores[svc] = max(
                    merged_scores.get(svc, 0.0), score
                )
        
        all_direct = list(set(
            svc for r in individual_results 
            for svc in r.directly_affected
        ))
        all_indirect = list(set(
            svc for r in individual_results
            for svc in r.potentially_affected
            if svc not in all_direct
        ))
        
        total_risk = sum(merged_scores.values())
        max_possible = len(self.graph.nodes) * 1.0
        blast_radius = min(1.0, total_risk / max(max_possible, 1))
        
        return CascadeRisk(
            origin_service="combined_" + "+".join(anomalous_services),
            blast_radius_score=round(blast_radius, 4),
            directly_affected=all_direct,
            potentially_affected=all_indirect,
            risk_scores=merged_scores,
            max_cascade_depth=max(r.max_cascade_depth 
                                  for r in individual_results),
            estimated_services_at_risk=len(merged_scores)
        )
