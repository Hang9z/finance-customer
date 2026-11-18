import sys
from pathlib import Path

# 保证以脚本形式直接运行当前文件时，能正常找到项目根目录模块
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel

from customer.config.config import settings

# 创建llm对象 (基于 OpenAI 兼容协议连接 Cloudflare Workers AI)
llm: BaseChatModel = init_chat_model(
    model=settings.LLM_MODEL,
    model_provider="openai",
    api_key=settings.llm_api_key,
    base_url=settings.llm_base_url,
    temperature=0,
)

if __name__ == "__main__":
    print("=" * 60)
    print("【LLM 客户端配置检测】")
    print(f"模型名称: {settings.LLM_MODEL}")
    print(f"端点地址: {settings.llm_base_url}")
    masked_key = (
        f"{settings.llm_api_key[:6]}...{settings.llm_api_key[-4:]}"
        if len(settings.llm_api_key) > 10
        else (settings.llm_api_key or "未设置")
    )
    print(f"API Key : {masked_key}")
    print("=" * 60)

    if not settings.llm_api_key or settings.llm_api_key == "your_cloudflare_api_token_here":
        print("\n提示: 当前尚未配置有效的 Cloudflare API Token。")
        print("请在项目根目录的 .env 文件中配置 LLM_API_KEY：")
        print("  1. 前往 Cloudflare 官网: My Profile → API Tokens")
        print("  2. 创建带有 Account → Workers AI → Read 权限的令牌")
        print("  3. 将令牌填写到 .env 的 LLM_API_KEY 中即可完成调用测试。\n")
    else:
        print("\n正在向 Cloudflare Workers AI 发送测试请求...")
        try:
            response = llm.invoke("用一句话介绍 Cloudflare")
            print("\n【模型回答】:")
            print(response.content)
            print("\n测试调用成功！")
        except Exception as e:
            print(f"\n调用异常: {e}")
            print("\n请排查:")
            print("1. API Token 是否具备 Workers AI -> Read 权限")
            print("2. 账户 ID (e6175ad163bd8b2ea0dad6cdd71b3a38) 是否匹配该 Token")