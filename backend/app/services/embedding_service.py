"""Embedding 服务 - 本地 HuggingFace 与远程厂商 Embedding 实例"""
import os
from functools import lru_cache
from pathlib import Path

from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings

from app.core.config import Settings, get_settings


LOCAL_HUGGINGFACE_PROVIDER = "local_huggingface"
LOCAL_HUGGINGFACE_MODEL = "BAAI/bge-small-zh-v1.5"

# 各厂商的默认 Embedding 模型和支持状态
EMBEDDING_PROVIDER_DEFAULTS = {
    LOCAL_HUGGINGFACE_PROVIDER: {
        "name": "本地 HuggingFace（无需 API Key）",
        "default_model": LOCAL_HUGGINGFACE_MODEL,
        "supported": True,
        "requires_api_key": False,
        "is_local": True,
    },
    "openai": {
        "name": "OpenAI",
        "default_model": "text-embedding-3-small",
        "supported": True,
        "requires_api_key": True,
        "is_local": False,
    },
    "gemini": {
        "name": "Gemini",
        "default_model": "text-embedding-004",
        "supported": True,
        "requires_api_key": True,
        "is_local": False,
    },
    "openrouter": {
        "name": "OpenRouter",
        "default_model": "openai/text-embedding-3-small",
        "supported": True,
        "requires_api_key": True,
        "is_local": False,
    },
    "deepseek": {
        "name": "DeepSeek",
        "default_model": "",
        "supported": False,
        "requires_api_key": True,
        "is_local": False,
    },
    "kimi": {
        "name": "Kimi",
        "default_model": "",
        "supported": False,
        "requires_api_key": True,
        "is_local": False,
    },
    "anthropic": {
        "name": "Anthropic",
        "default_model": "",
        "supported": False,
        "requires_api_key": True,
        "is_local": False,
    },
}


def is_local_embedding_provider(provider: str) -> bool:
    """判断是否为进程内运行的本地 Embedding 提供商。"""
    return provider.lower() == LOCAL_HUGGINGFACE_PROVIDER


def local_embedding_status(settings: Settings | None = None) -> tuple[bool, str]:
    """检查本地 BGE 模型是否已由运行环境显式提供。"""
    settings = settings or get_settings()
    if not settings.local_embedding_enabled:
        return False, "本地 Embedding 已禁用，请设置 LOCAL_EMBEDDING_ENABLED=true"

    model_path_value = settings.local_embedding_model_path.strip()
    if not model_path_value:
        return False, "未配置 LOCAL_EMBEDDING_MODEL_PATH；请先手动恢复 BGE 模型文件"

    model_path = Path(model_path_value).expanduser()
    if not model_path.is_dir():
        return False, f"本地 Embedding 模型目录不存在：{model_path}"
    if not os.access(model_path, os.R_OK):
        return False, f"本地 Embedding 模型目录不可读取：{model_path}"

    required_files = ("config.json", "modules.json")
    missing_files = [name for name in required_files if not (model_path / name).is_file()]
    has_weights = any((model_path / name).is_file() for name in ("model.safetensors", "pytorch_model.bin"))
    if missing_files or not has_weights:
        missing = ", ".join(missing_files + ([] if has_weights else ["model.safetensors 或 pytorch_model.bin"]))
        return False, f"本地 BGE 模型文件不完整，缺少：{missing}"

    return True, "本地 BGE 模型已就绪"


class LocalHuggingFaceEmbeddings(Embeddings):
    """使用 Sentence Transformers 在当前后端进程中运行本地 BGE 模型。"""

    def __init__(self, model_path: str, device: str, batch_size: int, local_files_only: bool):
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(
            model_name_or_path=model_path,
            device=device,
            local_files_only=local_files_only,
        )
        self._batch_size = batch_size

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors = self._model.encode(
            list(texts),
            batch_size=self._batch_size,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return [vector.tolist() for vector in vectors]

    def embed_query(self, text: str) -> list[float]:
        vector = self._model.encode(
            text,
            batch_size=self._batch_size,
            convert_to_numpy=True,
            normalize_embeddings=True,
            show_progress_bar=False,
        )
        return vector.tolist()


@lru_cache(maxsize=4)
def _get_local_embeddings(
    model_path: str,
    device: str,
    batch_size: int,
    local_files_only: bool,
) -> LocalHuggingFaceEmbeddings:
    """按不可变运行配置缓存模型，避免每次上传或检索重复加载权重。"""
    return LocalHuggingFaceEmbeddings(model_path, device, batch_size, local_files_only)


def create_embeddings(
    provider: str,
    api_key: str | None = None,
    base_url: str | None = None,
    model: str = "",
) -> Embeddings:
    """根据提供商创建 LangChain Embeddings 实例。"""
    provider = provider.lower() if provider else "openai"

    if is_local_embedding_provider(provider):
        if model != LOCAL_HUGGINGFACE_MODEL:
            raise ValueError(f"本地 Embedding 仅支持模型 {LOCAL_HUGGINGFACE_MODEL}")
        settings = get_settings()
        is_ready, message = local_embedding_status(settings)
        if not is_ready:
            raise ValueError(message)
        return _get_local_embeddings(
            settings.local_embedding_model_path,
            settings.local_embedding_device,
            settings.local_embedding_batch_size,
            settings.local_embedding_local_files_only,
        )

    if not api_key:
        raise ValueError(f"Embedding 厂商 {provider} 未配置 API Key")

    # Gemini 单独处理
    if provider == "gemini":
        try:
            from langchain_google_genai import GoogleGenerativeAIEmbeddings
            return GoogleGenerativeAIEmbeddings(
                model=model,
                google_api_key=api_key,
            )
        except ImportError:
            # 回退到 OpenAI 兼容模式
            return OpenAIEmbeddings(
                model=model,
                api_key=api_key,
                base_url=f"{(base_url or '').rstrip('/')}/v1beta/openai",
            )

    # OpenAI / OpenRouter / 其他兼容 OpenAI 格式的厂商
    kwargs = {
        "model": model,
        "api_key": api_key,
    }
    if base_url:
        kwargs["base_url"] = f"{base_url.rstrip('/')}/v1"

    return OpenAIEmbeddings(**kwargs)


def is_embedding_supported(provider: str) -> bool:
    """检查厂商是否支持 Embedding API。"""
    info = EMBEDDING_PROVIDER_DEFAULTS.get(provider.lower(), {})
    return info.get("supported", False)


def get_default_embedding_model(provider: str) -> str:
    """获取厂商默认 Embedding 模型名。"""
    info = EMBEDDING_PROVIDER_DEFAULTS.get(provider.lower(), {})
    return info.get("default_model", "")
