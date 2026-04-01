import sys

from loguru import logger


def setup_logging(env: str = "development") -> None:
    logger.remove()
    if env == "production":
        logger.add(sys.stdout, level="INFO", serialize=True)
    else:
        logger.add(
            sys.stdout,
            format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level:<8}</level> | "
                   "<cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
            level="DEBUG",
            colorize=True,
        )
