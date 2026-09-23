"""Build API payloads through the shared execution field policy."""
from typing import Any, Dict, List, Optional

from .field_policy import (
    BREAKER_GROUP,
    EDITOR_ROLE,
    LOG_GROUP,
    NODE_GROUP,
    PAGE_VIEW,
    apply_field_policy,
)


def serialize_workflow(
    dag: Dict[str, Any],
    workflow_id: int,
    name: str,
    role: Optional[str] = EDITOR_ROLE,
    view: Optional[str] = PAGE_VIEW,
) -> Dict[str, Any]:
    return {
        "id": workflow_id,
        "name": name,
        "nodes": apply_field_policy(NODE_GROUP, dag["nodes"], role, view),
        "edges": [list(edge) for edge in dag["edges"]],
    }


def serialize_execution(
    *,
    nodes: List[Dict[str, Any]],
    edges: List[Any],
    logs: List[Dict[str, Any]],
    circuit_breakers: List[Dict[str, Any]],
    completed: bool,
    workflow_id: int = 1,
    workflow_name: str = "workflow",
    role: Optional[str] = EDITOR_ROLE,
    view: Optional[str] = PAGE_VIEW,
) -> Dict[str, Any]:
    workflow = serialize_workflow(
        {"nodes": nodes, "edges": edges}, workflow_id, workflow_name, role, view
    )
    return {
        "workflow": workflow,
        "logs": apply_field_policy(LOG_GROUP, logs[-30:], role, view),
        "circuitBreakers": apply_field_policy(BREAKER_GROUP, circuit_breakers, role, view),
        "completed": completed,
    }
