import httpx
from datetime import datetime
from app.core.security import generate_checksum
from app.core.logger import logger
from app.db.db import execute_insert  # 数据库查询执行器
# 导入常见网络/请求异常
from httpx import ConnectError, TimeoutException, HTTPError


async def save_upload_log(log_data: dict) -> None:
    """保存上传日志到数据库（使用参数化查询）"""
    try:
        # 参数化INSERT SQL
        sql = """
            INSERT INTO sys_upload_log (
                interfaceName, interfaceDescribe, uploadUrl, 
                content, result, uploadStatus, uploadStartTime, uploadFinishTime
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        # 参数元组（顺序对应SQL中的占位符）
        params = (
            log_data['interfaceName'],
            log_data['interfaceDescribe'],
            log_data['uploadUrl'],
            log_data['content'],
            log_data['result'],
            log_data['uploadStatus'],
            log_data['uploadStartTime'],
            log_data['uploadFinishTime']
        )
        # 执行SQL（支持参数化）
        affected = execute_insert(sql, params)
        print(f"日志保存成功，受影响行数: {affected}")
    except Exception as e:
        print(f"日志保存失败：{str(e)}，日志数据：{log_data}")


async def upload_data(task_id: str, data: list, config: dict):
    """
    异步批量上传数据到外部接口
    功能：批量拆分数据+校验上传+日志记录
    """
    # 1. 提取配置并做基础校验
    try:
        url = config["upload_url"]
        headers = config["headers"]
        interface_describe = config["description"]  # 接口描述
    except KeyError as e:
        err_msg = f"{task_id} 上传配置缺失：{str(e)}（需检查 upload_url/headers/description）"
        logger.error(err_msg)
        raise ValueError(err_msg) from None

    batch_size = config.get("batch_size", 50)
    total_batches = (len(data) + batch_size - 1) // batch_size
    logger.info(f"{task_id} 开始上传：共{len(data)}条数据，分{total_batches}批，每批{batch_size}条")

    # 2. 批次上传核心逻辑
    for batch_idx in range(0, len(data), batch_size):
        batch = data[batch_idx:batch_idx + batch_size]
        current_batch_num = (batch_idx // batch_size) + 1
        batch_log_prefix = f"{task_id} [第{current_batch_num}/{total_batches}批]"

        # 生成日志ID（可根据实际情况调整，这里用时间戳+批次号确保唯一）
        log_id = int(datetime.now().timestamp() * 1000) + current_batch_num

        # 记录上传开始时间
        upload_start_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 构建请求体
        payload = [{"data": row, "checksum": generate_checksum(row)} for row in batch]
        # 上传内容（包含headers和body，转为字符串存储）
        content = f"headers: {headers}\nbody: {payload}"

        try:
            # 3. 发送请求
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    url=url,
                    json=payload,
                    headers=headers,
                    follow_redirects=True
                )
            resp.raise_for_status()

            # 4. 上传成功处理
            upload_status = 0  # 0-成功
            result = f"状态码：{resp.status_code}\n响应内容：{resp.text[:500]}"  # 限制长度
            success_msg = f"{batch_log_prefix} 上传成功，{len(batch)}条数据"
            logger.info(success_msg)
            print(success_msg)

        # 5. 异常处理（失败场景）
        except ConnectError as e:
            upload_status = 1  # 1-失败
            result = f"连接失败：无法访问 {url}（检查地址/端口/网络），错误详情：{str(e)}"
            err_msg = f"{batch_log_prefix} {result}"
            logger.error(err_msg)
            raise ValueError(err_msg) from None

        except TimeoutException as e:
            upload_status = 1
            result = f"超时失败：请求 {url} 超过10秒，错误详情：{str(e)}"
            err_msg = f"{batch_log_prefix} {result}"
            logger.error(err_msg)
            raise ValueError(err_msg) from None

        except HTTPError as e:
            upload_status = 1
            # 处理有响应的HTTP错误（如400/500）
            status_code = resp.status_code if 'resp' in locals() else '未知'
            resp_text = resp.text[:500] if 'resp' in locals() else '无响应内容'
            result = f"HTTP错误：{status_code}，响应内容：{resp_text}，错误详情：{str(e)}"
            err_msg = f"{batch_log_prefix} {result}"
            logger.error(err_msg)
            raise ValueError(err_msg) from None

        except Exception as e:
            upload_status = 1
            result = f"未知错误：{str(e)[:500]}"  # 限制错误信息长度
            err_msg = f"{batch_log_prefix} {result}"
            logger.error(err_msg)
            raise ValueError(err_msg) from None

        finally:
            # 6. 记录上传结束时间并保存日志（无论成功失败都记录）
            upload_finish_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_data = {
                "interfaceName": task_id,  # 接口名=task_id
                "interfaceDescribe": interface_describe,  # 从config取描述
                "uploadUrl": url,
                "content": content,  # 包含headers和body
                "result": result,  # 响应结果或错误信息
                "uploadStatus": upload_status,  # 0成功/1失败
                "uploadStartTime": upload_start_time,
                "uploadFinishTime": upload_finish_time
            }
            # 异步保存日志（不阻塞主流程）
            await save_upload_log(log_data)