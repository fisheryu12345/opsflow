"""
向量嵌入服务 — 将知识条目转为向量存入数据库
Vector Embedding Service — Convert knowledge entries to vectors for similarity search
"""
import hashlib
import json
import logging
import math
import re
from collections import Counter
from typing import List, Optional

logger = logging.getLogger(__name__)


# ── Lightweight TF-IDF vectorizer (no external deps) ──


class _TfidfVectorizer:
    """Simple in-memory TF-IDF vectorizer for fallback embedding"""

    def __init__(self):
        self._idf: dict[str, float] = {}
        self._fitted = False

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize Chinese + English text"""
        # Split Chinese characters
        tokens = []
        for token in re.findall(r'[一-鿿]+|[a-zA-Z]+', text.lower()):
            # Further split English by punctuation boundaries
            tokens.extend(re.findall(r'[a-zA-Z]+', token))
        return tokens

    def fit(self, documents: List[str]):
        """Compute IDF from a corpus"""
        n_docs = len(documents)
        df: Counter = Counter()
        for doc in documents:
            terms = set(self._tokenize(doc))
            for term in terms:
                df[term] += 1
        self._idf = {
            term: math.log((n_docs + 1) / (freq + 1)) + 1
            for term, freq in df.items()
        }
        self._fitted = True
        return self

    def transform(self, text: str) -> dict[str, float]:
        """Transform text to TF-IDF vector (sparse dict)"""
        tokens = self._tokenize(text)
        if not tokens:
            return {}
        tf = Counter(tokens)
        max_tf = max(tf.values())
        vector = {}
        for term, count in tf.items():
            tf_val = count / max_tf
            idf_val = self._idf.get(term, 1.0)
            vector[term] = tf_val * idf_val
        return vector

    def cosine_similarity(self, vec_a: dict[str, float], vec_b: dict[str, float]) -> float:
        """Compute cosine similarity between two sparse vectors"""
        if not vec_a or not vec_b:
            return 0.0
        intersection = set(vec_a.keys()) & set(vec_b.keys())
        dot_product = sum(vec_a[k] * vec_b[k] for k in intersection)
        norm_a = math.sqrt(sum(v * v for v in vec_a.values()))
        norm_b = math.sqrt(sum(v * v for v in vec_b.values()))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot_product / (norm_a * norm_b)


# Global TF-IDF vectorizer (lazy initialized)
_tfidf_vectorizer = _TfidfVectorizer()


class VectorService:
    """向量嵌入服务 — Vector Embedding Service"""

    EMBEDDING_DIM = 128  # Fixed dimension for hash-based embedding

    @classmethod
    def generate_embedding(cls, text: str) -> List[float]:
        """Generate embedding vector for text.

        Priority: sentence-transformers (all-MiniLM-L6-v2) if available.
        Fallback: deterministic hash-based feature vector.
        """
        # Try sentence-transformers first
        try:
            return cls._sentence_transformer_embed(text)
        except Exception as e:
            logger.debug(f"sentence-transformers unavailable, using fallback: {e}")
            return cls._hash_embed(text)

    @classmethod
    def _sentence_transformer_embed(cls, text: str) -> List[float]:
        """Embed using sentence-transformers library"""
        from sentence_transformers import SentenceTransformer

        # Lazy-load the model (cached after first call)
        if not hasattr(cls, "_st_model"):
            cls._st_model = SentenceTransformer("all-MiniLM-L6-v2")
        embedding = cls._st_model.encode(text, normalize_embeddings=True)
        return embedding.tolist()

    @classmethod
    def _hash_embed(cls, text: str, dim: int = 128) -> List[float]:
        """Deterministic hash-based embedding fallback.

        Uses feature hashing (hash of n-grams) to produce a fixed-dim vector.
        Output is L2-normalized.
        """
        vec = [0.0] * dim
        text_lower = text.lower()
        # Character n-grams (2-grams and 3-grams)
        for n in (2, 3):
            for i in range(len(text_lower) - n + 1):
                gram = text_lower[i:i + n]
                h = int(hashlib.md5(gram.encode()).hexdigest(), 16)
                idx = h % dim
                # Signed feature hash
                sign = 1 if (h // dim) % 2 == 0 else -1
                vec[idx] += sign * 1.0

        # L2 normalize
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec

    @classmethod
    def cosine_similarity(cls, vec_a: List[float], vec_b: List[float]) -> float:
        """Compute cosine similarity between two dense vectors"""
        if not vec_a or not vec_b or len(vec_a) != len(vec_b):
            return 0.0
        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    @classmethod
    def search_similar(cls, query: str, top_k: int = 5) -> List[dict]:
        """向量相似度搜索 — 返回最相关的知识条目
        Vector similarity search — return top_k most relevant knowledge entries.

        Uses cosine similarity on stored embeddings (dense or sparse).
        Falls back to TF-IDF keyword search if no embeddings are stored.
        """
        from opsflow.models import OpsKnowledge

        query_embedding = cls.generate_embedding(query)
        entries = OpsKnowledge.objects.all()
        scored = []

        for entry in entries:
            stored = entry.get_embedding_vector()
            if stored:
                score = cls.cosine_similarity(query_embedding, stored)
            else:
                # Fallback: text-based match with TF-IDF scoring
                score = cls._text_score(query, entry.title + " " + entry.content)
            scored.append((score, entry))

        # Sort by score descending
        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            {
                "id": entry.id,
                "title": entry.title,
                "content": entry.content[:500],  # Truncate for display
                "tags": entry.tags,
                "source": entry.source,
                "score": round(score, 4),
                "created_at": entry.created_at.isoformat() if entry.created_at else None,
            }
            for score, entry in scored[:top_k]
        ]

    @classmethod
    def _text_score(cls, query: str, text: str) -> float:
        """Simple text relevance score using TF-IDF"""
        global _tfidf_vectorizer
        if not _tfidf_vectorizer._fitted:
            # Fit on the fly with available content
            from opsflow.models import OpsKnowledge
            docs = [f"{k.title} {k.content}" for k in OpsKnowledge.objects.all()[:100]]
            if not docs:
                docs = [text]
            _tfidf_vectorizer.fit(docs)
        q_vec = _tfidf_vectorizer.transform(query)
        d_vec = _tfidf_vectorizer.transform(text)
        return _tfidf_vectorizer.cosine_similarity(q_vec, d_vec)

    @classmethod
    def index_all(cls):
        """批量索引所有知识条目 — Batch index all knowledge entries"""
        from opsflow.models import OpsKnowledge

        entries = OpsKnowledge.objects.filter(embedding__isnull=True)
        count = entries.count()
        if count == 0:
            logger.info("No unindexed knowledge entries found")
            return 0

        # Pre-fit TF-IDF vectorizer on all entries
        global _tfidf_vectorizer
        all_docs = [
            f"{k.title} {k.content}" for k in OpsKnowledge.objects.all()
        ]
        if all_docs:
            _tfidf_vectorizer.fit(all_docs)

        indexed = 0
        for entry in entries:
            text = f"{entry.title} {entry.content} {' '.join(entry.tags or [])}"
            try:
                embedding = cls.generate_embedding(text)
                entry.set_embedding_vector(embedding)
                entry.save(update_fields=["embedding"])
                indexed += 1
            except Exception as e:
                logger.error(f"Failed to index entry {entry.id}: {e}")

        logger.info(f"Indexed {indexed}/{count} knowledge entries")
        return indexed
