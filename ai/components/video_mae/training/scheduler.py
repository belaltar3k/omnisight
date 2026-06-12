"""
Warmup + cosine decay learning rate scheduler.

Not a PyTorch LRScheduler subclass — call .step(epoch) manually
at the start of each epoch to get the current LR back.
"""

import math


class WarmupCosineScheduler:
    """
    Linear warmup for `warmup_epochs`, then cosine decay to `min_lr`.

    Args:
        optimizer:     the AdamW (or any) optimiser to control.
        warmup_epochs: number of linear ramp-up epochs.
        total_epochs:  total training epochs.
        min_lr:        floor for the cosine tail.
    """

    def __init__(
        self,
        optimizer,
        warmup_epochs: int,
        total_epochs:  int,
        min_lr:        float = 1e-6,
    ):
        self.optimizer     = optimizer
        self.warmup_epochs = warmup_epochs
        self.total_epochs  = total_epochs
        self.min_lr        = min_lr
        self.base_lrs      = [pg["lr"] for pg in optimizer.param_groups]

    def step(self, epoch: int) -> float:
        """Update LR for `epoch` and return the new value."""
        if epoch < self.warmup_epochs:
            scale = (epoch + 1) / self.warmup_epochs
        else:
            progress = (epoch - self.warmup_epochs) / (
                self.total_epochs - self.warmup_epochs
            )
            scale = 0.5 * (1.0 + math.cos(math.pi * progress))
            scale = max(scale, self.min_lr / self.base_lrs[0])

        for pg, base_lr in zip(self.optimizer.param_groups, self.base_lrs):
            pg["lr"] = base_lr * scale

        return self.optimizer.param_groups[0]["lr"]