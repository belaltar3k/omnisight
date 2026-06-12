import torch


class ExponentialMovingAverage:
    """
    Maintains a shadow copy of model weights updated with EMA.

    Usage:
        ema = ExponentialMovingAverage(model, decay=0.995)
        # after each optimiser step:
        ema.update()
        # before validation:
        ema.apply()
        # … run eval …
        ema.restore()
    """

    def __init__(self, model: torch.nn.Module, decay: float = 0.999):
        self.model   = model
        self.decay   = decay
        self.shadow  = {k: v.data.clone() for k, v in model.state_dict().items()}
        self._backup: dict = {}

    def update(self) -> None:
        with torch.no_grad():
            for k, v in self.model.state_dict().items():
                if k in self.shadow:
                    self.shadow[k] = self.shadow[k] * self.decay + v.data * (1 - self.decay)

    def apply(self) -> None:
        """Swap live weights → EMA weights (saves live weights for restore)."""
        self._backup = {k: v.data.clone() for k, v in self.model.state_dict().items()}
        self.model.load_state_dict(self.shadow)

    def restore(self) -> None:
        """Restore original live weights after evaluation."""
        self.model.load_state_dict(self._backup)
        self._backup = {}