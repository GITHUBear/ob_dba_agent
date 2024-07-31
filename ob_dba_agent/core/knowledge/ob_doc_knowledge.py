from typing import List
from agentuniverse.agent.action.knowledge.knowledge import Knowledge
from agentuniverse.agent.action.knowledge.store.query import Query
from agentuniverse.agent.action.knowledge.store.document import Document
from .search_engine import MilvusSearchEngine
from .multi_search_engine import MultiSearchEngine
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
engine = MultiSearchEngine(logger)

class ObDocKnowledge(Knowledge):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    def insert_knowledge(self, **kwargs) -> None:
        # TODO
        pass

    def query_knowledge(self, **kwargs) -> List[Document]:
        query = Query(**kwargs)
        db_names = ['oceanbase-4.3.1']
        if 'db_names' in kwargs:
            db_names = kwargs['db_names']

        qstr = query.query_str
        docs, _ = engine.search([qstr], db_names=db_names)
        au_docs = []
        for doc in docs[0]:
            au_doc = Document()
            au_doc.id = doc['id']
            au_doc.text = doc['document']
            au_doc.metadata = doc['metadata']
            au_docs.append(au_doc)
        return au_docs
