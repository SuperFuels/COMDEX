# backend/modules/sqi/sqi_trace_logger.py
import logging

logger = logging.getLogger(__name__)

class SQITraceLogger:
    @staticmethod
    def log_trace(engine, message: str):
        logger.info(f"[SQITrace] {message}")