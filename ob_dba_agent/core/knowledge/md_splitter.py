from typing import List
from .document import Document, Chunk
from langchain.text_splitter import MarkdownHeaderTextSplitter
from abc import ABC, abstractmethod

class DocSplitter(ABC):
    @abstractmethod
    def split_doc(self, doc: Document):
        pass

class LocalFsMdSplitter(DocSplitter):
    def __init__(self):
        headers_to_split_on = [
            ("#", "Header1"),
            ("##", "Header2"),
            ("###", "Header3"),
            ("####", "Header4"),
            ("#####", "Header5"),
            ("######", "Header6"),
        ]
        self.md_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)

    def split_doc(self, doc: Document) -> List[Chunk]:
        chunks = []
        with open(doc.doc_url, 'r', encoding='utf-8') as f:
            content = f.read()
            for chunk in self.md_splitter.split_text(content):
                my_chunk = Chunk(doc, chunk.page_content, list(chunk.metadata.values()))
                my_chunk.gen_id()
                chunks.append(my_chunk)
        return chunks
