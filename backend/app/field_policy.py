"""Shared presentation rules for execution data.

The large screen and the regular page consume the same execution payload. Keep
the field catalogue, role visibility and masking rules here so that adding a
field or changing its scope does not require parallel implementations.
"""
from copy import deepcopy
from typing import Any, Dict, Iterable, List, Optional


SCREEN_VIEW = "screen"
PAGE_VIEW = "page"
PRESENTATION_VIEWS = (SCREEN_VIEW, PAGE_VIEW)

EDITOR_ROLE = "editor"
READONLY_ROLE = "readonly"
ROLES = (EDITOR_ROLE, READONLY_ROLE)

NODE_GROUP = "nodes"
LOG_GROUP = "logs"
BREAKER_GROUP = "circuitBreakers"

# (group, key, label, readonly_visible, sensitive)
# A new presentation field is added as one row in this catalogue. Changing its
# read-only scope or masking it is likewise a change to this single row.
_FIELD_SPEC = (
    (NODE_GROUP, "id", "任务ID", True, False),
    (NODE_GROUP, "name", "任务名称", True, False),
    (NODE_GROUP, "deps", "依赖任务", True, False),
    (NODE_GROUP, "x", "X坐标", True, False),
    (NODE_GROUP, "y", "Y坐标", True, False),
    (NODE_GROUP, "status", "状态", True, False),
    (NODE_GROUP, "startTime", "开始时间", True, False),
    (NODE_GROUP, "endTime", "结束时间", True, False),
    (NODE_GROUP, "retries", "重试次数", True, False),

    (LOG_GROUP, "taskId", "任务ID", True, False),
    (LOG_GROUP, "status", "状态", True, False),
    (LOG_GROUP, "timestamp", "时间", True, False),
    (LOG_GROUP, "message", "消息", True, False),

    (BREAKER_GROUP, "taskId", "任务ID", True, False),
    (BREAKER_GROUP, "failureCount", "失败次数", True, False),
    (BREAKER_GROUP, "state", "熔断状态", True, False),
    (BREAKER_GROUP, "cooldownUntil", "冷却截止时间", True, False),
)

FIELD_CATALOG = tuple(
    {
        "group": group,
        "key": key,
        "label": label,
        "readonlyVisible": readonly_visible,
        "sensitive": sensitive,
    }
    for group, key, label, readonly_visible, sensitive in _FIELD_SPEC
)
SENSITIVE_FIELDS = frozenset(
    (item["group"], item["key"]) for item in FIELD_CATALOG if item["sensitive"]
)

_ALLOWED_KEYS = {
    group: tuple(item["key"] for item in FIELD_CATALOG if item["group"] == group)
    for group in (NODE_GROUP, LOG_GROUP, BREAKER_GROUP)
}
_READONLY_KEYS = {
    group: tuple(
        item["key"]
        for item in FIELD_CATALOG
        if item["group"] == group and item["readonlyVisible"]
    )
    for group in (NODE_GROUP, LOG_GROUP, BREAKER_GROUP)
}


def normalize_role(role: Optional[str]) -> str:
    """Treat unknown roles conservatively as read-only members."""
    return role if role in ROLES else READONLY_ROLE


def normalize_view(view: Optional[str]) -> str:
    """Both presentation paths intentionally share the same field policy."""
    return view if view in PRESENTATION_VIEWS else PAGE_VIEW


def get_field_definitions(role: Optional[str] = EDITOR_ROLE, view: Optional[str] = PAGE_VIEW) -> List[Dict[str, Any]]:
    """Return the visible field list for a role and presentation.

    ``view`` is accepted by both paths but does not alter the result. This makes
    a refresh of either surface resolve against the same catalogue.
    """
    normalized_role = normalize_role(role)
    # Pin the view value even though both views share the same result. Callers
    # cannot accidentally fork this method by adding view-specific filtering.
    _ = normalize_view(view)
    return [
        dict(item)
        for item in FIELD_CATALOG
        if normalized_role == EDITOR_ROLE or item["readonlyVisible"]
    ]


def visible_keys(group: str, role: Optional[str] = EDITOR_ROLE) -> tuple:
    role = normalize_role(role)
    keys = _ALLOWED_KEYS.get(group, ())
    if role == EDITOR_ROLE:
        return keys
    return tuple(key for key in keys if key in _READONLY_KEYS.get(group, ()))


def is_field_visible(group: str, key: str, role: Optional[str] = EDITOR_ROLE) -> bool:
    return key in visible_keys(group, role)


def mask_value(group: str, key: str, value: Any) -> Any:
    """Mask one sensitive scalar without mutating source execution data."""
    return "******" if (group, key) in SENSITIVE_FIELDS and value is not None else value


def apply_field_policy(
    group: str,
    records: Iterable[Dict[str, Any]],
    role: Optional[str] = EDITOR_ROLE,
    view: Optional[str] = PAGE_VIEW,
) -> List[Dict[str, Any]]:
    """Project and mask records according to the shared field catalogue."""
    # All views resolve through this same method; never branch by view here.
    _ = normalize_view(view)
    keys = visible_keys(group, role)
    result = []
    for record in records:
        item = {}
        for key in keys:
            if key in record:
                value = deepcopy(record[key])
                item[key] = mask_value(group, key, value)
        result.append(item)
    return result
