from common.knowledge.search_engine_config import SearchEngineConfig
from FlagEmbedding import BGEM3FlagModel
from typing import List
import logging
import threading

__model = None


def get_model(model_args: SearchEngineConfig):
    global __model
    if __model is not None:
        return __model
    __model = BGEM3FlagModel(
        model_name_or_path=model_args.encoder_name,
        pooling_method=model_args.pooling_method,
        normalize_embeddings=model_args.normalize_embeddings,
        use_fp16=model_args.use_fp16,
    )
    return __model


def parse_semver(ver: str):
    try:
        return tuple(map(int, ver.split(".")))
    except:
        return (0, 0, 0)


class EngineBase:
    def __init__(self, logger: logging.Logger | None = None, **kwargs):
        config = SearchEngineConfig()
        self.config = config
        self.db_file = kwargs.get("db_file", config.milvus_db_file)
        self.collection_name = kwargs.get(
            "collection_name", config.milvus_corpus_collection_name
        )
        self.bge_lock = threading.Lock()
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
        self.logger = logger or logging.getLogger(__name__)

    def _embed(self, texts: List[str], use_dense: bool, use_sparse: bool):
        with self.bge_lock:
            return self.bge_m3_model.encode(
                texts,
                batch_size=1,
                max_length=512,
                return_dense=use_dense,
                return_sparse=use_sparse,
                return_colbert_vecs=False,
            )

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
        with self.bge_lock:
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
