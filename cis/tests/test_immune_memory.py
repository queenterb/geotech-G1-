import unittest

import numpy as np

from cis.immune_memory import ImmuneMemory


class TestImmuneMemory(unittest.TestCase):
    def test_detect_returns_bool(self):
        m = ImmuneMemory(pool_size=16, feature_dim=256)
        antigen = np.zeros(256, dtype=np.float32)
        out = m.detect(antigen)
        self.assertIsInstance(out, bool)

    def test_clonal_selection_runs(self):
        m = ImmuneMemory(pool_size=16, feature_dim=256)
        antigens = [np.ones(256, dtype=np.float32) for _ in range(4)]
        labels = [1, 1, 0, 1]
        m.clonal_selection(antigens, labels, mutation_rate=0.01)
        self.assertGreater(len(m.antibodies), 0)


if __name__ == "__main__":
    unittest.main()
