from .search_engine_config import SearchEngineConfig
from FlagEmbedding import BGEM3FlagModel
from .document import Chunk
from typing import List
from pymilvus import MilvusClient, FieldSchema, DataType, CollectionSchema, Collection
import logging

_model = None

def get_model(model_args: SearchEngineConfig):
    global _model
    if _model is not None:
        return _model
    _model = BGEM3FlagModel(
        model_name_or_path=model_args.encoder_name,
        pooling_method=model_args.pooling_method,
        normalize_embeddings=model_args.normalize_embeddings,
        use_fp16=model_args.use_fp16,
    )
    return _model


class MilvusSearchEngine:
    def __init__(self, logger: logging.Logger, db_path = "../../../DB/milvus_rag.db"):
        config = SearchEngineConfig()
        self.db_file = db_path
        self.collection_corpus = config.milvus_corpus_collection_name
        self.bge_m3_model = get_model(config)
        self.dense_corpus_topk = config.milvus_dense_corpus_topk
        self.sparse_corpus_topk = config.milvus_sparse_corpus_topk
        self.dense_title_topk = config.milvus_dense_title_topk
        self.sparse_title_topk = config.milvus_sparse_title_topk
        self.reranker_topk = config.milvus_reranker_topk
        self.dense_weight = config.dense_weight
        self.sparse_weight = config.sparse_weight
        self.colbert_weight = config.colbert_weight
        self.dense_dim = config.milvus_dense_dim
        self.logger = logger
        self._create_collections()

    def _create_collections(self):
        self.client = MilvusClient(self.db_file)
        if self.client.has_collection(collection_name=self.collection_corpus):
            self.client.load_collection(collection_name=self.collection_corpus)
            self.logger.info(f"load collection success: {self.collection_corpus}")
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
                collection_name=self.collection_corpus, schema=corpus_schema
            )
            self.logger.info(f"create collection success: {self.collection_corpus}")

            ctt_dense_idx_params = self.client.prepare_index_params()
            ctt_dense_idx_params.add_index(
                field_name="content_dense_vec",
                index_name="ctt_dense_idx",
                index_type="HNSW",
                metric_type="L2",
                params={"M": 16, "efConstruction": 256},
            )
            self.client.create_index(self.collection_corpus, ctt_dense_idx_params)
            self.logger.info(f"create index success: ctt_dense_idx")

            ctt_sparse_idx_params = self.client.prepare_index_params()
            ctt_sparse_idx_params.add_index(
                field_name="content_sparse_vec",
                index_name="ctt_sparse_idx",
                index_type="SPARSE_INVERTED_INDEX",
                metric_type="IP",
                params={"drop_ratio_build": 0},
            )
            self.client.create_index(self.collection_corpus, ctt_sparse_idx_params)
            self.logger.info(f"create index success: ctt_sparse_idx")

            title_dense_idx_params = self.client.prepare_index_params()
            title_dense_idx_params.add_index(
                field_name="enhause_title_dense_vec",
                index_name="title_dense_idx",
                index_type="HNSW",
                metric_type="L2",
                params={"M": 16, "efConstruction": 256},
            )
            self.client.create_index(self.collection_corpus, title_dense_idx_params)
            self.logger.info(f"create index success: title_dense_idx")

            title_sparse_idx_params = self.client.prepare_index_params()
            title_sparse_idx_params.add_index(
                field_name="enhause_title_sparse_vec",
                index_name="title_sparse_idx",
                index_type="SPARSE_INVERTED_INDEX",
                metric_type="IP",
                params={"drop_ratio_build": 0},
            )
            self.client.create_index(self.collection_corpus, title_sparse_idx_params)
            self.logger.info(f"create index success: title_sparse_idx")

    def _embed(self, texts: List[str], use_dense: bool, use_sparse: bool):
        return self.bge_m3_model.encode(
            texts,
            batch_size=1,
            max_length=512,
            return_dense=use_dense,
            return_sparse=use_sparse,
            return_colbert_vecs=False,
        )

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
        self.client.insert(self.collection_corpus, entities)

    def _merge_res_with_reranker(self, query: str, all_doc_snippets: List[dict]):
        id_dict = {}
        rerank_doc_id = []
        rerank_pair = []
        for doc_snippet_with_score in all_doc_snippets:
            doc_snippet = doc_snippet_with_score["entity"]
            id = doc_snippet["id"]
            if id not in id_dict:
                id_dict[id] = {
                    "id": id,
                    "metadata": {
                        "doc_url": doc_snippet["doc_url"],
                        "doc_name": doc_snippet["doc_name"],
                        "chunk_title": doc_snippet["chunk_title"],
                        "enhanced_title": doc_snippet["enhanse_chunk_title"],
                    },
                    "document": doc_snippet["content"],
                }
                rerank_doc_id.append(id)
                rerank_pair.append((query, doc_snippet["content"]))
        scores_dict = self.bge_m3_model.compute_score(
            rerank_pair,
            batch_size=1,
            max_query_length=512,
            max_passage_length=8192,
            weights_for_different_modes=[
                self.dense_weight,
                self.sparse_weight,
                self.colbert_weight,
            ],
        )
        scores = scores_dict["colbert+sparse+dense"]
        combined = list(zip(scores, rerank_doc_id))
        combined_sorted = sorted(combined, key=lambda x: x[0], reverse=True)
        merge_res = []
        for _, doc_id in combined_sorted:
            merge_res.append(id_dict[doc_id])

        same_doc_idx = []
        doc_url_idx_mapper = {}
        for i in range(self.reranker_topk):
            mr = merge_res[i]
            doc_url = mr["metadata"]["doc_url"]
            if doc_url not in doc_url_idx_mapper:
                doc_url_idx_mapper[doc_url] = len(same_doc_idx)
                same_doc_idx.append([i])
            else:
                same_doc_idx[doc_url_idx_mapper[doc_url]].append(i)
        return merge_res[: self.reranker_topk], same_doc_idx

    def search(self, query_texts: List[str]):
        query_embds = self._embed(query_texts, True, True)

        ctt_dense_search = self.client.search(
            self.collection_corpus,
            data=[embds.tolist() for embds in query_embds["dense_vecs"]],
            limit=self.dense_corpus_topk,
            anns_field="content_dense_vec",
            output_fields=[
                "id",
                "content",
                "doc_url",
                "doc_name",
                "chunk_title",
                "enhanse_chunk_title",
            ],
        )

        ctt_sparse_search = self.client.search(
            self.collection_corpus,
            data=query_embds["lexical_weights"],
            limit=self.sparse_corpus_topk,
            anns_field="content_sparse_vec",
            output_fields=[
                "id",
                "content",
                "doc_url",
                "doc_name",
                "chunk_title",
                "enhanse_chunk_title",
            ],
        )

        title_dense_search = self.client.search(
            self.collection_corpus,
            data=[embds.tolist() for embds in query_embds["dense_vecs"]],
            limit=self.dense_title_topk,
            anns_field="enhause_title_dense_vec",
            output_fields=[
                "id",
                "content",
                "doc_url",
                "doc_name",
                "chunk_title",
                "enhanse_chunk_title",
            ],
        )

        title_sparse_search = self.client.search(
            self.collection_corpus,
            data=query_embds["lexical_weights"],
            limit=self.sparse_title_topk,
            anns_field="enhause_title_sparse_vec",
            output_fields=[
                "id",
                "content",
                "doc_url",
                "doc_name",
                "chunk_title",
                "enhanse_chunk_title",
            ],
        )

        results = []
        same_doc_idxs = []
        for i in range(len(query_texts)):
            all_doc_snippets = []
            all_doc_snippets.extend(ctt_dense_search[i])
            all_doc_snippets.extend(ctt_sparse_search[i])
            all_doc_snippets.extend(title_dense_search[i])
            all_doc_snippets.extend(title_sparse_search[i])
            rerank_result, same_doc_idx = self._merge_res_with_reranker(
                query_texts[i], all_doc_snippets
            )
            results.append(rerank_result)
            same_doc_idxs.append(same_doc_idx)
        return results, same_doc_idxs
