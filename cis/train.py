from __future__ import annotations

import argparse
import os

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader

from dataset_preparation import RansomwareSequenceDataset
from model import AnticipatoryLSTMGNN


def train(model: AnticipatoryLSTMGNN, train_loader: DataLoader, val_loader: DataLoader, epochs: int = 10, lr: float = 1e-3):
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=lr)

    for epoch in range(epochs):
        model.train()
        train_loss = 0.0
        for seq, target in train_loader:
            seq = seq.to(device)
            target = target.to(device)
            batch_size = seq.size(0)
            adj_seq = torch.eye(model.num_nodes, device=device).unsqueeze(0).unsqueeze(0)
            adj_seq = adj_seq.repeat(batch_size, seq.size(1), 1, 1)

            optimizer.zero_grad()
            pred = model(seq, adj_seq)
            loss = criterion(pred, target)
            loss.backward()
            optimizer.step()
            train_loss += float(loss.item())

        model.eval()
        val_loss = 0.0
        with torch.no_grad():
            for seq, target in val_loader:
                seq = seq.to(device)
                target = target.to(device)
                batch_size = seq.size(0)
                adj_seq = torch.eye(model.num_nodes, device=device).unsqueeze(0).unsqueeze(0)
                adj_seq = adj_seq.repeat(batch_size, seq.size(1), 1, 1)
                pred = model(seq, adj_seq)
                val_loss += float(criterion(pred, target).item())

        print(
            f"epoch={epoch + 1} train_loss={train_loss / max(1, len(train_loader)):.4f} "
            f"val_loss={val_loss / max(1, len(val_loader)):.4f}"
        )


def make_dummy_data(n: int = 256, seq_len: int = 50):
    X = []
    y = []
    for _ in range(n):
        seq = torch.rand(seq_len, 6).tolist()
        target = torch.rand(3).tolist()
        X.append(seq)
        y.append(target)
    return X, y


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--save", type=str, default="models/lstm_gnn_scripted.pt")
    args = parser.parse_args()
    save_dir = os.path.dirname(args.save)
    if save_dir:
        os.makedirs(save_dir, exist_ok=True)

    X_train, y_train = make_dummy_data(256)
    X_val, y_val = make_dummy_data(64)

    train_ds = RansomwareSequenceDataset(X_train, y_train)
    val_ds = RansomwareSequenceDataset(X_val, y_val)
    train_loader = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=args.batch_size)

    model = AnticipatoryLSTMGNN()
    train(model, train_loader, val_loader, epochs=args.epochs)

    scripted = torch.jit.script(model.cpu())
    torch.jit.save(scripted, args.save)
    print(f"saved scripted model -> {args.save}")


if __name__ == "__main__":
    main()
