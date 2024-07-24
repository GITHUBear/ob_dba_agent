import os
import logging

log_level = os.environ.get("LOG_LEVEL", "INFO")
levelMapping = logging.getLevelNamesMapping()

handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)

logger = logging.getLogger("dba-agent")
logger.addHandler(handler)
logger.setLevel(levelMapping[log_level])
