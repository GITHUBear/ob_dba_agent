from typing import List
from pymilvus import MilvusClient
import logging
import os
from common.knowledge.engine_base import EngineBase


def parse_semver(ver: str):
    try:
        return tuple(map(int, ver.split(".")))
    except:
        return (0, 0, 0)


class MultiSearchEngine(EngineBase):
    def __init__(self, logger: logging.Logger | None = None, **kwargs):
        super().__init__(logger, **kwargs)

        self.db_files = []
        for name in os.listdir(self.config.milvus_db_store):
            self.db_files.append(
                (
                    name.replace(".db", ""),
                    os.path.join(self.config.milvus_db_store, name),
                )
            )
        self.__create_clients()

    def __create_clients(self):
        self.clients = {
            db_name: MilvusClient(db_file) for (db_name, db_file) in self.db_files
        }
        for db_name, client in self.clients.items():
            if not client.has_collection(collection_name=self.collection_name):
                raise ValueError(
                    f"collection {self.collection_name} not found in db {db_name}"
                )

    def search(
        self, query_texts: List[str], db_names: List[str] = ["oceanbase-4.3.1"]
    ) -> tuple[List[dict], List[int]]:
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


engine = MultiSearchEngine(logging.getLogger(__name__))

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
