from local_fs_doc_base_loader import LocalFsDocBaseMilvusLoader
from .document import DocumentBase
import logging

def parse_title(title: str) -> str:
    idx = title.find('.')
    return title[idx + 1:].strip(' ')

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

doc_base = DocumentBase(url='../../../resources/oceanbase-doc/zh-CN', path_name_handler=parse_title)
loader = LocalFsDocBaseMilvusLoader(logger)
loader.load_doc_base(doc_base)