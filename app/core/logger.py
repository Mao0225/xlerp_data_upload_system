import logging

# 简单日志配置
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def log_query(interface_name: str, sql: str):
    logger.info(f"Executed query for {interface_name}: {sql[:100]}...")  # 截断长 SQL

def log_error(interface_name: str, error: Exception):
    logger.error(f"Error in {interface_name}: {str(error)}")