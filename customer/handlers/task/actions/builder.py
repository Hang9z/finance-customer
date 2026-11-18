"""把 action 服务通过包扫描自动注册到字典中."""
import importlib
import inspect
import pkgutil

import customer.handlers.task.actions.impl as impl_pkg
from customer.handlers.task.actions.base import Action
from customer.handlers.task.actions.registry import ActionRegistry


def registry_action(registry: ActionRegistry):
    # 1. 递归扫描 impl 包下的所有子模块
    for _, module_name, _ in pkgutil.walk_packages(
        path=impl_pkg.__path__,
        prefix=f"{impl_pkg.__name__}."
    ):
        # 动态导入模块
        module = importlib.import_module(module_name)

        # 2. 遍历模块中的所有类
        for _, cls in inspect.getmembers(module, inspect.isclass):
            # 3. 严格过滤条件，防止误注册或重复注册
            if (
                cls.__module__ == module.__name__      # 必须是当前文件定义的类（过滤掉 import 进来的类）
                and issubclass(cls, Action)        # 必须是 Action 的子类
                and cls is not Action              # 排除基类本身
                and not inspect.isabstract(cls)        # 排除抽象基类 (ABC)
            ):
                registry.register(cls())
