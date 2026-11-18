"""
 把远程方法注册到字典中
"""
from customer.handlers.task.actions.base import Action


class ActionRegistry:
    def __init__(self):
        self.actions: dict[str, Action] = {}

    # 注册 action
    def register(self, action: Action):
        self.actions[action.name] = action

    # 根据 step 中的 name 获取 action
    def get_action(self, name: str) -> Action:
        return self.actions[name]