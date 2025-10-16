from fastapi import APIRouter
from app.api.v1.preview import router as preview_router

def create_router(configs: dict) -> APIRouter:
    # 目前只预览，未来加 upload
    return preview_router  # 直接返回，动态在 main 加载 configs