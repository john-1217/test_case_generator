"""API 路由"""
from fastapi import APIRouter
from app.api import auth, task, template, llm_config, knowledge, retrieval_test

router = APIRouter(prefix="/api/v1")
router.include_router(auth.router, prefix="/auth", tags=["认证"])
router.include_router(task.router, tags=["任务"])
router.include_router(template.router, prefix="/templates", tags=["模板"])
router.include_router(llm_config.router, prefix="/llm-configs", tags=["LLM配置"])
router.include_router(knowledge.router, prefix="/knowledge", tags=["知识库"])
router.include_router(retrieval_test.router, prefix="/retrieval-test", tags=["检索测试"])
