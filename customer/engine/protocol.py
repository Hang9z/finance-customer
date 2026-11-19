"""前后端对话状态与快捷选项协议构建器."""
from typing import Any

from jinja2 import Template

from customer.domain.state import DialogueState
from customer.handlers.task.flow.models import FlowCatalog
from customer.handlers.task.flow.steps import CollectSlotStep, ConfirmFlowStep
from customer.security.masking import mask_identifier


def build_workflow_snapshot(
    state: DialogueState,
    flow_catalog: FlowCatalog,
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    """根据当前 DialogueState 与流程目录生成结构化 workflow_state 与 quick_replies."""
    quick_replies: list[dict[str, str]] = []
    active_payload: dict[str, Any] | None = None

    active = state.tasks.active
    if active is not None:
        flow = flow_catalog.flows.get(active.flow_id)
        flow_name = flow.name or active.flow_id if flow else active.flow_id
        step = flow.get_step_by_id(active.step_id) if (flow and active.step_id) else None

        awaiting: str | None = None
        awaiting_slot: str | None = None
        awaiting_question: str | None = None
        awaiting_confirmation = False
        risk_level: str | None = None

        if isinstance(step, CollectSlotStep):
            slot_meta = flow_catalog.slots.get(step.slot_name)
            awaiting = slot_meta.label if (slot_meta and slot_meta.label) else step.slot_name
            awaiting_slot = step.slot_name
            awaiting_question = step.template.text
            quick_replies = [dict(item) for item in step.quick_replies]
        elif isinstance(step, ConfirmFlowStep):
            awaiting = "确认办理"
            awaiting_slot = step.confirm_slot
            awaiting_question = Template(step.template.text).render(
                slots=active.slots,
                mask_id=mask_identifier,
            )
            awaiting_confirmation = True
            risk_level = step.risk_level
            quick_replies = [dict(item) for item in step.quick_replies]

        active_payload = {
            "flowId": active.flow_id,
            "flowName": flow_name,
            "stepId": active.step_id,
            "awaiting": awaiting,
            "awaitingSlot": awaiting_slot,
            "awaitingQuestion": awaiting_question,
            "awaitingConfirmation": awaiting_confirmation,
            "riskLevel": risk_level,
        }

    paused_list: list[dict[str, str]] = []
    for task in state.tasks.paused:
        paused_flow = flow_catalog.flows.get(task.flow_id)
        paused_name = (paused_flow.name or task.flow_id) if paused_flow else task.flow_id
        paused_list.append(
            {
                "taskId": task.task_id,
                "flowId": task.flow_id,
                "flowName": paused_name,
            }
        )

    return (
        {
            "active": active_payload,
            "paused": paused_list,
            "source": "server",
        },
        quick_replies,
    )
