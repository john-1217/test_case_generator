"""FastAPI 主入口"""
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.core.config import configure_langsmith_tracing, get_settings

settings = get_settings()
configure_langsmith_tracing(settings)

from app.api import router
from app.core.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化数据库
    await init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    lifespan=lifespan,
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}


class SPAStaticFiles(StaticFiles):
    """Serve existing assets normally and fall back to index.html for SPA routes."""

    async def get_response(self, path: str, scope):
        try:
            response = await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code != 404 or Path(path).suffix or path.startswith("api/"):
                raise
            return await super().get_response("index.html", scope)

        if (
            response.status_code == 404
            and not Path(path).suffix
            and not path.startswith("api/")
        ):
            return await super().get_response("index.html", scope)
        return response


# 挂载前端静态文件（仅在 Docker 容器中存在）
STATIC_DIR = Path(__file__).parent.parent.parent / "static"
if STATIC_DIR.exists():
    app.mount("/", SPAStaticFiles(directory=str(STATIC_DIR), html=True), name="static")
