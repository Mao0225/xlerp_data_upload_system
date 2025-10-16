# 导入所需模块
import os
from datetime import datetime
from sched import scheduler  # 标准库调度from aps apscheduler.schedulers.asyncio import AsyncIOScheduler  # 异步任务调度器
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.core.query_builder import build_sql  # SQL构建器
from app.db.db import execute_query  # 数据库查询执行器
from app.core.uploader import upload_data  # 数据上传器
from app.core.logger import logger  # 日志工具
import redis  # Redis客户端，用于任务状态管理

# Redis客户端初始化（优先使用Redis，连接失败则使用内存字典作为降级方案）
try:
    # 尝试连接本地Redis服务（默认地址：localhost:6379，数据库编号0）
    r = redis.Redis(host=os.getenv("REDIS_HOST"), port=os.getenv("REDIS_PORT", 6379), db=0)
    r.ping()  # 测试连接是否成功
except:
    # 连接失败时，将Redis客户端设为None，后续使用内存存储
    print("Redis connection failed, using memory storage instead.")
    r = None  # 降级为内存存储

# 内存状态存储（当Redis不可用时作为备选）
tasks_status = {}  # 结构示例: {task_id: {"status": "running", "last_run": "2023-10-01T12:00:00"}}

# 全局异步调度器实例（供main.py导入并启动）
scheduler = AsyncIOScheduler()  # 移至此处定义，便于全局统一管理


async def runner(task_id: str, config: dict):
    # 新增：任务开始就记录当前时间，确保无论成败都有 last_run
    start_time = datetime.now()
    last_run = start_time.isoformat()
    error_count = 0  # 记录本次执行是否出错

    try:
        # 1. 任务开始：更新状态为“运行中”（原有逻辑不变）
        print(f"runner启动：{task_id}")
        if r:
            print(f"redis启动：{task_id}")
            r.set(f"task:{task_id}:status", "running")
        else:
            tasks_status[task_id] = {"status": "running", "last_run": last_run}

        # 2. 构建参数、生成SQL、查询数据（原有逻辑不变）
        params = {"page": 1, "limit": config["batch_size"]}
        sql = build_sql(config, params)
        rows = execute_query(sql)

        # 3. 数据校验（原有逻辑不变）
        required_fields = config.get("required_fields", [])
        valid_rows = [
            row for row in rows
            if all(row.get(field) is not None for field in required_fields)
        ]

        # 4. 上传数据（若报错，会进入 except 块）
        if valid_rows:
            await upload_data(task_id, valid_rows, config)
        print(f"{task_id} 本次执行无错误")

    except Exception as e:
        # 5. 捕获所有异常：记录错误数，更新状态为“错误”
        error_count = 1
        err_msg = f"{task_id} 执行失败：{str(e)[:100]}"  # 限制错误信息长度
        logger.error(err_msg)
        # 异常时也更新状态为“error”，方便查询时区分
        if r:
            r.set(f"task:{task_id}:status", "error")
        else:
            tasks_status[task_id]["status"] = "error"

    finally:
        # 6. 关键：无论成功/失败，都更新 last_run 和 errors（用 finally 确保执行）
        last_run = datetime.now().isoformat()  # 用任务结束时间更准确
        if r:
            # 即使报错，也写入 last_run，同时记录错误数
            r.hset(f"task:{task_id}", mapping={
                "last_run": last_run,
                "errors": error_count  # 1=本次报错，0=本次成功
            })
            # 若没报错，状态更新为“idle”；若报错，上面已设为“error”，这里不覆盖
            if error_count == 0:
                r.set(f"task:{task_id}:status", "idle")
        else:
            tasks_status[task_id]["last_run"] = last_run
            tasks_status[task_id]["errors"] = error_count

    # 记录任务周期完成日志（无论成败）
    logger.info(f"{task_id} cycle complete | 错误数：{error_count} | 最后运行：{last_run}")


def start_task(task_id: str, configs: dict):
    """
    启动指定的定时任务

    参数:
        task_id: 任务唯一标识
        scheduler: 调度器实例
        configs: 全局配置字典（包含所有任务的配置）

    返回:
        str: 启动结果状态（"already running"或"started"）
    """
    # 从全局配置中获取当前任务的详细配置
    config = configs["interfaces"][task_id]
    print("开始运行")
    # 检查任务是否已在运行（通过任务ID查询调度器中的任务）
    if scheduler.get_job(task_id):
        return "already running"  # 已在运行则返回对应状态

    # 从配置中获取任务执行间隔（默认为300秒，即5分钟）
    interval = config.get("interval", 300)

    # 向调度器添加任务：
    # - 任务函数：runner
    # - 触发器类型：interval（间隔触发）
    # - 触发间隔：interval秒
    # - 任务ID：task_id（用于后续管理）
    # - 传递给runner的参数：task_id和config
    scheduler.add_job(
        runner,
        "interval",
        seconds=interval,
        id=task_id,
        args=[task_id, config]
    )
    return "started"  # 返回启动成功状态


def stop_task(task_id: str):
    """
    停止指定的定时任务

    参数:
        task_id: 任务唯一标识
        scheduler: 调度器实例

    返回:
        str: 停止结果状态（"stopped"）
    """
    # 从调度器中移除指定ID的任务
    scheduler.remove_job(task_id)

    # 更新任务状态为"已停止"
    if r:
        r.set(f"task:{task_id}:status", "stopped")
    else:
        tasks_status[task_id] = {"status": "stopped"}

    return "stopped"  # 返回停止成功状态


def get_status(task_id: str):
    """
    获取指定任务的当前状态

    参数:
        task_id: 任务唯一标识

    返回:
        dict: 任务状态信息（包含状态、最后运行时间、错误数等）
    """
    # 检查调度器中是否存在该任务（判断是否正在运行）
    # 注：使用globals()判断scheduler是否已在全局变量中定义
    job = scheduler.get_job(task_id) if 'scheduler' in globals() else None
    # 初始状态：若任务存在则为"running"，否则为"stopped"
    status = "running" if job else "stopped"

    # 从Redis或内存中获取详细状态信息
    if r:
        # Redis模式：优先从Redis获取状态（可能更实时）
        redis_status = r.get(f"task:{task_id}:status")
        # 若Redis中有状态记录，则覆盖初始状态
        status = redis_status.decode() if redis_status else status

        # 从Redis哈希中获取最后运行时间和错误数
        last_run = r.hget(f"task:{task_id}", "last_run")
        errors = r.hget(f"task:{task_id}", "errors")

        # 构建并返回状态字典（解码Redis的字节数据为字符串）
        return {
            "status": status,
            "last_run": last_run.decode() if last_run else None,
            "errors": int(errors.decode()) if errors else 0
        }
    else:
        # 内存模式：从内存字典中获取状态（若不存在则返回初始状态）
        return tasks_status.get(task_id, {"status": status})