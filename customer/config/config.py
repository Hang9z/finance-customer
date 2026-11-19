from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

# 获取当前文件上两层目录，找到.env文件
ENV_DIR = Path(__file__).parents[2]
ENV_FILE = ENV_DIR / '.env'

class Settings(BaseSettings):
    # 加载配置文件，读取值，赋值当前对应变量里面
    # 使用变量接受，特殊：变量名称固定的 model_config
    model_config = SettingsConfigDict(
        # 文件位置
        env_file=ENV_FILE,
        # 编码方式，中文
        env_file_encoding='utf-8',
        # 配置文件属性和类属性不一致
        extra='ignore'
    )
    # 对应配置文件，创建对应属性:类型
    LLM_MODEL: str = "@cf/zai-org/glm-4.7-flash"

    llm_api_key: str = ""
    llm_base_url: str = "https://api.cloudflare.com/client/v4/accounts/e6175ad163bd8b2ea0dad6cdd71b3a38/ai/v1"
    llm_enable_thinking: bool = False
    llm_reasoning_effort: str | None = None

    # 数据库
    database_url: str = "mysql+aiomysql://root:123456@127.0.0.1:3306/customer_service?charset=utf8mb4"
    # 商城 API
    commerce_api_base_url: str = "http://127.0.0.1:18081"
    # 金融中台 API
    finance_api_base_url: str = "http://127.0.0.1:8000/api/v1"
    finance_default_customer_no: str = "CUS00000001"
    # 服务器
    app_host: str = "0.0.0.0"
    app_port: int = 18082
    # 会话安全与鉴权
    auth_secret: str = "zhongzhou-finance-dev-secret-change-in-prod"
    auth_token_ttl_seconds: int = 7200
    auth_required: bool = False
    # Langfuse 可观测性配置
    langfuse_secret_key: str = ""
    langfuse_public_key: str = ""
    langfuse_base_url: str = "https://jp.cloud.langfuse.com"
    langfuse_enabled: bool = True
    # 金融智脑 RAG 知识库服务配置
    rag_api_base_url: str = "http://127.0.0.1:8001"
    rag_import_base_url: str = "http://127.0.0.1:8002"
    rag_enabled: bool = True
    rag_top_k: int = 10
    rag_enable_hyde: bool = True
    rag_enable_web: bool = True
    rag_timeout_seconds: float = 0.0

settings = Settings()

if __name__ == '__main__':
    print("LLM_MODEL:", settings.LLM_MODEL)
    print("LLM_BASE_URL:", settings.llm_base_url)
    print("APP_HOST:", settings.app_host)
