from __future__ import annotations

from typing import List, Sequence

import torch
from torch.utils.data import Dataset


class RansomwareSequenceDataset(Dataset):
    """Dataset for sequence-to-future-state regression.

    Each X sample is a sequence of vectors with 6 features:
    [file_ops_rate, entropy, encryption_api_calls, power, acoustic, thermal]
    """

    def __init__(self, X: Sequence[Sequence[Sequence[float]]], y: Sequence[Sequence[float]], seq_len: int = 50):
        if len(X) != len(y):
            raise ValueError("X and y must have the same length")
        self.seq_len = seq_len
        self.X = [self._pad_or_truncate(list(seq)) for seq in X]
        self.y = list(y)

    def _pad_or_truncate(self, seq: List[Sequence[float]]) -> List[Sequence[float]]:
        if not seq:
            return [[0.0] * 6 for _ in range(self.seq_len)]
        if len(seq) > self.seq_len:
            return seq[-self.seq_len :]
        if len(seq) < self.seq_len:
            pad_len = self.seq_len - len(seq)
            padding = [list(seq[0]) for _ in range(pad_len)]
            return padding + seq
        return seq

    def __len__(self) -> int:
        return len(self.X)

    def __getitem__(self, idx: int):
        seq = torch.tensor(self.X[idx], dtype=torch.float32)
        target = torch.tensor(self.y[idx], dtype=torch.float32)
        return seq, target
