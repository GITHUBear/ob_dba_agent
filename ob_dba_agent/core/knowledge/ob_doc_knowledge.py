from typing import List
from agentuniverse.agent.action.knowledge.knowledge import Knowledge
from agentuniverse.agent.action.knowledge.store.query import Query
from agentuniverse.agent.action.knowledge.store.document import Document
from .search_engine import MilvusSearchEngine
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
engine = MilvusSearchEngine(logger, "../../DB/milvus_rag.db")
# engine = MilvusSearchEngine(logger)

class ObDocKnowledge(Knowledge):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def insert_knowledge(self, **kwargs) -> None:
        # TODO
        pass

    def query_knowledge(self, **kwargs) -> List[Document]:
        query = Query(**kwargs)
        qstr = query.query_str
        docs, _ = engine.search([qstr])
        au_docs = []
        for doc in docs[0]:
            au_doc = Document()
            au_doc.id = doc['id']
            au_doc.text = doc['document']
            au_doc.metadata = doc['metadata']
            au_docs.append(au_doc)
        return au_docs
