"""统一的执行数据取数与字段可见范围策略。

大屏（WebSocket 实时推送）与普通页面（HTTP 明细接口）共用同一份执行数据，
字段的脱敏规则与只读成员（viewer）的可见列曾经散落在各取数路径中分头维护，
新增字段或调整范围时容易只改一处。现在所有判定只落在本模块：

* 字段目录（NODE_FIELDS / LOG_FIELDS / BREAKER_FIELDS）声明每个字段是否
  敏感（需要脱敏）以及只读成员是否可见；
* project_fields 按字段目录裁剪并脱敏一份记录；
* serialize_workflow / serialize_execution 是三条取数路径唯一的序列化入口。

默认角色为 operator（可读写成员），行为与收拢前逐字段一致，已有数据不受影响。
"""

NO_FIELDS = object()  # 表示该角色看不到该记录的任何字段

# 角色：operator 可读写成员；viewer 只读成员
ROLE_OPERATOR = "operator"
ROLE_VIEWER = "viewer"
_ROLES = (ROLE_OPERATOR, ROLE_VIEWER)

# 执行明细里的字段顺序即字段列表顺序，也是明细列的展示顺序
NODE_FIELDS = [
    # key,        sensitive, viewer_visible
    ("id",        False, True),
    ("name",      True,  True),
    ("deps",      False, True),
    ("x",         False, True),
    ("y",         False, True),
    ("status",    False, True),
    ("startTime", False, True),
    ("endTime",   False, True),
    ("retries",   False, True),
]
LOG_FIELDS = [
    ("taskId",    False, True),
    ("status",    False, True),
    ("timestamp", False, True),
    ("message",   True,  True),
]
BREAKER_FIELDS = [
    ("taskId",        False, True),
    ("failureCount",  False, True),
    ("state",         False, True),
    ("cooldownUntil", False, True),
]


def mask_value(value):
    """对敏感字段值统一脱敏：保留首尾，其余以 * 代替。"""
    if value is None:
        return None
    text = str(value)
    if len(text) <= 2:
        return "*" * len(text)
    return text[0] + "*" * (len(text) - 2) + text[-1]


def normalize_role(role):
    """未知角色一律按可读写成员处理，保证旧调用方结果不变。"""
    return role if role in _ROLES else ROLE_OPERATOR


def project_fields(record, catalog, role):
    """按字段目录输出一条记录：裁剪角色不可见列并对敏感列脱敏。

    字段不存在于 record 中时按 None 补齐，使每条记录的字段集合一致。
    """
    if not catalog:
        return NO_FIELDS
    out = {}
    for key, sensitive, viewer_visible in catalog:
        if role == ROLE_VIEWER and not viewer_visible:
            continue
        value = record.get(key)
        out[key] = mask_value(value) if sensitive and role == ROLE_VIEWER else value
    return out


def _project_list(records, catalog, role):
    result = []
    for record in records:
        projected = project_fields(record, catalog, role)
        if projected is not NO_FIELDS:
            result.append(projected)
    return result


def serialize_workflow(workflow_id, name, nodes, edges, role=ROLE_OPERATOR):
    """序列化工作流主体，取数路径共享的唯一入口。"""
    role = normalize_role(role)
    return {
        "id": workflow_id,
        "name": mask_value(name) if role == ROLE_VIEWER else name,
        "nodes": _project_list(nodes, NODE_FIELDS, role),
        "edges": [list(edge) for edge in edges],
    }


def serialize_execution(nodes, edges, logs, breakers, completed, role=ROLE_OPERATOR, workflow_id=1):
    """序列化一次执行的完整明细（HTTP 与 WebSocket 共用）。"""
    role = normalize_role(role)
    return {
        "workflow": serialize_workflow(workflow_id, "workflow", nodes, edges, role),
        "logs": _project_list(logs[-30:], LOG_FIELDS, role),
        "circuitBreakers": _project_list(breakers, BREAKER_FIELDS, role),
        "completed": completed,
    }


def serialize_creation(workflow_id, name, nodes, edges, durations, role=ROLE_OPERATOR):
    """序列化创建工作流的响应，在工作流主体上附带调度时长表。"""
    payload = serialize_workflow(workflow_id, name, nodes, edges, role)
    payload["_durations"] = dict(durations)
    return payload
