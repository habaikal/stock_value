# ============================================================
# logger_config.py - 중앙집중식 로깅 설정
# ============================================================
import logging
import os
from logging.handlers import RotatingFileHandler
from config import LOG_FILE, LOG_LEVEL, LOG_FORMAT, LOG_MAX_BYTES, LOG_BACKUP_COUNT


def setup_logger(name: str = "StockAI", level: str = LOG_LEVEL) -> logging.Logger:
    """
    애플리케이션 전체 로거 설정.
    콘솔 + 파일 동시 로깅.
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level, logging.INFO))
    
    # 중복 핸들러 방지
    if logger.hasHandlers():
        return logger
    
    formatter = logging.Formatter(LOG_FORMAT)
    
    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 파일 핸들러 (회전식)
    os.makedirs("logs", exist_ok=True)
    log_path = os.path.join("logs", LOG_FILE)
    
    try:
        file_handler = RotatingFileHandler(
            log_path,
            maxBytes=LOG_MAX_BYTES,
            backupCount=LOG_BACKUP_COUNT
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        logger.warning(f"파일 로거 설정 실패: {e}")
    
    return logger


# 전역 로거 초기화
main_logger = setup_logger()
