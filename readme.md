# 数据上传平台 - 预览接口原型

## 启动
1. pip install -r requirements.txt
2. # 改 .env 中的 DM 连接
3. uvicorn app.main:app --reload --port 8000

## 测试预览
- GET /v1/preview/user_orders?filter_date=2025-01-01&page=1&limit=10
- Swagger: http://localhost:8000/docs

## 维护
- 加接口：configs/interfaces.yaml 加块 + sql_templates/ 新.sql
- 改 SQL：编辑 sql_templates/*.sql，重载测试