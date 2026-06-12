"""
Evaluation and visualisation utilities for the VideoMAE component.
"""

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import torch
from sklearn.metrics import roc_auc_score
from torch.utils.tensorboard import SummaryWriter


def evaluate(
    model,
    loader,
    device: str,
    epoch: int,
    writer: SummaryWriter,
) -> tuple[float, float]:
    """
    Compute snippet-level AUC-ROC and video-level crime classification
    accuracy on the test loader.

    AUC is computed over smoothed per-snippet anomaly scores to mirror
    the smoothing applied during live inference.

    Returns:
        (auc, cls_acc)
    """
    model.eval()

    all_scores:       list[float] = []
    all_clip_labels:  list[float] = []
    all_pred_classes: list[int]   = []
    all_true_classes: list[int]   = []

    with torch.no_grad():
        for batch in loader:
            features      = batch["features"].to(device)
            magnitudes    = batch["magnitudes"].to(device)
            clip_labels   = batch["clip_labels"].numpy()
            crime_classes = batch["crime_class"].numpy()

            anomaly_scores, class_logits = model(features, magnitudes)
            anomaly_scores = anomaly_scores.cpu().numpy()
            pred_classes   = class_logits.argmax(dim=-1).cpu().numpy()

            for i in range(len(anomaly_scores)):
                raw      = anomaly_scores[i]
                smoothed = np.convolve(raw, np.ones(5) / 5, mode="same") if len(raw) >= 5 else raw
                all_scores.extend(smoothed.tolist())
                all_clip_labels.extend(clip_labels[i].tolist())

            for i in range(len(crime_classes)):
                if batch["video_label"][i].item() == 1:
                    all_pred_classes.append(int(pred_classes[i]))
                    all_true_classes.append(int(crime_classes[i]))

    auc = (
        roc_auc_score(all_clip_labels, all_scores)
        if len(set(all_clip_labels)) >= 2
        else 0.0
    )

    cls_acc = 0.0
    if all_true_classes:
        correct = sum(p == t for p, t in zip(all_pred_classes, all_true_classes))
        cls_acc = correct / len(all_true_classes)

    writer.add_scalar("Val/AUC",    auc,     epoch)
    writer.add_scalar("Val/ClsAcc", cls_acc, epoch)

    return auc, cls_acc


def save_training_curve(
    history_loss: list[float],
    history_auc:  list[tuple[int, float]],
    output_path:  str,
    target_auc:   float = 0.84,
) -> None:
    """Save a dual-axis loss + AUC training curve to disk."""
    fig, ax1 = plt.subplots(figsize=(12, 5))

    ax1.plot(history_loss, color="steelblue", label="Loss")
    ax1.set_xlabel("Epoch")
    ax1.set_ylabel("Loss", color="steelblue")
    ax1.tick_params(axis="y", labelcolor="steelblue")

    if history_auc:
        ax2 = ax1.twinx()
        ep, au = zip(*history_auc)
        ax2.plot(ep, au, "o-", color="coral", label="AUC")
        ax2.set_ylabel("AUC", color="coral")
        ax2.set_ylim(0.5, 1.0)
        ax2.tick_params(axis="y", labelcolor="coral")
        ax2.axhline(
            y=target_auc, color="coral", linestyle="--",
            alpha=0.4, label=f"Target {target_auc}"
        )

    plt.title("Training Curve — VideoMAE + CrimeTransformer")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close(fig)
    print(f"Training curve → {output_path}")