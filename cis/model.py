from __future__ import annotations

try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
except Exception:  # pragma: no cover - optional runtime dependency
    torch = None
    nn = None
    F = None


if torch is not None:
    class TemporalGNNLayer(nn.Module):
        def __init__(self, in_features: int, out_features: int):
            super().__init__()
            self.linear = nn.Linear(in_features, out_features)

        def forward(self, x: torch.Tensor, adj: torch.Tensor) -> torch.Tensor:
            out = torch.matmul(adj, x)
            out = self.linear(out)
            return F.relu(out)


    class AnticipatoryLSTMGNN(nn.Module):
        def __init__(
            self,
            input_dim: int = 6,
            hidden_dim: int = 128,
            gnn_hidden: int = 64,
            num_nodes: int = 100,
            output_dim: int = 3,
        ):
            super().__init__()
            self.lstm = nn.LSTM(input_dim, hidden_dim, batch_first=True, bidirectional=True)
            self.gnn1 = TemporalGNNLayer(hidden_dim * 2, gnn_hidden)
            self.gnn2 = TemporalGNNLayer(gnn_hidden, gnn_hidden)
            self.fc = nn.Linear(gnn_hidden, output_dim)
            self.num_nodes = num_nodes

        def forward(self, x_seq: torch.Tensor, adj_seq: torch.Tensor) -> torch.Tensor:
            lstm_out, _ = self.lstm(x_seq)
            node_features = lstm_out.unsqueeze(2).expand(-1, -1, self.num_nodes, -1)
            last_node_features = node_features[:, -1, :, :]
            adj_last = adj_seq[:, -1, :, :]

            x = self.gnn1(last_node_features, adj_last)
            x = self.gnn2(x, adj_last)
            x = x.mean(dim=1)
            return self.fc(x)
else:
    class TemporalGNNLayer:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("PyTorch is required to use cis.model")


    class AnticipatoryLSTMGNN:
        def __init__(self, *args, **kwargs):
            raise RuntimeError("PyTorch is required to use cis.model")
