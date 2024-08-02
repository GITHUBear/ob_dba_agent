import logging

from typing import List
from common.knowledge.document import Chunk
from common.knowledge.engine_base import EngineBase
from pymilvus import MilvusClient, FieldSchema, DataType, CollectionSchema, Collection


class MilvusSearchEngine(EngineBase):
    def __init__(self, logger: logging.Logger | None = None, **kwargs):
        super().__init__(logger, **kwargs)
        self._create_collections()

    def _create_collections(self):
        self.client = MilvusClient(self.db_file)
        if self.client.has_collection(collection_name=self.collection_name):
            self.client.load_collection(collection_name=self.collection_name)
            self.logger.info(f"load collection success: {self.collection_name}")
        else:
            corpus_fields = [
                FieldSchema(
                    name="id",
                    dtype=DataType.VARCHAR,
                    is_primary=True,
                    auto_id=True,
                    max_length=100,
                ),
                FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=65535),
                FieldSchema(name="doc_url", dtype=DataType.VARCHAR, max_length=1024),
                FieldSchema(name="doc_name", dtype=DataType.VARCHAR, max_length=512),
                FieldSchema(name="chunk_title", dtype=DataType.VARCHAR, max_length=256),
                FieldSchema(
                    name="enhanse_chunk_title", dtype=DataType.VARCHAR, max_length=2048
                ),
                FieldSchema(
                    name="content_dense_vec",
                    dtype=DataType.FLOAT_VECTOR,
                    dim=self.dense_dim,
                ),
                FieldSchema(
                    name="content_sparse_vec", dtype=DataType.SPARSE_FLOAT_VECTOR
                ),
                FieldSchema(
                    name="enhause_title_dense_vec",
                    dtype=DataType.FLOAT_VECTOR,
                    dim=self.dense_dim,
                ),
                FieldSchema(
                    name="enhause_title_sparse_vec", dtype=DataType.SPARSE_FLOAT_VECTOR
                ),
            ]
            corpus_schema = CollectionSchema(corpus_fields)
            self.client.create_collection(
                collection_name=self.collection_name, schema=corpus_schema
            )
            self.logger.info(f"create collection success: {self.collection_name}")

            ctt_dense_idx_params = self.client.prepare_index_params()
            ctt_dense_idx_params.add_index(
                field_name="content_dense_vec",
                index_name="ctt_dense_idx",
                index_type="HNSW",
                metric_type="L2",
                params={"M": 16, "efConstruction": 256},
            )
            self.client.create_index(self.collection_name, ctt_dense_idx_params)
            self.logger.info(f"create index success: ctt_dense_idx")

            ctt_sparse_idx_params = self.client.prepare_index_params()
            ctt_sparse_idx_params.add_index(
                field_name="content_sparse_vec",
                index_name="ctt_sparse_idx",
                index_type="SPARSE_INVERTED_INDEX",
                metric_type="IP",
                params={"drop_ratio_build": 0},
            )
            self.client.create_index(self.collection_name, ctt_sparse_idx_params)
            self.logger.info(f"create index success: ctt_sparse_idx")

            title_dense_idx_params = self.client.prepare_index_params()
            title_dense_idx_params.add_index(
                field_name="enhause_title_dense_vec",
                index_name="title_dense_idx",
                index_type="HNSW",
                metric_type="L2",
                params={"M": 16, "efConstruction": 256},
            )
            self.client.create_index(self.collection_name, title_dense_idx_params)
            self.logger.info(f"create index success: title_dense_idx")

            title_sparse_idx_params = self.client.prepare_index_params()
            title_sparse_idx_params.add_index(
                field_name="enhause_title_sparse_vec",
                index_name="title_sparse_idx",
                index_type="SPARSE_INVERTED_INDEX",
                metric_type="IP",
                params={"drop_ratio_build": 0},
            )
            self.client.create_index(self.collection_name, title_sparse_idx_params)
            self.logger.info(f"create index success: title_sparse_idx")

    def add_chunks(self, chunks: List[Chunk]):
        contents = [chunk.text for chunk in chunks]
        chunk_title_embd_str = [
            chunk.get_enhanced_url_for_embed()
            + " - "
            + chunk.get_enhanced_title_for_embed()
            for chunk in chunks
        ]

        contents_embds = self._embed(contents, True, True)
        chunk_title_embds = self._embed(chunk_title_embd_str, True, True)

        entities = []
        for chunk, ctt_dense, ctt_sparse, title_dense, title_sparse in zip(
            chunks,
            contents_embds["dense_vecs"],
            contents_embds["lexical_weights"],
            chunk_title_embds["dense_vecs"],
            chunk_title_embds["lexical_weights"],
        ):
            content = chunk.text
            chunk_meta = chunk.get_metadata()
            entities.append(
                {
                    "content": content,
                    "doc_url": chunk_meta["doc_url"],
                    "doc_name": chunk_meta["doc_name"],
                    "chunk_title": chunk_meta["chunk_title"],
                    "enhanse_chunk_title": chunk_meta["enhanced_title"],
                    "content_dense_vec": ctt_dense.tolist(),
                    "content_sparse_vec": ctt_sparse,
                    "enhause_title_dense_vec": title_dense.tolist(),
                    "enhause_title_sparse_vec": title_sparse,
                }
            )
        self.client.insert(self.collection_name, entities)
