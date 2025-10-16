# 简单占位：预览无需加密，上传时用
def generate_checksum(data: dict) -> str:
    import hashlib
    return hashlib.md5(str(data).encode()).hexdigest()[:8]  # 示例 HMAC 简化

# 扩展：JWT 等在上传用