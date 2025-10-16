# 导入达梦数据库Python驱动
import dmPython
# 导入contextmanager装饰器，用于创建上下文管理器
from contextlib import contextmanager

# 导入os模块，用于操作环境变量
import os

@contextmanager
def get_db():
    """
    数据库连接上下文管理器，用于获取数据库游标并自动处理连接的关闭和事务回滚

    使用with语句调用此函数，可以自动管理数据库连接的生命周期，
    确保资源正确释放，即使发生异常也能妥善处理
    """
    conn = None  # 初始化数据库连接变量
    try:
        # 建立到达梦数据库的连接
        conn = dmPython.connect(
            host=os.getenv("DM_HOST"),  # 从环境变量获取数据库主机地址
            port=int(os.getenv("DM_PORT", 5236)),  # 从环境变量获取端口，默认5236
            user=os.getenv("DM_USER"),  # 从环境变量获取用户名
            password=os.getenv("DM_PASS"),  # 从环境变量获取密码
            schema=os.getenv("DM_DB")  # 从环境变量获取数据库名称
        )
        # 返回数据库游标，供with语句块中使用
        yield conn.cursor()
    except Exception as e:
        # 如果发生异常且连接已建立，则执行事务回滚
        if conn:
            conn.rollback()
        # 重新抛出异常，让上层代码处理
        raise e
    finally:
        # 无论是否发生异常，最终都要关闭数据库连接
        if conn:
            conn.close()


# 示例执行函数
def execute_query(sql: str):
    """
    执行SQL查询并返回结果

    参数:
        sql: 要执行的SQL查询语句

    返回:
        list[dict]: 查询结果列表，每个元素是一个字典，
                   键为列名，值为对应字段的值
    """
    # 使用数据库连接上下文管理器获取游标
    with get_db() as cursor:
        # 执行SQL语句
        cursor.execute(sql)
        # 获取查询结果的列名列表
        columns = [desc[0] for desc in cursor.description]
        # 获取所有查询结果行
        rows = cursor.fetchall()
        # 将每行数据与列名组合成字典，最终返回字典列表
        return [dict(zip(columns, row)) for row in rows]