import os
import logging
from abc import ABC, abstractmethod
from common.knowledge.document import DocumentBase, Document
from common.knowledge.md_splitter import LocalFsMdSplitter
from common.knowledge.search_engine import MilvusSearchEngine

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class DocBaseLoader(ABC):
    @abstractmethod
    def load_doc_base(self, doc_base: DocumentBase):
        pass

class LocalFsDocBaseMilvusLoader(DocBaseLoader):
    def __init__(self, logger: logging.Logger | None = None, **kwargs):
        self.logger = logger or logging.getLogger(__name__)
        self.engine = MilvusSearchEngine(logger, **kwargs)

    def load_doc_base(self, doc_base: DocumentBase, checkpoint = 0):
        md_splitter = LocalFsMdSplitter()
        file_cnt = 0
        for root, _, files in os.walk(doc_base.url):
            for file in files:
                if file.endswith('.md'):
                    file_path = os.path.join(root, file)
                    self.logger.info(f"finish {file_cnt}s doc -- current: {file_path}")
                    if file_cnt >= checkpoint:
                        doc = Document(doc_base, file_path)
                        chunks = md_splitter.split_doc(doc)
                        self.engine.add_chunks(chunks)
                    file_cnt += 1