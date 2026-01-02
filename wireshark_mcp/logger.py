"""日志配置模块"""

import logging
from typing import Optional


class CustomFormatter(logging.Formatter):
    """自定义日志格式器，带颜色"""
    
    grey = "\x1b[38;21m"
    blue = "\x1b[38;5;39m"
    yellow = "\x1b[38;5;226m"
    red = "\x1b[38;5;196m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"

    def __init__(self):
        super().__init__()
        self.fmt = "%(asctime)s %(levelname)s: %(message)s"
        self.FORMATS = {
            logging.DEBUG: self.grey + self.fmt + self.reset,
            logging.INFO: self.blue + self.fmt + self.reset,
            logging.WARNING: self.yellow + self.fmt + self.reset,
            logging.ERROR: self.red + self.fmt + self.reset,
            logging.CRITICAL: self.bold_red + self.fmt + self.reset
        }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt, datefmt="%H:%M:%S")
        return formatter.format(record)


def setup_logger(
    name: str = __name__,
    level: int = logging.INFO,
    use_color: bool = True
) -> logging.Logger:
    """
    设置并返回配置好的日志记录器
    
    Args:
        name: 日志记录器名称
        level: 日志级别
        use_color: 是否使用颜色格式化器
    
    Returns:
        配置好的日志记录器
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # 避免重复添加处理器
    if logger.handlers:
        return logger
    
    handler = logging.StreamHandler()
    handler.setLevel(level)
    
    if use_color:
        handler.setFormatter(CustomFormatter())
    else:
        formatter = logging.Formatter(
            "%(asctime)s %(levelname)s: %(message)s",
            datefmt="%H:%M:%S"
        )
        handler.setFormatter(formatter)
    
    logger.addHandler(handler)
    return logger


def get_logger(name: Optional[str] = None) -> logging.Logger:
    """
    获取日志记录器（如果未配置则自动配置）
    
    Args:
        name: 日志记录器名称，默认为调用模块名
    
    Returns:
        日志记录器实例
    """
    if name is None:
        import inspect
        frame = inspect.currentframe()
        if frame and frame.f_back:
            name = frame.f_back.f_globals.get('__name__', __name__)
        else:
            name = __name__
    
    logger = logging.getLogger(name)
    
    # 如果日志记录器未配置，使用默认配置
    if not logger.handlers:
        return setup_logger(name)
    
    return logger

