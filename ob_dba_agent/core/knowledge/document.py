import uuid
from typing import List

class DocumentBase:
    def __init__(self, url: str, path_name_handler = None):
        self.url = url
        self.path_name_handler = path_name_handler
        protocal_split_idx = url.find('://')
        if -1 == protocal_split_idx:
            self.url_protocal = ''
        else:
            self.url_protocal = url[0:protocal_split_idx]
    
    def __repr__(self) -> str:
        return f"[DocumentBase] url={self.url} url_protocal={self.url_protocal}"

class Document:
    def __init__(self, doc_base: DocumentBase, url: str):
        self.doc_base = doc_base
        self.doc_url = url
        if not url.startswith(self.doc_base.url):
            raise ValueError('document is not in document base')
        related_path = (url[len(self.doc_base.url):]).strip('/')
        self.url_path_list = related_path.split('/')
        self.name = self.url_path_list[-1]
    
    def __repr__(self) -> str:
        return f"[Document] doc_url={self.doc_url} url_path_list={self.url_path_list} name={self.name}"
    
    def doc_url_enhanse(self):
        if self.doc_base.path_name_handler is not None:
            return ' - '.join([self.doc_base.path_name_handler(path) for path in self.url_path_list])
        else:
            return ' - '.join(self.url_path_list)
    
    def get_enhansed_doc_name(self):
        if self.doc_base.path_name_handler is not None:
            return self.doc_base.path_name_handler(self.name)
        else:
            return self.name

class Chunk:
    def __init__(self, doc: Document, text: str, subtitles: List[str]):
        self.doc = doc
        self.text = text
        if len(subtitles) == 0:
            subtitles.append(self.doc.get_enhansed_doc_name())
        self.subtitles = subtitles
        self.title = subtitles[-1]
        
    def set_id(self, id: str):
        self.id = id

    def gen_id(self):
        self.id = str(uuid.uuid1())
    
    def get_id(self) -> str:
        return self.id

    def __repr__(self) -> str:
        return f"[Chunk] subtitles={self.subtitles} title={self.title}"
    
    def get_enhance_text(self):
        return self.doc.name + ' - ' + self.get_enhanced_title_for_embed() + ': ' + self.text
    
    def get_enhanced_title_for_embed(self):
        return ' - '.join(self.subtitles)
    
    def get_enhanced_url_for_embed(self):
        return self.doc.doc_url_enhanse()
    
    def get_metadata(self) -> dict:
        return {
            "doc_url": self.doc.doc_url,
            "doc_name": self.doc.name,
            "enhance_url": self.doc.doc_url_enhanse(),
            "chunk_title": self.title,
            "enhanced_title": ' -> '.join(self.subtitles)
        }
    
    def get_metadata_for_title_enhance(self) -> dict:
        return {
            "doc_url": self.doc.doc_url,
            "doc_name": self.doc.name,
            "enhance_url": self.doc.doc_url_enhanse(),
            "chunk_title": self.title,
            "enhanced_title": ' -> '.join(self.subtitles),
            "document": self.text,
        }