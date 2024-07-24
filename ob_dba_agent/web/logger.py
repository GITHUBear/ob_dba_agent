import os
import logging

log_level = os.environ.get("LOG_LEVEL", "INFO")
levelMapping = logging.getLevelNamesMapping()

logger = logging.getLogger("dba-agent")
logger.setLevel(levelMapping[log_level])
