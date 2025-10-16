import yaml  # 用于解析 YAML 格式的配置文件（YAML是常用的配置文件格式，比JSON更易读）
from pathlib import Path  # 用于处理文件路径（跨系统兼容，比os.path更简洁）


def load_configs() -> dict:
    """
    加载并处理任务配置文件（configs/interfaces.yaml）
    核心功能：
    1. 读取YAML配置文件，验证文件是否存在
    2. 提取"interfaces"节点下的所有任务配置
    3. 把原始的"query_params"列表，转换成便于代码使用的"param_schema"字典
    4. 验证每个任务配置的必填字段（如sql_template_file）
    返回：
        dict: 结构化的配置字典，格式为 {"interfaces": {任务ID: 处理后的任务配置, ...}}
    """
    # 1. 定义配置文件的路径（相对路径：项目根目录下的 configs 文件夹 → interfaces.yaml 文件）
    # Path() 会自动适配 Windows/macOS/Linux 的路径分隔符（如\和/），避免跨系统路径错误
    yaml_path = Path("configs/interfaces.yaml")

    # 2. 检查配置文件是否存在，不存在则抛出明确错误（方便定位问题）
    if not yaml_path.exists():
        # FileNotFoundError 是Python内置异常，这里添加具体文件路径，让报错更清晰
        raise FileNotFoundError("配置文件不存在：configs/interfaces.yaml not found")

    # 3. 打开并读取YAML文件，解析成Python字典
    # with open(...)：自动管理文件流，读取完后自动关闭，避免文件句柄泄漏
    # encoding="utf-8"：指定编码格式，防止中文等特殊字符乱码
    # yaml.safe_load(f)：安全解析YAML文件，只解析标准YAML语法，避免执行恶意代码（比yaml.load更安全）
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)  # data 是解析后的原始配置字典（包含"interfaces"节点）

    # 4. 提取"interfaces"节点的配置，若没有则默认是空字典（避免后续代码报KeyError）
    # data.get("interfaces", {})：如果data里有"interfaces"键，取它的值；没有则返回空字典
    interfaces = data.get("interfaces", {})

    # 5. 遍历每个任务配置，处理"query_params"（核心格式转换逻辑）
    # interfaces.items()：遍历"interfaces"下的所有任务（key=任务ID，value=原始任务配置）
    for task_name, task_config in interfaces.items():
        # 5.1 提取当前任务的"query_params"（查询参数配置，如分页参数page/limit、筛选参数status等）
        # 若任务没有配置query_params，默认是空列表
        query_params = task_config.get("query_params", [])

        # 5.2 验证"query_params"的格式：必须是列表（防止配置写错成字典等其他类型）
        if not isinstance(query_params, list):
            # 抛出 ValueError 异常，明确指出哪个任务的配置有误
            raise ValueError(f"任务 {task_name} 的 query_params 格式错误：必须是列表（list）类型")

        # 5.3 把"query_params"列表转换成"param_schema"字典（便于后续代码使用）
        # 原始列表格式（配置文件中）：[{"name": "page", "type": "int", "default": 1}, ...]
        # 目标字典格式（代码中用）：{"page": {"type": "int", "default": 1, ...}, ...}
        param_schema = {}  # 初始化转换后的参数字典
        for param in query_params:  # 遍历每个查询参数
            # 5.3.1 验证单个参数的必填字段：必须包含"name"（参数名）和"type"（参数类型）
            if not all(key in param for key in ["name", "type"]):
                raise ValueError(f"任务 {task_name} 的 query_params 配置错误：参数缺少 'name' 或 'type'")

            # 5.3.2 把当前参数的信息整理到param_schema中
            # param.get(键, 默认值)：获取参数的配置，没有则用默认值（保证字段不缺失）
            param_schema[param["name"]] = {
                "type": param.get("type", "str"),  # 参数类型（如int/str，默认是字符串）
                "default": param.get("default"),  # 参数默认值（没有则为None）
                "required": param.get("required", False),  # 是否必填（默认非必填）
                "description": param.get("description", "")  # 参数描述（默认空字符串）
            }

        # 5.4 把转换后的"param_schema"添加到当前任务的配置中（后续代码可直接用 task_config["param_schema"]）
        task_config["param_schema"] = param_schema

        # 6. 验证当前任务的必填配置：必须包含"sql_template_file"（SQL模板文件路径，用于生成查询SQL）
        # 若没有这个配置，说明任务无法生成SQL，直接抛出错误
        if "sql_template_file" not in task_config:
            raise ValueError(f"任务 {task_name} 配置缺失：缺少必填项 'sql_template_file'（SQL模板文件路径）")

    # 7. 函数最终返回结构化的配置字典：外层键是"interfaces"，值是所有处理后的任务配置
    # 这样调用方（如start_task函数）就能通过 configs["interfaces"][任务ID] 拿到对应任务的配置
    return {"interfaces": interfaces}