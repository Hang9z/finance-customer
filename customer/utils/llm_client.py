import sys
from pathlib import Path
from typing import Any

# 保证以脚本形式直接运行当前文件时，能正常找到项目根目录模块
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel

from customer.config.config import settings

_llm_kwargs: dict[str, Any] = {
    "model": settings.LLM_MODEL,
    "model_provider": "openai",
    "api_key": settings.llm_api_key,
    "base_url": settings.llm_base_url,
    "temperature": 0,
}
if settings.llm_reasoning_effort:
    _llm_kwargs["reasoning_effort"] = settings.llm_reasoning_effort
if settings.llm_enable_thinking:
    _llm_kwargs["extra_body"] = {"thinking": {"type": "enabled"}}

# 创建 llm 对象 (兼容 DeepSeek / Cloudflare Workers AI 等 OpenAI 协议服务)
llm: BaseChatModel = init_chat_model(**_llm_kwargs)

if __name__ == "__main__":
    print("=" * 60)
    print("【LLM 客户端配置检测】")
    print(f"模型名称: {settings.LLM_MODEL}")
    print(f"端点地址: {settings.llm_base_url}")
    print(f"深度思考: {settings.llm_enable_thinking} (effort={settings.llm_reasoning_effort})")
    masked_key = (
        f"{settings.llm_api_key[:6]}...{settings.llm_api_key[-4:]}"
        if len(settings.llm_api_key) > 10
        else (settings.llm_api_key or "未设置")
    )
    print(f"API Key : {masked_key}")
    print("=" * 60)

    if not settings.llm_api_key or settings.llm_api_key.startswith("your_"):
        print("\n提示: 当前尚未配置有效的 LLM API Key，请在 .env 文件中配置 LLM_API_KEY。")
    else:
        print("\n正在发送 LLM 连通性测试请求...")
        try:
            response = llm.invoke("请只回复两个字：正常")
            print("\n【模型回答】:")
            print(response.content)
            print("\n测试调用成功！")
        except Exception as e:
            print(f"\n调用异常: {e}")
