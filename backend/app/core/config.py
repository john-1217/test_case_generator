"""配置管理"""
import logging
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache

# 获取项目根目录（backend 目录）
_BACKEND_DIR = Path(__file__).parent.parent.parent.resolve()
logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    # 基础配置
    app_name: str = "Test Case Generator"
    debug: bool = False

    # 服务配置
    host: str = "0.0.0.0"
    port: int = 8080

    # JWT配置
    jwt_secret: str = "your-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 24

    # 数据库配置 - 默认使用相对路径，docker 环境可通过环境变量覆盖
    database_url: str = f"sqlite+aiosqlite:///{_BACKEND_DIR / 'data' / 'flow_test.db'}"

    # 文件配置 - 默认使用相对路径
    upload_dir: str = str(_BACKEND_DIR / "uploads")
    output_dir: str = str(_BACKEND_DIR / "outputs")
    max_file_size: int = 52428800  # 50MB

    # ChromaDB 配置
    chroma_dir: str = str(_BACKEND_DIR / "data" / "chroma")

    # 本地 HuggingFace Embedding 配置（模型路径必须由运行环境提供）
    local_embedding_enabled: bool = True
    local_embedding_model_path: str = ""
    local_embedding_device: str = "cpu"
    local_embedding_batch_size: int = 32
    local_embedding_local_files_only: bool = True

    # LangSmith 可观测性（默认关闭，且默认不上传输入输出）
    langsmith_tracing: bool = False
    langsmith_api_key: str = ""
    langsmith_project: str = "test-case-generator"
    langsmith_endpoint: str = "https://api.smith.langchain.com"
    langsmith_workspace_id: str = ""
    langsmith_hide_inputs: bool = True
    langsmith_hide_outputs: bool = True

    # 内置管理员账号
    admin_username: str = "admin"
    admin_password: str = "admin"

    # 演示模式
    demo_mode: bool = False

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


def configure_langsmith_tracing(settings: Settings) -> bool:
    """将应用配置映射为 LangChain/LangGraph 可识别的 LangSmith 环境变量。"""
    enabled = settings.langsmith_tracing and bool(settings.langsmith_api_key)
    os.environ["LANGSMITH_TRACING"] = str(enabled).lower()
    os.environ["LANGSMITH_PROJECT"] = settings.langsmith_project
    os.environ["LANGSMITH_ENDPOINT"] = settings.langsmith_endpoint
    os.environ["LANGSMITH_HIDE_INPUTS"] = str(settings.langsmith_hide_inputs).lower()
    os.environ["LANGSMITH_HIDE_OUTPUTS"] = str(settings.langsmith_hide_outputs).lower()

    if settings.langsmith_api_key:
        os.environ["LANGSMITH_API_KEY"] = settings.langsmith_api_key
    if settings.langsmith_workspace_id:
        os.environ["LANGSMITH_WORKSPACE_ID"] = settings.langsmith_workspace_id

    if settings.langsmith_tracing and not settings.langsmith_api_key:
        logger.warning("LangSmith tracing is enabled but no API key is configured; tracing is disabled")
    else:
        logger.info(
            "LangSmith tracing %s for project %s",
            "enabled" if enabled else "disabled",
            settings.langsmith_project,
        )

    return enabled


@lru_cache
def get_settings() -> Settings:
    return Settings()
