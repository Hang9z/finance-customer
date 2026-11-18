"""
 调用物流接口
"""
from customer.config import settings
from customer.domain.state import DialogueState
from customer.actions.base import Action, ActionResult
from customer.utils.httpx_client import httpx_client


class LogisticsTracking(Action):
    name = "action_lookup_logistics"

    async def run(self, state:DialogueState) -> ActionResult:
        # 订单编号
        order_number = state.tasks.active.slots.get("order_number")
        # 拼接调用路径
        url = f"{settings.commerce_api_base_url}/orders/{order_number}/logistics"
        # httpx
        response = await httpx_client.get(url)

        # 封装数据
        data = response.json().get("data","")
        return ActionResult(
            result={
                "logistics_company":data.get("logistics_company"),
                "tracking_number":data.get("tracking_number"),
                "logistics_status":data.get("status_desc")
            }
        )