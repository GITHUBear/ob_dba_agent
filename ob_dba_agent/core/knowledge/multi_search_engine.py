from .search_engine_config import SearchEngineConfig
from FlagEmbedding import BGEM3FlagModel
from typing import List
from pymilvus import MilvusClient, FieldSchema, DataType, CollectionSchema, Collection
import logging
import threading
import os

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


def parse_semver(ver: str):
    return tuple(map(int, ver.split(".")))


class MultiSearchEngine:
    def __init__(self, logger: logging.Logger):
        config = SearchEngineConfig()
        self.db_files = []
        for name in os.listdir(config.milvus_db_store):
            self.db_files.append(
                (name.replace(".db", ""), os.path.join(config.milvus_db_store, name))
            )
        self.collection_name = config.milvus_corpus_collection_name
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
        self.logger = logger
        self._create_clients()

    def _create_clients(self):
        self.clients = {
            db_name: MilvusClient(db_file) for (db_name, db_file) in self.db_files
        }
        for db_name, client in self.clients.items():
            if not client.has_collection(collection_name=self.collection_name):
                raise ValueError(
                    f"collection {self.collection_name} not found in db {db_name}"
                )

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

    def search(self, query_texts: List[str], db_names: List[str] = ["oceanbase-4.3.1"]):
        query_embds = self._embed(query_texts, True, True)

        output_fields = [
            "id",
            "content",
            "doc_url",
            "doc_name",
            "chunk_title",
            "enhanse_chunk_title",
        ]

        search_results = []

        for db_name in db_names:
            target = db_name
            if db_name not in self.clients:
                name, version = db_name.split("-")
                target_semver = parse_semver(version)
                for key in sorted(self.clients.keys()):
                    x_name, x_version = key.split("-")
                    x_semver = parse_semver(x_version)
                    if name == x_name and (
                        target_semver[0] == x_semver[0]
                        and target_semver[1] == x_semver[1]
                    ):
                        target = key
                        break

                if target not in self.clients:
                    # component analyzing error
                    continue

            client = self.clients[target]
            client.load_collection(collection_name=self.collection_name)
            search_results.append(
                client.search(
                    self.collection_name,
                    data=[embds.tolist() for embds in query_embds["dense_vecs"]],
                    limit=self.dense_corpus_topk,
                    anns_field="content_dense_vec",
                    output_fields=output_fields,
                )
            )
            search_results.append(
                client.search(
                    self.collection_name,
                    data=query_embds["lexical_weights"],
                    limit=self.sparse_corpus_topk,
                    anns_field="content_sparse_vec",
                    output_fields=output_fields,
                )
            )
            client.release_collection(collection_name=self.collection_name)

        results = []
        same_doc_idxs = []
        for i in range(len(query_texts)):
            all_doc_snippets = []
            for res in search_results:
                all_doc_snippets.extend(res[i])
            rerank_result, same_doc_idx = self._merge_res_with_reranker(
                query_texts[i], all_doc_snippets
            )
            results.append(rerank_result)
            same_doc_idxs.append(same_doc_idx)
        return results, same_doc_idxs


if __name__ == "__main__":
    import logging

    logger = logging.getLogger(__name__)
    engine = MultiSearchEngine(logger)
    print(
        engine.search(
            ["OCP所在的机器重启了，如何恢复OCP的所有服务？"],
            ["oceanbase-4.3.1", "ocp-4.3.0"],
        )
    )
