"""检索测试 API - 业务知识库问答（BM25 检索 + LLM 生成）

- chunks 索引文件：默认 backend/data/retrieval/chunks.jsonl，可用环境变量 KB_CHUNKS_PATH 覆盖
- BM25 检索在前端浏览器内完成（数据一次性加载），本路由只负责提供索引与 LLM 流式代理
- LLM 复用「模型配置」里的厂商配置，仅支持 OpenAI 兼容协议（openai/deepseek/kimi/openrouter）
"""
import json
import os

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.llm_config import ProviderConfig
from app.services import llm_service

router = APIRouter()

# OpenAI 兼容 /chat/completions 协议的厂商
OPENAI_COMPATIBLE_PROVIDERS = {"openai", "deepseek", "kimi", "openrouter"}

DEFAULT_CHUNKS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data", "retrieval", "chunks.jsonl",
)


def _chunks_path() -> str:
    return os.environ.get("KB_CHUNKS_PATH", DEFAULT_CHUNKS_PATH)


@router.get("/chunks")
async def get_chunks():
    """提供知识块索引文件（前端加载后构建 BM25 索引）"""
    path = _chunks_path()
    if not os.path.exists(path):
        raise HTTPException(404, f"chunks 索引不存在: {path}（先运行 chunk-all.mjs 生成）")
    return FileResponse(path, media_type="application/json; charset=utf-8")


class ChatMessage(BaseModel):
    role: str
    content: str


class RetrievalChatRequest(BaseModel):
    provider: str
    model: str
    messages: list[ChatMessage]
    temperature: float = 0.2


@router.post("/chat")
async def retrieval_chat(req: RetrievalChatRequest, db: AsyncSession = Depends(get_db)):
    """知识库问答的 LLM 流式代理（复用模型配置中的厂商配置）"""
    if req.provider not in OPENAI_COMPATIBLE_PROVIDERS:
        raise HTTPException(400, f"检索测试仅支持 OpenAI 兼容厂商: {', '.join(sorted(OPENAI_COMPATIBLE_PROVIDERS))}")

    result = await db.execute(
        select(ProviderConfig).where(ProviderConfig.provider == req.provider)
    )
    config = result.scalars().first()
    if not config:
        raise HTTPException(400, f"厂商 {req.provider} 尚未在「模型配置」中配置")

    url = llm_service.get_chat_url(req.provider, config.base_url, req.model)
    headers = llm_service.get_chat_headers(req.provider, config.api_key)
    payload = {
        "model": req.model,
        "messages": [m.model_dump() for m in req.messages],
        "stream": True,
        "temperature": req.temperature,
    }

    async def stream():
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                async with client.stream("POST", url, headers=headers, json=payload) as resp:
                    if resp.status_code != 200:
                        body = (await resp.aread()).decode("utf-8", "ignore")[:300]
                        yield f"data: {json.dumps({'error': f'HTTP {resp.status_code}: {body}'}, ensure_ascii=False)}\n\n"
                        return
                    async for chunk in resp.aiter_bytes():
                        yield chunk
        except httpx.HTTPError as e:
            yield f"data: {json.dumps({'error': f'LLM 调用失败: {e}'}, ensure_ascii=False)}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})
