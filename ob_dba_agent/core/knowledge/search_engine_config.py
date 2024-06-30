class SearchEngineConfig:
    encoder_name = 'BAAI/bge-m3'
    pooling_method = 'cls'
    normalize_embeddings = True
    use_fp16 = True

    milvus_db_file = "../../../DB/milvus_rag.db"
    milvus_corpus_collection_name="corpus"
    milvus_dense_corpus_topk = 10
    milvus_sparse_corpus_topk = 10
    milvus_dense_title_topk = 6
    milvus_sparse_title_topk = 6
    milvus_reranker_topk = 10
    milvus_dense_dim = 1024

    dense_weight = 0.3
    sparse_weight = 0.2
    colbert_weight = 0.5