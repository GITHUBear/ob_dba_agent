import fire
from common.knowledge.local_fs_doc_base_loader import LocalFsDocBaseMilvusLoader
from common.knowledge.document import DocumentBase
from common.knowledge.convert_headings import walk_dir


class Commands:

    def embedding_docs(
        self,
        *,
        doc_folder: str,
        db_file: str,
        collection_name: str = "corpus",
    ):
        """
        Load documents from local file system and embedding them into Milvus.
        Embedding model is BGE-m3.
        """
        doc_base = DocumentBase(url=doc_folder)
        loader = LocalFsDocBaseMilvusLoader(
            db_file=db_file,
            collection_name=collection_name,
        )
        loader.load_doc_base(doc_base)

    def correct_md_headings(
        self,
        *,
        doc_folder: str,
    ):
        """
        Convert markdown headings to correct format.
        """
        walk_dir(doc_folder)


if __name__ == "__main__":
    fire.Fire(Commands)
