"""Tiny BM25Okapi index — stdlib only, suitable for technique-scale corpora."""

from __future__ import annotations

import math
import re
from typing import Sequence


_TOKEN_RE = re.compile(r"[a-z0-9]+(?:\.[a-z0-9]+)*|[a-z]{2,}", re.IGNORECASE)


def tokenize(text: str) -> list[str]:
    return [t.lower() for t in _TOKEN_RE.findall(text or "")]


class BM25Index:
    def __init__(self, documents: Sequence[str], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self._docs_tokens = [tokenize(d) for d in documents]
        self._doc_freqs: list[dict[str, int]] = []
        self._doc_lens: list[int] = []
        df: dict[str, int] = {}
        for tokens in self._docs_tokens:
            fd: dict[str, int] = {}
            for t in tokens:
                fd[t] = fd.get(t, 0) + 1
            self._doc_freqs.append(fd)
            self._doc_lens.append(len(tokens))
            for t in fd:
                df[t] = df.get(t, 0) + 1
        self.N = len(documents)
        self.avgdl = sum(self._doc_lens) / self.N if self.N else 0.0
        self._idf = {
            t: math.log(1 + (self.N - n + 0.5) / (n + 0.5)) for t, n in df.items()
        }

    def scores(self, query: str) -> list[float]:
        q_tokens = tokenize(query)
        if not q_tokens:
            return [0.0] * self.N
        scores = [0.0] * self.N
        q_tf: dict[str, int] = {}
        for t in q_tokens:
            q_tf[t] = q_tf.get(t, 0) + 1
        for i in range(self.N):
            dl = self._doc_lens[i]
            denom_norm = self.k1 * (1 - self.b + self.b * dl / self.avgdl) if self.avgdl else self.k1
            fd = self._doc_freqs[i]
            s = 0.0
            for t, qf in q_tf.items():
                idf = self._idf.get(t)
                if idf is None:
                    continue
                f = fd.get(t, 0)
                if f == 0:
                    continue
                num = f * (self.k1 + 1)
                den = f + denom_norm
                s += idf * (num / den) * (1 + math.log(qf))
            scores[i] = s
        return scores

    def top_k(self, query: str, k: int) -> list[tuple[int, float]]:
        sc = self.scores(query)
        ranked = sorted(enumerate(sc), key=lambda x: x[1], reverse=True)
        return ranked[:k]

    def idf_vector(self) -> dict[str, float]:
        """Copy of IDF weights for explainability."""
        return dict(self._idf)

    def top_k_pooled(self, queries: list[str], k: int) -> list[tuple[int, float]]:
        """Per-document max BM25 score across multiple query strings (e.g. chunks)."""
        if not queries:
            return []
        pooled = [0.0] * self.N
        for q in queries:
            if not (q or "").strip():
                continue
            sc = self.scores(q)
            for i, s in enumerate(sc):
                if s > pooled[i]:
                    pooled[i] = s
        ranked = sorted(enumerate(pooled), key=lambda x: x[1], reverse=True)
        return ranked[:k]
