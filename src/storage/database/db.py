import os
import time
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import OperationalError
import logging
logger = logging.getLogger(__name__)

MAX_RETRY_TIME = 5  # 连接最大重试时间（秒）- 从20秒减少到5秒
# Load environment variables from .env if present
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# 缓存数据库 URL，避免每次都调用 coze_workload_identity
_cached_db_url = None

def get_db_url() -> str:
    """Build database URL from environment."""
    global _cached_db_url
    
    # 如果已经缓存了，直接返回
    if _cached_db_url is not None:
        return _cached_db_url
    
    url = os.getenv("PGDATABASE_URL") or ""
    if url is not None and url != "":
        _cached_db_url = url
        logger.info("使用环境变量 PGDATABASE_URL")
        return url
    
    from coze_workload_identity import Client
    try:
        logger.info("开始从 coze_workload_identity 获取数据库 URL...")
        start_time = time.time()
        client = Client()
        env_vars = client.get_project_env_vars()
        client.close()
        for env_var in env_vars:
            if env_var.key == "PGDATABASE_URL":
                url = env_var.value.replace("'", "'\\''")
                _cached_db_url = url
                elapsed = time.time() - start_time
                logger.info(f"从 coze_workload_identity 获取数据库 URL 成功，耗时: {elapsed:.2f}s")
                return url
    except Exception as e:
        logger.error(f"Error loading PGDATABASE_URL: {e}")
        raise e
    finally:
        if url is None or url == "":
            logger.error("PGDATABASE_URL is not set")
    return url
_engine = None
_SessionLocal = None

def _create_engine_with_retry():
    url = get_db_url()
    if url is None or url == "":
        logger.error("PGDATABASE_URL is not set")
        raise ValueError("PGDATABASE_URL is not set")
    
    # 优化连接池配置，适配聊天应用场景
    size = 5  # 从100减少到5，聊天应用不需要太大的连接池
    overflow = 10  # 从100减少到10
    recycle = 300  # 从1800减少到300（5分钟），更频繁地回收连接
    timeout = 10  # 从30减少到10秒
    
    logger.info(f"创建数据库引擎 - pool_size={size}, max_overflow={overflow}, pool_recycle={recycle}s")
    
    engine = create_engine(
        url,
        pool_size=size,
        max_overflow=overflow,
        pool_pre_ping=True,
        pool_recycle=recycle,
        pool_timeout=timeout,
        echo=False  # 生产环境关闭 SQL 日志
    )
    
    # 验证连接，带重试
    start_time = time.time()
    last_error = None
    while time.time() - start_time < MAX_RETRY_TIME:
        try:
            logger.info("测试数据库连接...")
            conn_start = time.time()
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            conn_elapsed = time.time() - conn_start
            logger.info(f"数据库连接测试成功，耗时: {conn_elapsed:.2f}s")
            return engine
        except OperationalError as e:
            last_error = e
            elapsed = time.time() - start_time
            logger.warning(f"数据库连接失败，重试中... (已耗时: {elapsed:.1f}s, 错误: {type(e).__name__})")
            time.sleep(min(0.5, MAX_RETRY_TIME - elapsed))  # 减少重试等待时间从1秒到0.5秒
    
    total_elapsed = time.time() - start_time
    logger.error(f"数据库连接在 {total_elapsed:.1f}s 后失败: {last_error}")
    raise last_error  # pyright: ignore [reportGeneralTypeIssues]

def get_engine():
    global _engine
    if _engine is None:
        _engine = _create_engine_with_retry()
    return _engine

def get_sessionmaker():
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())
    return _SessionLocal

def get_session():
    return get_sessionmaker()()

__all__ = [
    "get_db_url",
    "get_engine",
    "get_sessionmaker",
    "get_session",
]
