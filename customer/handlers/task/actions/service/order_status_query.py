

"""
 调用订单查询接口
"""
from customer.config.config import settings
from customer.domain.state import DialogueState
from customer.handlers.task.actions.base import Action, ActionResult
from customer.utils.httpx_client import httpx_client


class OrderStatusQuery(Action):
    name = "action_lookup_order_status"

    async def run(self, state:DialogueState) -> ActionResult:
        order_number = state.tasks.active.slots.get("order_number")
        url = f"{settings.commerce_api_base_url}/orders/{order_number}"
        response = await httpx_client.get(url)

        data = response.json().get("data")
        return ActionResult(
            result={
                "order_status": data.get("status"),
                "order_summary": data.get("status_desc")
            }
        )