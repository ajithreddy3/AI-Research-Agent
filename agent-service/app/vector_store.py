import time
import uuid
from dataclasses import dataclass

from pymilvus import Collection, CollectionSchema, DataType, FieldSchema, connections, utility

from . import config


@dataclass
class SearchResult:
    text_chunk: str
    paper_title: str
    score: float


def connect_milvus() -> None:
    connect_kwargs = {
        "alias": "default",
        "host": config.MILVUS_HOST,
        "port": config.MILVUS_PORT,
    }
    if config.MILVUS_USERNAME and config.MILVUS_PASSWORD:
        connect_kwargs["user"] = config.MILVUS_USERNAME
        connect_kwargs["password"] = config.MILVUS_PASSWORD
    connections.connect(**connect_kwargs)


def _collection_schema() -> CollectionSchema:
    fields = [
        FieldSchema(name="id", dtype=DataType.VARCHAR, max_length=64, is_primary=True, auto_id=False),
        FieldSchema(name="paper_title", dtype=DataType.VARCHAR, max_length=1024),
        FieldSchema(name="domain", dtype=DataType.VARCHAR, max_length=64),
        FieldSchema(name="language", dtype=DataType.VARCHAR, max_length=16),
        FieldSchema(name="text_chunk", dtype=DataType.VARCHAR, max_length=65535),
        FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=config.MILVUS_DIMENSION),
    ]
    return CollectionSchema(fields=fields, description="Academic paper chunks for Option 1")


def ensure_collection(index_type: str = "HNSW") -> Collection:
    connect_milvus()
    if utility.has_collection(config.MILVUS_COLLECTION):
        collection = Collection(config.MILVUS_COLLECTION)
    else:
        collection = Collection(name=config.MILVUS_COLLECTION, schema=_collection_schema())

    existing_indexes = collection.indexes
    if not existing_indexes:
        if index_type.upper() == "IVF_PQ":
            params = {
                "index_type": "IVF_PQ",
                "metric_type": config.MILVUS_METRIC_TYPE,
                "params": {"nlist": 128, "m": 16, "nbits": 8},
            }
        elif index_type.upper() == "DISKANN":
            params = {
                "index_type": "DISKANN",
                "metric_type": config.MILVUS_METRIC_TYPE,
                "params": {},
            }
        else:
            params = {
                "index_type": "HNSW",
                "metric_type": config.MILVUS_METRIC_TYPE,
                "params": {"M": 16, "efConstruction": 200},
            }

        collection.create_index(field_name="embedding", index_params=params)
    collection.load()
    return collection


def insert_chunks(
    collection: Collection,
    paper_title: str,
    domain: str,
    language: str,
    chunks: list[str],
    embeddings: list[list[float]],
) -> int:
    ids = [str(uuid.uuid4()) for _ in chunks]
    entities = [
        ids,
        [paper_title] * len(chunks),
        [domain] * len(chunks),
        [language] * len(chunks),
        chunks,
        embeddings,
    ]
    collection.insert(entities)
    collection.flush()
    return len(chunks)


def search_similar(
    collection: Collection,
    query_embedding: list[float],
    domain: str,
    top_k: int,
) -> list[SearchResult]:
    expr = f'domain == "{domain}"'
    results = collection.search(
        data=[query_embedding],
        anns_field="embedding",
        param={"metric_type": config.MILVUS_METRIC_TYPE, "params": {"ef": max(64, top_k)}},
        limit=top_k,
        expr=expr,
        output_fields=["paper_title", "text_chunk"],
    )

    output: list[SearchResult] = []
    for hit in results[0]:
        output.append(
            SearchResult(
                text_chunk=hit.entity.get("text_chunk"),
                paper_title=hit.entity.get("paper_title"),
                score=float(hit.distance),
            )
        )
    return output


def benchmark_index_rebuild(index_type: str) -> tuple[float, int]:
    """
    Rebuild index and return (seconds, estimated index bytes).
    For README experiment logging required by project rubric.
    """
    collection = ensure_collection(index_type=index_type)
    if collection.indexes:
        collection.drop_index()

    start = time.perf_counter()
    if index_type == "IVF_PQ":
        params = {"index_type": "IVF_PQ", "metric_type": config.MILVUS_METRIC_TYPE, "params": {"nlist": 128, "m": 16, "nbits": 8}}
    elif index_type == "DISKANN":
        params = {"index_type": "DISKANN", "metric_type": config.MILVUS_METRIC_TYPE, "params": {}}
    else:
        params = {"index_type": "HNSW", "metric_type": config.MILVUS_METRIC_TYPE, "params": {"M": 16, "efConstruction": 200}}
    collection.create_index("embedding", params)
    elapsed = time.perf_counter() - start

    index_size = 0
    try:
        stats = utility.index_building_progress(collection.name)
        indexed_rows = int(stats.get("indexed_rows", 0))
        index_size = indexed_rows * config.MILVUS_DIMENSION * 4
    except Exception:
        index_size = 0
    collection.load()
    return elapsed, index_size
