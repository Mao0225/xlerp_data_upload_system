from fastapi import APIRouter, Query, Depends, HTTPException, Request
from app.core.query_builder import build_sql
from app.core.config_loader import load_configs
from app.core.logger import log_query
from app.db.db import execute_query
from app.models.base_source import BaseSource
from typing import Optional, Dict, Any
from pydantic import BaseModel, ValidationError

configs = load_configs()["interfaces"]

router = APIRouter()


def validate_dynamic_params(query_params: Dict[str, Any], interface_name: str) -> Dict[str, Any]:
    config = configs[interface_name]
    param_schema = config.get("param_schema", {})

    # 只验证自定义动态参数（跳过固定 page/limit/filter_date）
    dynamic_fields = {k: v for k, v in param_schema.items() if k not in ["page", "limit"]}

    if dynamic_fields:
        from pydantic import create_model
        from typing import Optional

        fields = {}
        for param_name, schema in dynamic_fields.items():
            param_type_str = schema["type"]
            field_type = int if param_type_str == "int" else str
            required = schema["required"]
            default = schema["default"]
            if required:
                fields[param_name] = (field_type, ...)
            elif default is not None:
                fields[param_name] = (field_type, default)
            else:
                fields[param_name] = (Optional[field_type], None)

        DynamicParams = create_model(f"DynamicParams{interface_name}", __base__=BaseModel, **fields)
        try:
            validated = DynamicParams(**query_params)
            return validated.dict(exclude_unset=True)
        except ValidationError as e:
            raise HTTPException(400, f"Invalid dynamic params: {e.json()}")
    return {}


@router.get("/preview/{interface_name}")
async def preview_interface(
        request: Request,  # 用于动态参数
        interface_name: str,

        page: int = Query(
            1,
            ge=1,
            description="分页页码"
        ),
        limit: int = Query(
            50,
            le=100,
            description="每页条数"
        )
):
    config = configs[interface_name]

    # 构建通用 params（覆盖 YAML 默认）
    validated_params = {
        "page": page,
        "limit": limit
    }

    # 验证动态参数
    all_query_params = dict(request.query_params)
    dynamic_validated = validate_dynamic_params(all_query_params, interface_name)
    validated_params.update(dynamic_validated)

    # 填充 YAML 默认（自定义参数）
    param_schema = config.get("param_schema", {})
    for param_name, schema in param_schema.items():
        if param_name not in validated_params:
            validated_params[param_name] = schema["default"]

    # 构建 SQL
    sql = build_sql(config, validated_params)

    log_query(interface_name, sql)
    rows = execute_query(sql)

    # 校验 required_fields
    required = config.get("required_fields", [])
    valid_rows = [row for row in rows if all(row.get(field) is not None for field in required)]

    # 分页
    total = len(valid_rows)
    start = (page - 1) * limit
    end = start + limit
    paginated = valid_rows[start:end]

    data = [BaseSource(**row).dict() for row in paginated]

    # 过滤 preview_fields
    preview_fields = config.get("preview_fields", [])
    if preview_fields:
        data = [{k: v for k, v in d.items() if k in preview_fields} for d in data]

    return {
        "interface": interface_name,
        "data": data,
        "total": total,
        "page": page,
        "limit": limit,
        "sql_used": sql
    }