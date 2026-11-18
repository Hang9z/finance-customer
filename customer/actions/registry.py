"""把远程方法注册到字典中."""
from customer.actions.base import Action


class ActionRegistry:
    def __init__(self):
        self.actions: dict[str, Action] = {}

    def register(self, action: Action):
        self.actions[action.name] = action

    def get_action(self, name: str) -> Action:
        return self.actions[name]
