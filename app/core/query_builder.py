# 导入Jinja2模板引擎，用于渲染SQL模板
from jinja2 import Template
# 导入Path类，用于处理文件路径
from pathlib import Path


def build_sql(config: dict, params: dict = None) -> str:
    """
    根据配置和参数构建SQL查询语句

    参数:
        config: 包含SQL模板文件路径等配置的字典
        params: 用于渲染模板的参数字典，可选（支持动态自定义参数，从YAML schema填充默认值）

    返回:
        渲染后的SQL查询字符串
    """
    # 如果未提供参数，则初始化为空字典
    params = params or {}

    # 从配置中获取SQL模板文件名称
    template_file = config.get("sql_template_file")
    # 如果配置中没有模板文件信息，则抛出异常
    if not template_file:
        raise ValueError("配置中缺少sql_template_file")

    # 构建SQL模板文件的完整路径
    template_path = Path("configs/sql_templates") / template_file
    # 检查模板文件是否存在，如果不存在则抛出异常
    if not template_path.exists():
        raise FileNotFoundError(f"SQL模板文件不存在: {template_path}")

    # 读取模板文件内容
    with open(template_path, "r", encoding="utf-8") as f:
        template_str = f.read()

    # 准备渲染模板的参数，直接使用传入的params（已从YAML schema填充默认值）
    # 支持动态参数扩展（如filter_date, status, sort_by等）
    render_params = {
        # 如果SQL模板需要分页，确保params中有page/limit（从YAML默认）
        "page": params.get("page", 1),
        "limit": params.get("limit", 50),
        "offset": (params.get("page", 1) - 1) * params.get("limit", 50),
        # 其他动态参数直接传入
        **params
    }

    # 创建Jinja2模板对象
    template = Template(template_str)
    # 渲染模板，生成最终的SQL语句
    sql = template.render(**render_params)

    # 返回渲染后的SQL字符串，供db.py中使用dmPython执行
    return sql