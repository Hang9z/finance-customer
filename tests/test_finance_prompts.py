"""金融领域 Prompt 模板与澄清策略单元测试."""
import json
from pathlib import Path
import sys
import unittest

from jinja2 import Template

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from customer.domain.state import DialogueState
from customer.handlers.clarify.clarify_response import ClarifyResponse
from customer.handlers.knowledge.intents import KNOWLEDGE_INTENTS
from customer.plan.turn_plan import ClarifyReason
from customer.prompts.loader import load_prompt

_ECOMMERCE_TERMS = ("电商", "订单", "物流", "退货", "退款", "商品", "Atguigu")


class TestFinancePromptsAndClarify(unittest.TestCase):
    """验证 Prompt 模板无电商残留且渲染正确，澄清策略已金融化."""

    def test_prompts_have_no_ecommerce_leftovers(self):
        prompt_names = (
            "turn_plan",
            "knowledge_respond",
            "chitchat_respond",
            "clarify_respond",
        )
        for name in prompt_names:
            text = load_prompt(name)
            for term in _ECOMMERCE_TERMS:
                self.assertNotIn(
                    term,
                    text,
                    f"Prompt '{name}.jinja2' still contains e-commerce term '{term}'",
                )

    def test_prompts_render_cleanly_with_jinja2(self):
        turn_plan_tpl = Template(load_prompt("turn_plan"))
        rendered_turn_plan = turn_plan_tpl.render(
            flows_json=json.dumps([{"flow_id": "account_balance_query"}], ensure_ascii=False),
            knowledge_intents_json=json.dumps(
                [{"id": k, "description": v.description} for k, v in KNOWLEDGE_INTENTS.items()],
                ensure_ascii=False,
            ),
            task_state_json="{}",
            focused_object_json="null",
            conversation_history="",
            user_message="USER: 帮我查余额",
        )
        self.assertIn("account_balance_query", rendered_turn_plan)
        self.assertIn("wealth_product_info", rendered_turn_plan)

        knowledge_tpl = Template(load_prompt("knowledge_respond"))
        rendered_knowledge = knowledge_tpl.render(
            knowledge_content="理财产品 R2 等级",
            history="",
            user_message="USER: 有什么稳健理财？",
        )
        self.assertIn("理财产品 R2 等级", rendered_knowledge)
        self.assertIn("严禁承诺", rendered_knowledge)

        chitchat_tpl = Template(load_prompt("chitchat_respond"))
        rendered_chitchat = chitchat_tpl.render(history="", user_message="USER: 你好")
        self.assertIn("金融智能客服助手", rendered_chitchat)

        clarify_tpl = Template(load_prompt("clarify_respond"))
        rendered_clarify = clarify_tpl.render(
            reason="missing_track",
            clarify_message="请问您想办理哪项金融业务？",
            focused_object=None,
            history="",
            user_message="USER: 帮我查一下",
        )
        self.assertIn("请问您想办理哪项金融业务？", rendered_clarify)

    def test_clarify_reasons_are_financial(self):
        clarify = ClarifyResponse()
        state = DialogueState(sender_id="CUST00000001")
        for reason in ClarifyReason:
            msg = clarify.build_reason(reason, state)
            self.assertTrue(msg)
            for term in _ECOMMERCE_TERMS:
                self.assertNotIn(
                    term,
                    msg,
                    f"ClarifyReason '{reason}' message contains e-commerce term '{term}': {msg}",
                )


if __name__ == "__main__":
    unittest.main()
