from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from contextlib import asynccontextmanager  # 导入 lifespan 依赖
from core.config_loader import load_configs
from api.v1.preview import router as preview_router
from api.v1.upload import router as upload_router
from tasks.task_runner import scheduler  # 全局调度器

# 1. 先加载环境变量
load_dotenv()


# ------------------------------
# 关键：用 lifespan 管理应用生命周期（替代 on_event）
# ------------------------------
# 修改 main.py 的 lifespan 函数
@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.tasks.task_runner import scheduler  # 确保导入全局调度器
    import asyncio

    # 关键：手动将调度器绑定到当前运行的事件循环
    if not scheduler.running:
        scheduler.configure(event_loop=asyncio.get_running_loop())  # 绑定循环
        scheduler.start()
        print("调度器已启动，绑定事件循环")

    yield  # 应用运行阶段

    # 关闭阶段
    if scheduler.running:
        scheduler.shutdown()
        print("调度器已停止")


# 2. 初始化 FastAPI 时，指定 lifespan 参数
app = FastAPI(
    title="数据上传平台",
    lifespan=lifespan  # 绑定生命周期管理器
)

# 3. 配置 CORS（不变）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. 加载配置（不变）
configs = load_configs()

# 5. 注册路由（不变）
app.include_router(preview_router, prefix="/v1")
app.include_router(upload_router, prefix="/v1")

# 6. 启动服务（不变）
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)