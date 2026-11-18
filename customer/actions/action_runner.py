"""action 调用远程服务入口."""
from customer.domain.state import DialogueState
from customer.actions.base import Action, ActionResult
from customer.actions.registry import ActionRegistry


class ActionRunner:
    def __init__(self, registry: ActionRegistry):
        self.registry = registry

    async def run(self, action_name: str, state: DialogueState) -> ActionResult:
        action_object = self.registry.get_action(action_name)
        action_result = await action_object.run(state)
        return action_result
