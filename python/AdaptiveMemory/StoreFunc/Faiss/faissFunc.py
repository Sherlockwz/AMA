from __future__ import annotations

import faiss
import os
import numpy as np
from StoreFunc.Faiss.embedding import getEmbedding,getEmbeddingsList

_DATA_DIR = "Store"


def set_data_dir(data_dir: str | None):
    global _DATA_DIR
    if data_dir:
        _DATA_DIR = os.path.abspath(data_dir)


def get_data_dir() -> str:
    os.makedirs(_DATA_DIR, exist_ok=True)
    return _DATA_DIR


def get_index_path(user: str, embedType: str) -> str:
    return os.path.join(get_data_dir(), f"{user}_{embedType}_Index.faiss")

def loadFaissIndex(user: str, dim: int = 3072, embedType: str = "text"):
    os.makedirs(get_data_dir(), exist_ok=True)
    indexPath = get_index_path(user=user, embedType=embedType)

    if os.path.exists(indexPath):
        print(f"✅ Found existing FAISS index for user '{user}' [{embedType}] at: {indexPath}")
        index = faiss.read_index(indexPath)
    else:
        base = faiss.IndexFlatIP(dim)
        index = faiss.IndexIDMap(base)
        faiss.write_index(index, indexPath)
        print(f"✅ New FAISS index created and saved at: {indexPath}")

    return index, indexPath

def makeTwoTypesIndex(user: str, dim: int = 3072):
    loadFaissIndex(user=user, dim=dim, embedType="text")
    loadFaissIndex(user=user, dim=dim, embedType="fact")

def addToFaissIndex(user: str, text: str, id: int, embedType: str = "text", dim: int = 3072):
    index, indexPath = loadFaissIndex(user=user, dim=dim, embedType=embedType)

    try:
        embedding = getEmbedding(text)
        if embedding is None:
            print("⚠️ Empty embedding, nothing added.")
            return False

        vector = np.array(embedding, dtype="float32").reshape(1, -1)
        faiss.normalize_L2(vector)
        ids = np.array([id], dtype="int64")

        index.add_with_ids(vector, ids)

        faiss.write_index(index, indexPath)
        print(f"✅ Added embedding (ID={id}) to FAISS index: {indexPath}")

        return True

    except Exception as e:
        print(f"❌ Failed to add embedding (ID={id}): {e}")
        return False

def addBatchToFaissIndex(
    user: str,
    texts: list[str],
    ids: list[int],
    dim: int = 3072,
):
    if not texts or not ids or len(texts) != len(ids):
        print("⚠️ texts and ids length mismatch or empty.")
        return False

    index, indexPath = loadFaissIndex(user=user, dim=dim, embedType="fact")

    try:
        embeddings = getEmbeddingsList(texts)
        if not embeddings or len(embeddings) != len(texts):
            print("⚠️ Embedding generation failed or length mismatch.")
            return False

        vectors = np.array(embeddings, dtype="float32")
        faiss.normalize_L2(vectors)

        ids_np = np.array(ids, dtype="int64")

        index.add_with_ids(vectors, ids_np)

        faiss.write_index(index, indexPath)
        print(f"✅ Successfully added {len(texts)} embeddings to FAISS index: {indexPath}")

        return True

    except Exception as e:
        print(f"❌ Failed to add batch embeddings: {e}")
        return False

def addBatchToSentencesIndex(
    user: str,
    texts: list[str],
    ids: list[int],
    dim: int = 3072,
):
    if not texts or not ids or len(texts) != len(ids):
        print("⚠️ texts and ids length mismatch or empty.")
        return False

    index, indexPath = loadFaissIndex(user=user, dim=dim, embedType="sentence")

    try:
        embeddings = getEmbeddingsList(texts)
        if not embeddings or len(embeddings) != len(texts):
            print("⚠️ Embedding generation failed or length mismatch.")
            return False

        vectors = np.array(embeddings, dtype="float32")
        faiss.normalize_L2(vectors)

        ids_np = np.array(ids, dtype="int64")

        index.add_with_ids(vectors, ids_np)

        faiss.write_index(index, indexPath)
        print(f"✅ Successfully added {len(texts)} embeddings to FAISS index: {indexPath}")

        return True

    except Exception as e:
        print(f"❌ Failed to add batch embeddings: {e}")
        return False

def deleteFromFaissIndex(user: str, id: int, embedType: str = "text", dim: int = 3072):
    index, indexPath = loadFaissIndex(user=user, dim=dim, embedType=embedType)

    try:
        removeIds = np.array([id], dtype="int64")

        before = index.ntotal

        index.remove_ids(removeIds)

        after = index.ntotal

        if before == after:
            print(f"⚠️ ID={id} not found in index.")
            return False

        faiss.write_index(index, indexPath)
        print(f"✅ Successfully deleted vector with ID={id} from {indexPath}")

        return True

    except Exception as e:
        print(f"❌ Failed to delete ID={id}: {e}")
        return False

def searchFaissIndex(user: str, queryText: str, topK: int = 5, embedType: str = "fact", dim: int = 3072):
    index, indexPath = loadFaissIndex(user=user, dim=dim, embedType=embedType)

    if index.ntotal == 0:
        print(f"⚠️ Index is empty for user '{user}' [{embedType}].")
        return [], []

    try:
        embedding = getEmbedding(queryText)
        if embedding is None:
            print("⚠️ Query embedding is empty.")
            return [], []
    except Exception as e:
        print(f"❌ Failed to get query embedding: {e}")
        return [], []

    queryVector = np.array(embedding, dtype="float32").reshape(1, -1)
    faiss.normalize_L2(queryVector)

    distances, ids = index.search(queryVector, topK)

    idList = [int(i) for i in ids[0] if i != -1]
    distanceList = [float(d) for d, i in zip(distances[0], ids[0]) if i != -1]

    return idList, distanceList

def searchTwoTypesInFaissIndex(user: str, queryText: str, topK: int = 5, dim: int = 3072):
    textResults = searchFaissIndex(user=user, queryText=queryText, topK=topK, embedType="text", dim=dim)
    factResults = searchFaissIndex(user=user, queryText=queryText, topK=topK, embedType="fact", dim=dim)

    return textResults, factResults

def deleteUserFaissIndices(user: str, dim: int = 3072):
    results = {}
    for embedType in ["text", "fact","sentence"]:
        try:
            _, indexPath = loadFaissIndex(user=user, dim=dim, embedType=embedType)
            if os.path.exists(indexPath):
                os.remove(indexPath)
                print(f"🗑️ Deleted {embedType} FAISS index: {indexPath}")
                results[embedType] = True
            else:
                print(f"⚠️ {embedType} FAISS index not found: {indexPath}")
                results[embedType] = False
        except Exception as e:
            print(f"❌ Failed to delete {embedType} FAISS index: {e}")
            results[embedType] = False

    return results
