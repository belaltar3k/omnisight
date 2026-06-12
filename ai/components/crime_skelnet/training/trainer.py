"""
Main training loop for CrimeSkelNet.

Handles:
    - Weighted sampling to manage class imbalance
    - Gradient accumulation + bfloat16 mixed precision
    - EMA weight averaging
    - Per-epoch F1 / AUC-ROC / AUC-PR metrics
    - Checkpoint saving & resume
    - CSV metrics logging
"""

import csv
import json
import os
import random
import time

import numpy as np
import torch
import torch.nn.functional as F
from torch.utils.data import DataLoader, WeightedRandomSampler
from torchmetrics.classification import (
    BinaryAUROC,
    BinaryAveragePrecision,
    BinaryConfusionMatrix,
    BinaryF1Score,
    BinaryPrecision,
    BinaryRecall,
)
from tqdm import tqdm

from ..config           import Config
from ..data             import SurveillanceDataset
from ..data.taxonomy    import CRIME_CLASSES
from ..models           import CrimeSkelNet
from .augmentation      import cap_normal_class, class_aware_mixup
from .ema               import ExponentialMovingAverage
from .losses            import SoftFocalLoss
from .metrics           import find_optimal_threshold, save_confusion_matrix

torch.set_float32_matmul_precision("high")


# ── Utilities ────────────────────────────────────────────────────────────────

def seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.backends.cudnn.deterministic = False
    torch.backends.cudnn.benchmark     = True


def strip_compiled_prefix(state_dict: dict) -> dict:
    return {k.replace("_orig_mod.", ""): v for k, v in state_dict.items()}


def val_collate_fn(batch):
    xs, ys = zip(*batch)
    return torch.stack(xs), torch.tensor(ys, dtype=torch.long)


def _build_sampler(train_data: list[dict], cfg: Config) -> WeightedRandomSampler:
    labels  = [d["label"] for d in train_data]
    counts  = np.bincount(labels, minlength=cfg.num_classes)
    class_w = 1.0 / np.power(counts + 1e-5, 0.5)
    weights = [
        class_w[d["label"]] * max(1.0, d["T"] / (cfg.clip_seconds * d["fps"]))
        for d in train_data
    ]
    return WeightedRandomSampler(weights, num_samples=len(train_data), replacement=True)


# ── Training entry point ─────────────────────────────────────────────────────

def train(cfg: Config | None = None) -> None:
    cfg = cfg or Config()
    seed_everything(cfg.seed)
    os.makedirs(cfg.checkpoint_dir, exist_ok=True)

    # ── Load index files ─────────────────────────────────────────
    with open(os.path.join(cfg.unified_dir, "train_index.json")) as fh:
        raw_train = json.load(fh)
    with open(os.path.join(cfg.unified_dir, "val_index.json")) as fh:
        val_data  = json.load(fh)

    # ── Model + optimiser ────────────────────────────────────────
    model = CrimeSkelNet(
        num_classes     = cfg.num_classes,
        num_streams     = cfg.num_streams,
        drop_path_rate  = cfg.drop_path_rate,
        use_grad_ckpt   = cfg.use_grad_ckpt,
    ).cuda()

    if cfg.compile_model:
        try:
            model = torch.compile(model, mode=cfg.compile_mode)
            print("torch.compile enabled")
        except Exception as exc:
            print(f"torch.compile unavailable ({exc}); continuing without it.")

    ema  = ExponentialMovingAverage(model, decay=cfg.ema_decay)
    crit = SoftFocalLoss(gamma=cfg.focal_gamma, smoothing=cfg.label_smoothing)
    opt  = torch.optim.AdamW(model.parameters(), lr=cfg.lr, weight_decay=cfg.weight_decay)

    # ── Scheduler ────────────────────────────────────────────────
    normal_cnt = sum(1 for d in raw_train if d["label"] == 0)
    est_size   = min(normal_cnt, cfg.max_normal_clips) + (len(raw_train) - normal_cnt)
    total_steps = ((est_size // cfg.batch_size // cfg.accum_steps) + 1) * cfg.epochs

    sched = torch.optim.lr_scheduler.OneCycleLR(
        opt, max_lr=cfg.lr, total_steps=total_steps, pct_start=cfg.warmup_pct
    )

    # ── Mixed precision ───────────────────────────────────────────
    dtype  = torch.bfloat16 if cfg.use_bf16 else torch.float16
    scaler = torch.amp.GradScaler("cuda", enabled=not cfg.use_bf16)

    # ── Metrics ───────────────────────────────────────────────────
    f1_metric   = BinaryF1Score().cuda()
    recall_m    = BinaryRecall().cuda()
    precision_m = BinaryPrecision().cuda()
    conf_mat    = BinaryConfusionMatrix().cuda()
    auc_roc     = BinaryAUROC().cuda()
    auc_pr      = BinaryAveragePrecision().cuda()

    metrics_path = os.path.join(cfg.checkpoint_dir, "metrics.csv")
    with open(metrics_path, "w", newline="") as fh:
        csv.writer(fh).writerow([
            "epoch", "train_loss", "val_loss",
            "f1", "recall", "precision",
            "auc_roc", "auc_pr",
            "opt_thresh", "opt_f1",
        ])

    # ── Resume from checkpoint ───────────────────────────────────
    best_f1 = best_auc = 0.0
    no_improve = start_epoch = global_step = 0
    latest_ckpt = os.path.join(cfg.checkpoint_dir, "latest_ckpt.pth")

    if os.path.exists(latest_ckpt):
        ck = torch.load(latest_ckpt, map_location="cuda", weights_only=True)
        model.load_state_dict(strip_compiled_prefix(ck["model"]))
        ema.shadow = strip_compiled_prefix(ck["ema_shadow"])
        opt.load_state_dict(ck["opt"])
        sched.load_state_dict(ck["sched"])
        start_epoch  = ck["epoch"] + 1
        best_f1      = ck["best_f1"]
        global_step  = ck.get("global_step", 0)
        best_auc     = ck.get("best_auc", 0.0)
        print(f"Resumed from epoch {start_epoch} (best F1={best_f1:.4f})")

    # ── Data loaders ─────────────────────────────────────────────
    loader_kw = dict(
        batch_size       = cfg.batch_size,
        num_workers      = cfg.num_workers,
        pin_memory       = True,
        persistent_workers = True,
        prefetch_factor  = 4,
    )
    val_loader = DataLoader(
        SurveillanceDataset(val_data, cfg, mode="val", val_clips=cfg.val_num_clips),
        drop_last=False,
        collate_fn=val_collate_fn,
        **loader_kw,
    )

    # ── Epoch loop ───────────────────────────────────────────────
    for epoch in range(start_epoch, cfg.epochs):
        train_data = cap_normal_class(
            raw_train, label=0, max_clips=cfg.max_normal_clips, seed=cfg.seed + epoch
        )
        sampler      = _build_sampler(train_data, cfg)
        train_loader = DataLoader(
            SurveillanceDataset(train_data, cfg, mode="train"),
            sampler=sampler,
            drop_last=True,
            **loader_kw,
        )

        # ── Train ─────────────────────────────────────────────────
        model.train()
        opt.zero_grad(set_to_none=True)
        running_loss = 0.0
        t0 = time.time()

        pbar = tqdm(train_loader, desc=f"Ep {epoch+1:03d}/{cfg.epochs} [Train]", leave=False)
        for step, (x, y) in enumerate(pbar):
            x, y = x.cuda(non_blocking=True), y.cuda(non_blocking=True)

            if random.random() < 0.5:
                x, y_soft = class_aware_mixup(x, y, cfg.num_classes, cfg.mixup_alpha)
            else:
                y_soft = F.one_hot(y, cfg.num_classes).float()

            with torch.amp.autocast("cuda", dtype=dtype):
                loss = crit(model(x), y_soft) / cfg.accum_steps

            if cfg.use_bf16:
                loss.backward()
            else:
                scaler.scale(loss).backward()

            is_last_step = (step + 1) == len(train_loader)
            if (step + 1) % cfg.accum_steps == 0 or is_last_step:
                if cfg.use_bf16:
                    torch.nn.utils.clip_grad_norm_(model.parameters(), cfg.grad_clip)
                    opt.step()
                else:
                    scaler.unscale_(opt)
                    torch.nn.utils.clip_grad_norm_(model.parameters(), cfg.grad_clip)
                    scaler.step(opt)
                    scaler.update()

                opt.zero_grad(set_to_none=True)
                sched.step()
                global_step += 1
                if global_step > 100:
                    ema.update()

            running_loss += loss.item() * cfg.accum_steps
            pbar.set_postfix({"loss": f"{loss.item() * cfg.accum_steps:.4f}"})

        train_loss = running_loss / len(train_loader)
        print(f"Ep {epoch+1:03d} | Loss: {train_loss:.4f} | Time: {(time.time()-t0)/60:.1f}m")

        # ── Validate ───────────────────────────────────────────────
        ema.apply()
        model.eval()
        for m in (f1_metric, recall_m, precision_m, conf_mat, auc_roc, auc_pr):
            m.reset()

        val_loss  = 0.0
        all_scores: list[torch.Tensor] = []
        all_targets: list[torch.Tensor] = []

        with torch.no_grad():
            for x, y in tqdm(val_loader, desc=f"Ep {epoch+1:03d}/{cfg.epochs} [Val]", leave=False):
                y = y.cuda(non_blocking=True)

                if x.dim() == 7:
                    with torch.amp.autocast("cuda", dtype=dtype):
                        logits = torch.stack(
                            [model(x[:, ki].cuda(non_blocking=True)) for ki in range(x.shape[1])],
                            dim=0,
                        ).mean(0)
                else:
                    with torch.amp.autocast("cuda", dtype=dtype):
                        logits = model(x.cuda(non_blocking=True))

                with torch.amp.autocast("cuda", dtype=dtype):
                    val_loss += crit(logits, F.one_hot(y, cfg.num_classes).float()).item()

                anomaly_scores = torch.softmax(logits, dim=1)[:, 1]
                f1_metric.update(anomaly_scores, y)
                recall_m.update(anomaly_scores, y)
                precision_m.update(anomaly_scores, y)
                conf_mat.update(anomaly_scores, y)
                auc_roc.update(anomaly_scores, y)
                auc_pr.update(anomaly_scores, y)
                all_scores.append(anomaly_scores.cpu())
                all_targets.append(y.cpu())

        val_loss /= len(val_loader)
        val_f1    = f1_metric.compute().item()
        val_rec   = recall_m.compute().item()
        val_prec  = precision_m.compute().item()
        val_auc   = auc_roc.compute().item()
        val_pr    = auc_pr.compute().item()
        cm_val    = conf_mat.compute()

        opt_thresh, opt_f1 = find_optimal_threshold(
            torch.cat(all_scores), torch.cat(all_targets)
        )

        print(
            f"         Val → Loss: {val_loss:.4f} | F1: {val_f1:.4f} | "
            f"AUC-ROC: {val_auc:.4f} | AUC-PR: {val_pr:.4f}\n"
            f"                    Recall: {val_rec:.4f} | Prec: {val_prec:.4f} | "
            f"OptThresh: {opt_thresh:.3f} (F1={opt_f1:.4f})"
        )

        with open(metrics_path, "a", newline="") as fh:
            csv.writer(fh).writerow([
                epoch,
                f"{train_loss:.4f}", f"{val_loss:.4f}",
                f"{val_f1:.4f}", f"{val_rec:.4f}", f"{val_prec:.4f}",
                f"{val_auc:.4f}", f"{val_pr:.4f}",
                f"{opt_thresh:.3f}", f"{opt_f1:.4f}",
            ])

        # ── Save best ─────────────────────────────────────────────
        if val_f1 > best_f1 or val_auc > best_auc:
            best_f1  = max(best_f1, val_f1)
            best_auc = max(best_auc, val_auc)
            no_improve = 0
            torch.save(
                model.state_dict(),
                os.path.join(cfg.checkpoint_dir, "best_anomaly_skel.pth"),
            )
            save_confusion_matrix(
                cm_val,
                list(CRIME_CLASSES),
                os.path.join(cfg.checkpoint_dir, f"confusion_ep{epoch+1:03d}.csv"),
            )
            print(f"  ★ NEW BEST  F1={best_f1:.4f}  AUC-ROC={best_auc:.4f}")
        else:
            no_improve += 1
            if no_improve >= cfg.patience:
                print("Early stopping triggered.")
                ema.restore()
                break

        ema.restore()

        torch.save(
            dict(
                epoch=epoch, global_step=global_step,
                model=model.state_dict(), ema_shadow=ema.shadow,
                opt=opt.state_dict(), sched=sched.state_dict(),
                best_f1=best_f1, best_auc=best_auc,
            ),
            latest_ckpt,
        )