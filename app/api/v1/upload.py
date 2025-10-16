
from fastapi import APIRouter, Path
from app.tasks.task_runner import start_task, stop_task, get_status
from app.core.config_loader import load_configs

configs = load_configs()
router = APIRouter(prefix="/tasks", tags=["Upload Tasks"])  # tags 便于 Swagger 分组

@router.post("/{task_id}/start")
async def start_upload_task(task_id: str = Path(..., description="任务 ID，如 user_orders")):
    """
    启动自动上传任务（循环查询 + 上传）
    """
    result = start_task(task_id,configs)  # scheduler 从 main 全局传入或依赖
    return {"status": result, "task_id": task_id, "interval": configs["interfaces"][task_id].get("interval", 300)}

@router.post("/{task_id}/stop")
async def stop_upload_task(task_id: str = Path(..., description="任务 ID")):
    """
    停止自动上传任务
    """
    result = stop_task(task_id)
    return {"status": result, "task_id": task_id}

@router.get("/{task_id}/status")
async def get_task_status(task_id: str = Path(..., description="任务 ID")):
    """
    查看任务运行状态（running/idle/stopped, last_run, errors）
    """
    return get_status(task_id)

@router.get("/ListAllTask", summary="列出所有任务及对应状态")
async def list_tasks():
    """
    列出 configs 中所有任务（task_id），并返回每个任务的详细状态
    状态包含：运行状态（running/idle/stopped/error）、最后运行时间、错误数
    """
    # 1. 从 configs 中提取所有 task_id（即 interfaces 下的所有键）
    # 防止 configs 中没有 "interfaces" 键导致报错，加 get 兜底为空字典
    all_task_ids = configs.get("interfaces", {}).keys()
    if not all_task_ids:  # 没有任何任务配置时，返回空列表
        return {
            "status": "success",
            "total": 0,
            "tasks": []
        }

    # 2. 逐个获取每个任务的状态，整理成列表
    task_list = []
    for task_id in all_task_ids:
        # 调用已有的 get_status 函数，获取单个任务状态
        task_status = get_status(task_id)
        # 给每个任务添加 task_id 字段，方便前端对应
        task_info = {
            "task_id": task_id,
            "status": task_status.get("status", "unknown"),  # 运行状态
            "last_run": task_status.get("last_run", "未执行"),  # 最后运行时间
            "errors": task_status.get("errors", 0)  # 错误数（0=无错误）
        }
        task_list.append(task_info)

    # 3. 返回最终结果（包含总数和所有任务详情）
    return {
        "status": "success",
        "total": len(task_list),  # 任务总数
        "tasks": task_list  # 每个任务的ID+状态
    }