import asyncio
import os
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler  # 异步任务调度器
from app.core.query_builder import build_sql  # SQL构建器
from app.db.db import execute_query  # 数据库查询执行器
from app.core.uploader import upload_data  # 数据上传器
from app.core.logger import logger  # 日志工具
import redis  # Redis客户端，用于任务状态管理

# Redis客户端初始化（优先使用Redis，连接失败则使用内存字典作为降级方案）
try:
    r = redis.Redis(
        host=os.getenv("REDIS_HOST"),
        port=int(os.getenv("REDIS_PORT", 6379)),
        db=0
    )
    r.ping()  # 测试连接是否成功
except:
    print("Redis connection failed, using memory storage instead.")
    r = None  # 降级为内存存储

# 内存状态存储（当Redis不可用时作为备选）
tasks_status = {}  # 结构: {task_id: {"status": "running", "last_run": "...", "errors": 0}}

# 全局异步调度器实例
scheduler = AsyncIOScheduler()


async def runner(task_id: str, config: dict):
    """周期性任务的单次执行逻辑（不修改整体status，仅更新执行结果）"""
    error_count = 0
    # 状态续期参数（维持整体running状态）
    status_ttl = 60  # 状态过期时间（秒）
    renew_interval = 20  # 续期间隔（秒）
    renew_task = None

    try:
        # 1. 启动时确保整体状态为running（带过期时间，通过续期维持）
        print(f"runner启动：{task_id}")
        if r:
            r.set(f"task:{task_id}:status", "running", ex=status_ttl)
        else:
            # 内存模式：若状态不存在或为stopped，强制更新为running（避免手动停止后误启动）
            if tasks_status.get(task_id, {}).get("status") != "running":
                tasks_status[task_id] = {"status": "running", "last_run": None, "errors": 0}

        # 2. 启动续期任务：确保单次执行期间status始终为running（未过期）
        async def renew_status():
            while True:
                if r:
                    r.set(f"task:{task_id}:status", "running", ex=status_ttl)
                await asyncio.sleep(renew_interval)

        renew_task = asyncio.create_task(renew_status())

        # 3. 业务逻辑（查询、校验、上传）
        params = {"page": 1, "limit": config["batch_size"]}
        sql = build_sql(config, params)
        rows = execute_query(sql)

        required_fields = config.get("required_fields", [])
        valid_rows = [
            row for row in rows
            if all(row.get(field) is not None for field in required_fields)
        ]

        if valid_rows:
            await upload_data(task_id, valid_rows, config)

    except Exception as e:
        error_count = 1
        logger.error(f"{task_id} 执行失败：{str(e)[:100]}")

    finally:
        # 4. 单次执行结束：仅取消续期任务，不修改整体status（保持running）
        if renew_task:
            renew_task.cancel()
        # 更新最后运行时间和错误数（不影响status）
        last_run = datetime.now().isoformat()
        if r:
            r.hset(f"task:{task_id}", mapping={
                "last_run": last_run,
                "errors": error_count
            })
        else:
            # 内存模式：更新执行结果，保留status为running
            task_data = tasks_status.get(task_id, {"status": "running"})
            task_data.update({"last_run": last_run, "errors": error_count})
            tasks_status[task_id] = task_data

    logger.info(f"{task_id} cycle complete | 错误数：{error_count} | 最后运行：{last_run}")


def start_task(task_id: str, configs: dict):
    """启动定时任务（设置status为running）"""
    config = configs["interfaces"][task_id]
    if scheduler.get_job(task_id):
        return "already running"

    interval = config.get("interval", 300)
    scheduler.add_job(
        runner,
        "interval",
        seconds=interval,
        id=task_id,
        args=[task_id, config]
    )

    # 启动时强制设置status为running（无过期时间，确保初始状态正确）
    if r:
        r.set(f"task:{task_id}:status", "running")
    else:
        tasks_status[task_id] = {"status": "running", "last_run": None, "errors": 0}
    return "started"


def stop_task(task_id: str):
    """停止定时任务（设置status为stopped）"""
    if not scheduler.get_job(task_id):
        return "already stopped"

    scheduler.remove_job(task_id)
    # 停止时强制设置status为stopped（无过期时间）
    if r:
        r.set(f"task:{task_id}:status", "stopped")
    else:
        if task_id in tasks_status:
            tasks_status[task_id]["status"] = "stopped"
    return "stopped"


def get_status(task_id: str):
    """获取任务状态（status为整体状态，running表示周期性运行中）"""
    default_status = {
        "status": "stopped",
        "last_run": None,
        "errors": 0
    }

    if r:
        # 1. 获取整体status（running可能过期，不存在则视为stopped）
        status_bytes = r.get(f"task:{task_id}:status")
        status = status_bytes.decode() if status_bytes else "stopped"

        # 2. 获取执行详情
        task_info = r.hgetall(f"task:{task_id}")
        last_run = task_info.get(b"last_run", b"").decode() or None
        errors = int(task_info.get(b"errors", b"0").decode())

        return {
            "status": status,
            "last_run": last_run,
            "errors": errors
        }
    else:
        task_data = tasks_status.get(task_id, {})
        return {
            "status": task_data.get("status", default_status["status"]),
            "last_run": task_data.get("last_run", default_status["last_run"]),
            "errors": task_data.get("errors", default_status["errors"])
        }