import csv
import numpy as np
import torch


def find_optimal_threshold(
    scores: torch.Tensor,
    targets: torch.Tensor,
    n_thresholds: int = 100,
) -> tuple[float, float]:
    """Grid-search for the decision threshold that maximises F1."""
    thresholds = np.linspace(0.05, 0.95, n_thresholds)
    best_f1, best_thresh = 0.0, 0.5

    for th in thresholds:
        preds = (scores > th).int()
        tp = ((preds == 1) & (targets == 1)).sum().float()
        fp = ((preds == 1) & (targets == 0)).sum().float()
        fn = ((preds == 0) & (targets == 1)).sum().float()
        f1 = (2 * tp) / (2 * tp + fp + fn + 1e-8)
        if f1 > best_f1:
            best_f1, best_thresh = f1.item(), th

    return best_thresh, best_f1


def save_confusion_matrix(
    cm_tensor: torch.Tensor,
    class_names: list[str],
    path: str,
) -> None:
    cm = cm_tensor.cpu().numpy()
    with open(path, "w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow([""] + class_names)
        for i, row in enumerate(cm):
            writer.writerow([class_names[i]] + list(row))