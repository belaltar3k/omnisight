import torch
import torch.nn as nn

from .blocks import CrimeSkelBlock


class CrimeSkelNet(nn.Module):
    LAYOUT = [
        (3, 64, 1, False),
        (64, 64, 1, False),
        (64, 64, 1, False),
        (64, 128, 2, False),
        (128, 128, 1, False),
        (128, 128, 1, False),
        (128, 256, 2, True),
        (256, 256, 1, True),
        (256, 256, 1, True),
    ]

    def __init__(self, num_classes=15, num_streams=5, drop_path_rate=0.1, use_grad_ckpt=False):
        super().__init__()
        self.S = num_streams
        self.stream_embed = nn.Embedding(num_streams, 3 * 17)
        self.data_bn = nn.BatchNorm1d(3 * 17)
        self.stream_weight = nn.Parameter(torch.ones(num_streams))
        self.blocks = nn.ModuleList(
            [
                CrimeSkelBlock(
                    ic, oc, s, a,
                    dpr=drop_path_rate * i / (len(self.LAYOUT) - 1),
                    use_grad_ckpt=use_grad_ckpt,
                )
                for i, (ic, oc, s, a) in enumerate(self.LAYOUT)
            ]
        )
        self.head = nn.Sequential(
            nn.Linear(256 * num_streams, 512),
            nn.BatchNorm1d(512),
            nn.GELU(),
            nn.Dropout(0.4),
            nn.Linear(512, num_classes),
        )

    def forward(self, x):
        B, S, C, T, V, M = x.shape
        xs = x.permute(0, 1, 5, 2, 3, 4).contiguous().reshape(B * S * M, C, T, V)
        ids = (
            torch.arange(S, device=x.device)
            .repeat_interleave(M)
            .unsqueeze(0)
            .expand(B, -1)
            .reshape(B * S * M)
        )
        xs = xs + 0.05 * torch.tanh(
            self.stream_embed(ids).reshape(B * S * M, C, V).unsqueeze(2).expand(-1, -1, T, -1)
        )
        xs = (
            self.data_bn(xs.permute(0, 1, 3, 2).reshape(B * S * M, C * V, T))
            .reshape(B * S * M, C, V, T)
            .permute(0, 1, 3, 2)
        )
        conf = xs[:, 2].clamp(0.0, 1.0)
        for blk in self.blocks:
            xs, conf = blk(xs, conf)
        feat = xs.mean(dim=(2, 3)).reshape(B, S, M, 256).mean(2)
        return self.head((feat * torch.sigmoid(self.stream_weight).view(1, S, 1)).reshape(B, S * 256))
