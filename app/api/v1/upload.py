from fastapi import APIRouter, Path
from app.tasks.task_runner import start_task, stop_task, get_status
from app.core.config_loader import load_configs

configs = load_configs()
router = APIRouter(prefix="/tasks", tags=["Upload Tasks"])  # tags 便于 Swagger 分组


def success_response(data=None, msg="操作成功"):
    """
    统一成功返回格式
    """
    return {
        "data": data or {},
        "code": 200,
        "msg": msg,
        "success": True
    }


def error_response(msg="操作失败", code=400):
    """
    统一失败返回格式
    """
    return {
        "data": {},
        "code": code,
        "msg": msg,
        "success": False
    }


@router.post("/{task_id}/start", summary="启动自动上传任务")
async def start_upload_task(task_id: str = Path(..., description="任务 ID，如 user_orders")):
    """
    启动自动上传任务（循环查询 + 上传）
    """
    try:
        result = start_task(task_id, configs)
        data = {
            "status": result,
            "task_id": task_id,
            "interval": configs["interfaces"][task_id].get("interval", 300)
        }
        return success_response(data, msg="任务启动成功")
    except Exception as e:
        return error_response(f"任务启动失败: {str(e)}")


@router.post("/{task_id}/stop", summary="停止自动上传任务")
async def stop_upload_task(task_id: str = Path(..., description="任务 ID")):
    """
    停止自动上传任务
    """
    try:
        result = stop_task(task_id)
        data = {
            "status": result,
            "task_id": task_id
        }
        return success_response(data, msg="任务停止成功")
    except Exception as e:
        return error_response(f"任务停止失败: {str(e)}")


@router.get("/{task_id}/status", summary="查看任务运行状态")
async def get_task_status(task_id: str = Path(..., description="任务 ID")):
    """
    查看任务运行状态（running/idle/stopped, last_run, errors）
    """
    try:
        status_info = get_status(task_id)
        return success_response(status_info, msg="查询任务状态成功")
    except Exception as e:
        return error_response(f"查询任务状态失败: {str(e)}")


@router.get("/ListAllTask", summary="列出所有任务及对应状态")
async def list_tasks():
    """
    列出 configs 中所有任务（task_id），并返回每个任务的详细状态
    状态包含：运行状态（running/idle/stopped/error）、最后运行时间、错误数
    """
    try:
        all_task_ids = configs.get("interfaces", {}).keys()
        if not all_task_ids:
            return success_response(
                {"total": 0, "tasks": []},
                msg="暂无任务配置"
            )

        task_list = []
        for task_id in all_task_ids:
            task_status = get_status(task_id)
            task_info = {
                "task_id": task_id,
                "interval": configs["interfaces"][task_id].get("interval", 300),
                "description": configs["interfaces"][task_id].get("description", "无描述"),
                "upload_url": configs["interfaces"][task_id].get("upload_url", "无上传接口"),
                "status": task_status.get("status", "unknown"),
                "last_run": task_status.get("last_run", "未执行"),
                "errors": task_status.get("errors", 0)
            }
            task_list.append(task_info)

        data = {
            "total": len(task_list),
            "tasks": task_list
        }
        return success_response(data, msg="查询成功")
    except Exception as e:
        return error_response(f"查询任务列表失败: {str(e)}")
