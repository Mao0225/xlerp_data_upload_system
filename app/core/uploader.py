import httpx
from app.core.security import generate_checksum
from app.core.logger import logger
# 导入常见网络/请求异常，避免捕获所有Exception导致日志冗余
from httpx import ConnectError, TimeoutException, HTTPError


async def upload_data(task_id: str, data: list, config: dict):
    """
    异步批量上传数据到外部接口
    功能：批量拆分数据+校验上传，错误时输出精简日志，仅关键异常向上抛出
    """
    # 1. 提取配置并做基础校验（提前拦截配置错误，避免后续白跑）
    try:
        url = config["upload_url"]
        headers = config["headers"]
    except KeyError as e:
        # 配置缺失属于致命错误，日志明确提示，直接抛出
        err_msg = f"{task_id} 上传配置缺失：{str(e)}（需检查 upload_url/headers）"
        logger.error(err_msg)
        raise ValueError(err_msg) from None  # from None 避免打印冗余的KeyError堆栈

    batch_size = config.get("batch_size", 50)
    total_batches = (len(data) + batch_size - 1) // batch_size  # 计算总批次，方便日志追踪
    logger.info(f"{task_id} 开始上传：共{len(data)}条数据，分{total_batches}批，每批{batch_size}条")

    # 2. 批次上传核心逻辑
    for batch_idx in range(0, len(data), batch_size):
        batch = data[batch_idx:batch_idx + batch_size]
        current_batch_num = (batch_idx // batch_size) + 1  # 批次号（从1开始，更直观）
        batch_log_prefix = f"{task_id} [第{current_batch_num}/{total_batches}批]"

        # 构建请求体（保持原有逻辑）
        payload = [{"data": row, "checksum": generate_checksum(row)} for row in batch]

        try:
            # 3. 发送请求（仅捕获常见的请求相关异常，避免捕获所有Exception）
            async with httpx.AsyncClient(timeout=10.0) as client:  # 加超时，避免无限等待
                resp = await client.post(
                    url=url,
                    json=payload,
                    headers=headers,
                    follow_redirects=True  # 自动处理3xx重定向，减少不必要错误
                )

            # 4. 响应状态校验（仅200-299视为成功，兼容更多成功状态码）
            resp.raise_for_status()  # httpx内置方法：非2xx直接抛HTTPError，不用手动判断

            # 5. 上传成功：精简日志（只打关键信息）
            success_msg = f"{batch_log_prefix} 上传成功，{len(batch)}条数据"
            logger.info(success_msg)
            print(success_msg)  # 控制台打印也精简

        # 6. 分类捕获异常：不同错误不同提示，避免日志混乱
        except ConnectError:
            err_msg = f"{batch_log_prefix} 连接失败：无法访问 {url}（检查地址/端口/网络）"
            logger.error(err_msg)
            raise ValueError(err_msg) from None  # 抛自定义异常，隐藏底层复杂堆栈

        except TimeoutException:
            err_msg = f"{batch_log_prefix} 超时失败：请求 {url} 超过10秒（检查接口响应速度）"
            logger.error(err_msg)
            raise ValueError(err_msg) from None

        except HTTPError as e:
            # 处理HTTP错误（如404/500）：提取关键信息，不打印完整堆栈
            err_msg = f"{batch_log_prefix} HTTP错误：{resp.status_code} - {resp.text[:200]}..."  # 只取前200字符，避免日志过长
            logger.error(err_msg)
            raise ValueError(err_msg) from None

        except Exception as e:
            # 其他意外错误：只打关键信息，不扩散堆栈
            err_msg = f"{batch_log_prefix} 未知错误：{str(e)[:100]}"  # 限制错误信息长度
            logger.error(err_msg)
            raise ValueError(err_msg) from None