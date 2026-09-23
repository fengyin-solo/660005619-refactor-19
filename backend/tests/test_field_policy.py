import unittest

from app.execution_presenter import serialize_execution, serialize_workflow
from app.field_policy import (
    EDITOR_ROLE,
    PAGE_VIEW,
    READONLY_ROLE,
    SCREEN_VIEW,
    apply_field_policy,
    get_field_definitions,
    visible_keys,
)


class FieldPolicyTest(unittest.TestCase):
    def test_screen_and_page_share_one_field_list_per_role(self):
        for role in (EDITOR_ROLE, READONLY_ROLE):
            self.assertEqual(
                get_field_definitions(role, SCREEN_VIEW),
                get_field_definitions(role, PAGE_VIEW),
            )

    def test_default_role_and_unknown_role_are_safe(self):
        default_fields = get_field_definitions()
        self.assertEqual(default_fields, get_field_definitions(EDITOR_ROLE))
        self.assertEqual(
            get_field_definitions("unknown", SCREEN_VIEW),
            get_field_definitions(READONLY_ROLE, PAGE_VIEW),
        )

    def test_current_execution_payloads_remain_identical_across_views_and_roles(self):
        dag = {
            "nodes": [{
                "id": "extract",
                "name": "数据提取",
                "deps": [],
                "x": 2.5,
                "y": 0.0,
                "status": "PENDING",
                "startTime": None,
                "endTime": None,
                "retries": 0,
            }],
            "edges": [],
        }

        logs = [{"taskId": "extract", "status": "RUNNING", "timestamp": 1.0, "message": "开始"}]
        breakers = [{"taskId": "extract", "failureCount": 0, "state": "CLOSED", "cooldownUntil": 0}]

        for view in (SCREEN_VIEW, PAGE_VIEW):
            self.assertEqual(
                serialize_workflow(dag, 1, "workflow", READONLY_ROLE, view),
                serialize_workflow(dag, 1, "workflow", EDITOR_ROLE, view),
            )
            self.assertEqual(
                serialize_execution(
                    nodes=dag["nodes"],
                    edges=dag["edges"],
                    logs=logs,
                    circuit_breakers=breakers,
                    completed=False,
                    role=READONLY_ROLE,
                    view=view,
                ),
                serialize_execution(
                    nodes=dag["nodes"],
                    edges=dag["edges"],
                    logs=logs,
                    circuit_breakers=breakers,
                    completed=False,
                    role=EDITOR_ROLE,
                    view=view,
                ),
            )

    def test_policy_only_returns_registered_fields_for_a_group(self):
        record = {"taskId": "extract", "status": "SUCCESS", "internal": "secret"}
        result = apply_field_policy("logs", [record], READONLY_ROLE)

        self.assertEqual(result, [{"taskId": "extract", "status": "SUCCESS"}])
        self.assertEqual(record["internal"], "secret")

    def test_presenter_keeps_existing_payload_shape_and_source_data(self):
        dag = {
            "nodes": [{
                "id": "extract",
                "name": "数据提取",
                "deps": [],
                "x": 2.5,
                "y": 0.0,
                "status": "SUCCESS",
                "startTime": 1.0,
                "endTime": 3.0,
                "retries": 0,
            }],
            "edges": [["extract", "validate"]],
        }
        logs = [{
            "taskId": "extract",
            "status": "SUCCESS",
            "timestamp": 3.0,
            "message": "完成",
        }]
        breakers = [{
            "taskId": "extract",
            "failureCount": 0,
            "state": "CLOSED",
            "cooldownUntil": 0,
        }]

        workflow = serialize_workflow(dag, 1, "workflow")
        execution = serialize_execution(
            nodes=dag["nodes"],
            edges=dag["edges"],
            logs=logs,
            circuit_breakers=breakers,
            completed=True,
        )

        self.assertEqual(workflow, {
            "id": 1,
            "name": "workflow",
            "nodes": dag["nodes"],
            "edges": [["extract", "validate"]],
        })
        self.assertEqual(execution, {
            "workflow": workflow,
            "logs": logs,
            "circuitBreakers": breakers,
            "completed": True,
        })
        self.assertEqual(visible_keys("nodes"), tuple(dag["nodes"][0].keys()))
        self.assertEqual(visible_keys("logs"), tuple(logs[0].keys()))
        self.assertEqual(visible_keys("circuitBreakers"), tuple(breakers[0].keys()))


if __name__ == "__main__":
    unittest.main()
