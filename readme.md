# 数据上传平台 - FastAPI 项目 README

## 项目概述

**项目名称**：数据上传平台 (Data Upload System)  
**版本**：1.0.0  
**创建日期**：2025 年 10 月 17 日  
**描述**：这是一个基于 FastAPI 的 Web 平台，用于从达梦 (DM) 数据库查询多表联合数据（支持 JOIN、重命名字段），预览数据列表，并自动循环上传到外部接口。平台采用配置驱动设计（YAML + SQL 模板），支持动态参数验证、批量上传、实时任务控制。适用于单人开发场景，高效处理 40-50 个表/接口的复杂数据同步需求。

### 核心功能
- **数据预览**：通过 `/v1/preview/{interface_name}` 接口执行 YAML 配置的 SQL 模板，返回分页数据列表（支持模糊查询、日期过滤、分页）。
- **自动上传**：循环脚本（APScheduler 调度），每 N 秒查询 DM 数据，批量 POST 到外部 URL，支持加密头、校验码、失败回滚。
- **任务控制**：通过 `/v1/tasks/{task_id}` 接口启动/停止/查看状态，支持多类型任务（不同 SQL + URL）。
- **配置驱动**：SQL、参数、上传 URL 等统一在 `configs/interfaces.yaml` 中定义，便于扩展/维护。
- **安全性/完整性**：必填字段校验、HMAC 校验码、AES 加密，符合 GB/T 22239 标准。
- **实时性**：异步查询/上传，支持参数化过滤和状态监控（Redis）。

项目聚焦数据完整性（回滚 + 日志）、正确性（校验码 + 版本一致）、安全性（加密 + 头验证）、传输实时性（异步批量）和扩展性（YAML 版本管理）。

## 技术栈
- **后端**：FastAPI (ASGI), Python 3.12+
- **数据库**：dmPython (DM 驱动，直接 raw SQL)
- **配置**：PyYAML (YAML 解析), Jinja2 (SQL 模板渲染)
- **上传**：httpx (异步 HTTP POST)
- **调度**：APScheduler (循环任务)
- **状态**：Redis (实时状态，fallback 内存/文件)
- **验证**：Pydantic (动态参数模型)
- **日志**：Python logging (控制台/文件)

## 项目文件结构

```
project/                  # 项目根目录
├── app/                  # 主应用包 (FastAPI 核心逻辑)
│   ├── __init__.py       # 空文件，标记为 Python 包
│   ├── main.py           # 启动入口：加载配置、启动调度器、include 路由 (preview + upload)
│   ├── core/             # 核心工具模块 (通用函数)
│   │   ├── __init__.py   # 空文件
│   │   ├── config_loader.py  # YAML 加载 + query_params 转为 param_schema (dict 验证)
│   │   ├── query_builder.py  # SQL 构建：Jinja 渲染 .sql 模板 (支持动态参数)
│   │   ├── uploader.py   # 上传逻辑：httpx POST 到外部 URL，批量 + 校验 + 回滚
│   │   ├── security.py   # 安全：生成校验码 (HMAC) + 加密 (AES 等)
│   │   └── logger.py     # 日志管理：记录操作/错误/回滚 (logging 到文件/控制台)
│   ├── models/           # Pydantic 数据模型 (验证/序列化)
│   │   ├── __init__.py   # 空文件
│   │   ├── base_source.py  # 源数据模型：动态字段 (extra=allow，用于查询结果)
│   │   └── base_target.py  # 目标数据模型：上传格式 + 必填校验
│   ├── api/              # API 路由模块
│   │   ├── __init__.py   # 空文件
│   │   └── v1/           # v1 版本路由 (易扩展 v2)
│   │       ├── __init__.py  # 空文件
│   │       ├── preview.py   # 预览端点：/v1/preview/{name} (动态参数 + Swagger 输入框)
│   │       └── upload.py    # 任务控制端点：/v1/tasks/{task_id}/start/stop/status/list
│   ├── db/               # 数据库模块
│   │   ├── __init__.py   # 空文件
│   │   └── db.py         # DM 连接：dmPython get_db 上下文 + execute_query (raw SQL)
│   └── tasks/            # 自动上传脚本模块
│       ├── __init__.py   # 空文件
│       └── task_runner.py  # 循环 runner：APScheduler 调度 + 状态更新 (Redis/内存)
├── configs/              # 配置目录
│   ├── __init__.py       # 空文件
│   ├── interfaces.yaml   # 主 YAML：接口定义 (SQL 文件、参数、上传 URL、间隔等)
│   └── sql_templates/    # SQL 模板目录
│       └── user_orders.sql  # 示例：完整 SQL (JOIN/AS + Jinja {{ }} 参数)
├── requirements.txt      # Python 依赖列表
├── .env                  # 环境变量 (DM/Redis/密钥)
└── README.md             # 本文件：项目文档
```

- **作用总结**：
  - `app/core/`：通用工具，避免重复 (加载/构建/上传/安全/日志)。
  - `app/api/v1/`：REST 端点 (预览数据 + 任务控制)。
  - `app/tasks/`：后台循环执行 (查询 + 上传)。
  - `configs/`：集中配置，改 YAML 全局生效。
  - `app/db/`：DM 专用连接/执行。

## 安装与依赖

### 环境准备
1. **Python 环境**：推荐 Python 3.12+，创建虚拟环境。
   ```
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   ```

2. **安装依赖**：
   ```
   pip install -r requirements.txt
   ```
   **requirements.txt 内容**：
   ```
   fastapi==0.104.1
   uvicorn[standard]==0.24.0
   dmPython  # DM 驱动 (达梦官网下载安装)
   pyyaml==6.0.1
   jinja2==3.1.2
   httpx==0.25.2
   cryptography==41.0.7  # 加密
   pydantic==2.5.0
   python-dotenv==1.0.0
   apscheduler==3.10.4  # 任务调度
   redis==5.0.1  # 状态管理 (可选)
   ```

3. **达梦数据库**：确保 DM 服务运行，准备测试表 (users, orders 等)。

### 配置环境变量 (.env)
```
DM_HOST=127.0.0.1
DM_PORT=5236
DM_USER=SYSDBA
DM_PASS=SYSDBA
DM_DB=TESTDB
SECRET_KEY=your_secret_key_for_encryption
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

### 数据库准备示例
```sql
-- 测试表
CREATE TABLE users (id INT PRIMARY KEY, name VARCHAR(50));
INSERT INTO users VALUES (1, 'Alice'), (2, 'Bob');
CREATE TABLE orders (id INT, user_id INT, total DECIMAL(10,2), date DATE, status VARCHAR(20));
INSERT INTO orders VALUES (1, 1, 100.00, DATE '2025-10-15', 'paid');
```

## 启动与运行

1. **启动服务器**：
   ```
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```
   - `--reload`：开发模式，改 YAML/SQL 自动重载。
   - 访问 http://localhost:8000/docs (Swagger UI 测试 API)。

2. **Redis 服务**（状态管理）：
   - 本地：`redis-server` (或 Docker: `docker run -p 6379 redis`)。
   - 无 Redis：自动 fallback 内存 (重启丢失状态)。

3. **首次验证**：
   - 预览：GET /v1/preview/user_orders?filter_date=2025-10-16&name=Alice&page=1&limit=10。
   - 任务：POST /v1/tasks/user_orders/start → GET /v1/tasks/user_orders/status。

## 配置详解

### interfaces.yaml (configs/interfaces.yaml)
核心配置文件，定义接口类型（多表上传）。每个块一个接口（e.g., user_orders）。
```yaml
interfaces:
  user_orders:  # 接口 ID (任务 ID)
    sql_template_file: "user_orders.sql"  # SQL 模板路径
    required_fields: []  # 必填字段列表 (完整性过滤)
    preview_fields: []  # 预览显示字段 (空=返回所有)
    batch_size: 50  # 批量上传大小
    upload_url: "https://external.com/api/user_orders"  # 外部上传地址
    headers:  # 请求头 (认证/加密)
      Authorization: "Bearer your_token"
      Content-Type: "application/json"
      X-Version: "1.0"
    interval: 300  # 循环间隔 (秒，0=手动触发)
    query_params:  # 查询参数 (预览/上传过滤)
      - name: name
        type: str
        default: ""
        required: false
        description: "名称模糊查询"
      - name: filter_date
        type: date
        default: "2025-10-16"
        required: false
        description: "日期过滤 YYYY-MM-DD"
      - name: page
        type: int
        default: 1
        required: false
        description: "分页页码"
      - name: limit
        type: int
        default: 50
        required: false
        description: "每页条数"
  # 加新接口：复制块，改 ID + sql_template_file
```

### sql_templates/ 示例 (user_orders.sql) ---jinja格式
```
SELECT u.id AS api_user_id, u.name AS api_username, o.total AS api_amount
FROM users u JOIN orders o ON u.id = o.user_id
WHERE o.date > '{{ filter_date }}'
  AND u.name LIKE '%{{ name }}%'  # 模糊查询 (Jinja 条件)
{% if name %} AND u.name LIKE '%{{ name }}%' {% endif %}
ORDER BY u.id
LIMIT {{ limit }} OFFSET {{ offset }}
```
- **Jinja 支持**：`{{ param }}` 替换、`{% if param != '' %}` 条件。

## API 可视化网页
Swagger UI：http://localhost:8000/docs (交互测试，点击 Execute)。

### 预览端点 (/v1/preview)
- **GET /v1/preview/{interface_name}**：预览数据 (分页/过滤)。
  - 参数：interface_name (路径，e.g., user_orders), filter_date (str, 示例 2025-10-16), page (int ≥1), limit (int ≤100), name (str, 动态模糊)。
  - 返回：{"data": [dicts], "total": int, "page": int, "limit": int, "sql_used": str}。
  - 示例：/v1/preview/user_orders?filter_date=2025-10-16&name=Alice&page=1&limit=10。

### 上传任务控制 (/v1/tasks)
- **POST /v1/tasks/{task_id}/start**：启动循环上传 (task_id e.g., user_orders)。
  - 返回：{"status": "started", "task_id": str, "interval": int}。
- **POST /v1/tasks/{task_id}/stop**：停止任务。
  - 返回：{"status": "stopped"}。
- **GET /v1/tasks/{task_id}/status**：查看状态。
  - 返回：{"status": "running/idle/stopped", "last_run": str, "errors": int}。
- **GET /v1/tasks/ListAllTask**：列表所有任务以及状态。
  - 返回：{"tasks": ["user_orders", ...], "total": int}。

## 开发与维护

### 开发流程
1. **配置调整**：编辑 interfaces.yaml / sql_templates/*.sql，重载服务器 (/docs 测试预览)。
2. **加新接口**：YAML 加块 (新 ID + sql_template_file)，创建新 .sql，POST /v1/tasks/{new_id}/start。
3. **调试**：日志 (console)，sql_used 返回 SQL 复制到 DM 管理工具验证。
4. **扩展**：query_params 加新参数 (preview.py 自动验证)；uploader.py 加加密逻辑。

### 自动上传机制
- 启动后：每 interval 秒执行 runner (查询 + 上传 + 状态更新)。
- 失败处理：日志错误，errors 计数 >3 自动 stop，回滚 DB 事务 (dmPython rollback)。

## 故障排除

| 问题 | 可能原因 | 解决方法 |
|------|----------|----------|
| DM 连接失败 | .env 配置错误 | 检查 DM_HOST/PORT/USER/PASS/DB，dmPython 驱动安装。测试 db.py execute "SELECT 1"。 |
| SQL 渲染错误 | Jinja 占位符不匹配 | 打印 build_sql 输出，DM 工具手动执行。 |
| 上传失败 (4xx/5xx) | upload_url/headers 错 | 检查 YAML URL/token，httpx resp.text 日志。 |
| 任务不运行 | interval=0 或 scheduler 未启动 | main.py 确认 scheduler.start()，/status 检查。 |
| Swagger 无动态参数输入框 | Pydantic 动态模型 | 用固定 Query 测试 (filter_date 等)，Postman 补自定义 params (name)。 |
| Redis 连接失败 | 服务未启动 | 运行 redis-server，fallback 内存 (重启丢失)。 |
| Pydantic ValidationError | query_params 类型错 | YAML type/default 匹配 (str/int/date)，/docs 示例填值测试。 |

## 部署建议
- **生产**：Gunicorn + Uvicorn (`gunicorn -w 4 -k uvicorn.workers.UvicornWorker app.main:app`)，Nginx 反代 + HTTPS。
- **Docker**：Dockerfile + docker-compose.yml (app + Redis + DM)。
- **监控**：Prometheus/Grafana 仪表盘 (状态/errors)，Sentry 错误捕获。
- **许可**：MIT，开源友好。

问题反馈：提供日志/错误栈，或 GitHub Issue。感谢使用！