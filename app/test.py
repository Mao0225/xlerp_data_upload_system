import asyncio
from app.db.db import execute_insert
from dotenv import load_dotenv
load_dotenv()

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


async def test_save_upload_log():
    """测试日志保存功能"""
    # 测试数据（包含特殊字符，验证转义逻辑）
    test_log_data = {
        "interfaceName": "订单上传接口",
        "interfaceDescribe": "用于上传'销售订单'数据",  # 包含单引号
        "uploadUrl": "http://api.example.com/upload/orders",
        "content": '{"order_id": "ORD123", "amount": 999}',
        "result": "成功",
        "uploadStatus": 1,  # 假设1=成功，0=失败
        "uploadStartTime": "2025-10-18 09:00:00",
        "uploadFinishTime": "2025-10-18 09:01:30"
    }

    # 执行测试
    await save_upload_log(test_log_data)
    print("测试完成")


if __name__ == "__main__":
    # 运行异步测试
    asyncio.run(test_save_upload_log())