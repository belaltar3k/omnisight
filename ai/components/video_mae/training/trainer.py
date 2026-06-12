"""
Full training loop for VideoMAE + CrimeTransformer.

Handles:
    - Weighted sampling (2× weight for anomaly videos)
    - Warmup + cosine LR decay
    - MIL ranking loss + ramp-in classification loss
    - Gradient clipping
    - TensorBoard logging
    - Best-model checkpoint saving
    - Early stopping
"""

import os

import numpy as np
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader, WeightedRandomSampler
from torch.utils.tensorboard import SummaryWriter
from tqdm import tqdm

from ..config    import Config
from ..data      import UCFCrimeDataset, load_annotations
from ..data      import NUM_CLASSES
from ..models    import CrimeTransformer
from .losses     import RTFMLoss
from .metrics    import evaluate, save_training_curve
from .scheduler  import WarmupCosineScheduler


def _seed(seed: int) -> None:
    import random
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.benchmark = True


def train(cfg: Config | None = None) -> None:
    cfg    = cfg or Config()
    device = cfg.device if torch.cuda.is_available() else "cpu"

    _seed(cfg.seed)
    os.makedirs(cfg.checkpoint_dir, exist_ok=True)
    os.makedirs(cfg.log_dir, exist_ok=True)

    # ── Annotations + datasets ───────────────────────────────────
    annotations = load_annotations(cfg.anno_file)

    train_ds = UCFCrimeDataset(
        cfg.feature_dir, "train", annotations,
        num_snippets=cfg.num_snippets, is_train=True,
    )
    test_ds = UCFCrimeDataset(
        cfg.feature_dir, "test", annotations,
        num_snippets=cfg.num_snippets, is_train=False,
    )

    weights = train_ds.get_sample_weights()
    sampler = WeightedRandomSampler(weights, len(weights), replacement=True)

    loader_kw = dict(num_workers=cfg.num_workers, pin_memory=True)
    train_loader = DataLoader(
        train_ds, batch_size=cfg.batch_size,
        sampler=sampler, drop_last=True, **loader_kw,
    )
    test_loader = DataLoader(
        test_ds, batch_size=cfg.batch_size,
        shuffle=False, **loader_kw,
    )

    # ── Model ────────────────────────────────────────────────────
    model = CrimeTransformer(
        feature_dim  = cfg.feature_dim,
        num_classes  = NUM_CLASSES,
        num_snippets = cfg.num_snippets,
        d_model      = cfg.d_model,
        nhead        = cfg.nhead,
        num_layers   = cfg.num_layers,
        dropout      = cfg.dropout,
    ).to(device)

    n_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    print(f"Model parameters: {n_params:,}")

    # ── Optimiser + scheduler + loss ─────────────────────────────
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=cfg.lr, weight_decay=cfg.weight_decay
    )
    scheduler = WarmupCosineScheduler(optimizer, cfg.warmup_epochs, cfg.epochs)
    mil_loss  = RTFMLoss(
        margin        = cfg.mil_margin,
        lambda_smooth = cfg.mil_lambda_smooth,
        lambda_sparse = cfg.mil_lambda_sparse,
        k             = cfg.mil_top_k,
    )
    writer = SummaryWriter(cfg.log_dir)

    # ── Training state ───────────────────────────────────────────
    best_auc         = 0.0
    patience_counter = 0
    history_loss:    list[float]            = []
    history_auc:     list[tuple[int, float]] = []

    print(f"\nStarting training — {cfg.epochs} epochs  |  device: {device}")
    print(f"Warmup: {cfg.warmup_epochs} epochs, then cosine decay")
    print("─" * 65)

    for epoch in range(cfg.epochs):
        model.train()
        epoch_loss = epoch_mil = epoch_cls = 0.0
        current_lr = scheduler.step(epoch)

        pbar = tqdm(train_loader, desc=f"Epoch {epoch+1:02d}/{cfg.epochs}", leave=False)
        for batch in pbar:
            features      = batch["features"].to(device)
            magnitudes    = batch["magnitudes"].to(device)
            video_labels  = batch["video_label"].to(device)
            crime_classes = batch["crime_class"].to(device)

            optimizer.zero_grad()
            anomaly_scores, class_logits = model(features, magnitudes)

            loss_mil = mil_loss(anomaly_scores, magnitudes, video_labels)
            loss_cls = F.cross_entropy(
                class_logits, crime_classes,
                label_smoothing=cfg.label_smoothing,
            )

            # Ramp classification loss in over warmup period
            cls_weight = min(1.0, epoch / max(cfg.warmup_epochs, 1)) * cfg.cls_loss_max_weight
            loss       = loss_mil + cls_weight * loss_cls

            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()

            epoch_loss += loss.item()
            epoch_mil  += loss_mil.item()
            epoch_cls  += loss_cls.item()

            pbar.set_postfix({"loss": f"{loss.item():.4f}"})

        n_batches = len(train_loader)
        avg_loss  = epoch_loss / n_batches
        avg_mil   = epoch_mil  / n_batches
        avg_cls   = epoch_cls  / n_batches
        history_loss.append(avg_loss)

        writer.add_scalar("Train/Loss",    avg_loss,   epoch)
        writer.add_scalar("Train/MILLoss", avg_mil,    epoch)
        writer.add_scalar("Train/ClsLoss", avg_cls,    epoch)
        writer.add_scalar("Train/LR",      current_lr, epoch)

        # ── Evaluate every 5 epochs ───────────────────────────────
        if (epoch + 1) % 5 == 0:
            auc, cls_acc = evaluate(model, test_loader, device, epoch, writer)
            history_auc.append((epoch + 1, auc))

            marker = ""
            if auc > best_auc:
                best_auc         = auc
                patience_counter = 0
                torch.save(
                    {
                        "epoch":       epoch + 1,
                        "model_state": model.state_dict(),
                        "optimizer":   optimizer.state_dict(),
                        "auc":         auc,
                        "cls_acc":     cls_acc,
                        "config": {
                            "feature_dim":   cfg.feature_dim,
                            "num_classes":   NUM_CLASSES,
                            "num_snippets":  cfg.num_snippets,
                        },
                    },
                    os.path.join(cfg.checkpoint_dir, "best_model.pth"),
                )
                marker = "  ← best"
            else:
                patience_counter += 1

            print(
                f"Epoch {epoch+1:02d} | Loss {avg_loss:.4f} "
                f"(MIL {avg_mil:.4f} CLS {avg_cls:.4f}) | "
                f"AUC {auc:.4f} | ClsAcc {cls_acc:.3f} | "
                f"LR {current_lr:.2e}{marker}"
            )

            if patience_counter >= cfg.patience:
                print(f"\nEarly stopping at epoch {epoch + 1}")
                break

        else:
            warmup_tag = " [warmup]" if epoch < cfg.warmup_epochs else ""
            print(
                f"Epoch {epoch+1:02d} | Loss {avg_loss:.4f} "
                f"(MIL {avg_mil:.4f} CLS {avg_cls:.4f}) | "
                f"LR {current_lr:.2e}{warmup_tag}"
            )

    writer.close()

    save_training_curve(
        history_loss,
        history_auc,
        os.path.join(cfg.checkpoint_dir, "training_curve.png"),
    )

    print(f"\nBest AUC : {best_auc:.4f}")
    print(f"Model    : {cfg.checkpoint_dir}/best_model.pth")