from __future__ import annotations

import os
import pickle
from dataclasses import dataclass
from typing import Iterable

import numpy as np


@dataclass
class Antibody:
    weights: np.ndarray
    affinity: float = 0.0

    @staticmethod
    def random(dim: int) -> "Antibody":
        return Antibody(weights=np.random.randn(dim).astype(np.float32))

    def predict(self, antigen: np.ndarray) -> int:
        score = float(np.dot(self.weights, antigen[: self.weights.shape[0]]))
        return 1 if score > 0.0 else 0

    def mutate(self, rate: float) -> "Antibody":
        noise = np.random.randn(*self.weights.shape).astype(np.float32) * float(rate)
        return Antibody(weights=self.weights + noise)


class ImmuneMemory:
    def __init__(self, pool_size: int = 256, feature_dim: int = 256):
        self.pool_size = int(pool_size)
        self.feature_dim = int(feature_dim)
        self.antibodies: list[Antibody] = [Antibody.random(self.feature_dim) for _ in range(self.pool_size)]

    def detect(self, antigen: np.ndarray, top_k: int = 10, vote_threshold: int = 5) -> bool:
        top = self.antibodies[: max(1, int(top_k))]
        votes = sum(ab.predict(antigen) for ab in top)
        return votes >= int(vote_threshold)

    def _affinity(self, ab: Antibody, antigens: Iterable[np.ndarray], labels: Iterable[int]) -> float:
        pairs = list(zip(antigens, labels))
        if not pairs:
            return 0.0
        correct = sum(1 for ag, lb in pairs if ab.predict(ag) == int(lb))
        return float(correct) / float(len(pairs))

    def clonal_selection(self, antigens: list[np.ndarray], labels: list[int], mutation_rate: float = 0.05) -> None:
        if not antigens or not labels:
            return
        new_generation: list[Antibody] = []
        for ab in self.antibodies:
            aff = self._affinity(ab, antigens, labels)
            clone_count = max(1, int(8 * (1.0 - aff)))
            for _ in range(clone_count):
                clone = ab.mutate(mutation_rate)
                clone.affinity = self._affinity(clone, antigens, labels)
                new_generation.append(clone)
        new_generation.sort(key=lambda x: x.affinity, reverse=True)
        self.antibodies = new_generation[: self.pool_size]

    def save(self, path: str) -> None:
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "wb") as f:
            pickle.dump(self, f)

    @staticmethod
    def load_or_create(path: str, pool_size: int = 256, feature_dim: int = 256) -> "ImmuneMemory":
        if os.path.exists(path):
            try:
                with open(path, "rb") as f:
                    obj = pickle.load(f)
                if isinstance(obj, ImmuneMemory):
                    return obj
            except Exception:
                pass
        return ImmuneMemory(pool_size=pool_size, feature_dim=feature_dim)
