import asyncio
from httpx import AsyncClient

# 定义变量
httpx_client: AsyncClient | None = None

# 初始化方法
def init_httpx_client():
    global httpx_client
    httpx_client = AsyncClient(timeout=30.0, trust_env=False)

# 关闭的方法
async def close_httpx_client():
    if httpx_client is not None:
        await httpx_client.aclose()

# 测试调用的方法
async def test():
    init_httpx_client()
    try:
        response = await httpx_client.get(
            url="http://127.0.0.1:18081/users/u1001/orders")
        print(response.json())
    finally:
        await close_httpx_client()

if __name__ == "__main__":
    asyncio.run(test())
