import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.checkpoint import checkpoint as grad_ckpt

from .graph import Graph


class DropPath(nn.Module):
    def __init__(self, p=0.0):
        super().__init__()
        self.p = p

    def forward(self, x):
        if not self.training or self.p == 0.0:
            return x
        keep = 1.0 - self.p
        mask = (
            torch.rand((x.shape[0],) + (1,) * (x.ndim - 1), dtype=x.dtype, device=x.device)
            .add_(keep - 1)
            .clamp_(0, 1)
        )
        return x * mask / keep


class AdaptiveGC(nn.Module):
    def __init__(self, in_c, out_c):
        super().__init__()
        self.W = nn.Conv2d(in_c, out_c * 3, 1, bias=False)
        self.B = nn.Parameter(torch.zeros(3, 17, 17))
        self.log_alpha = nn.Parameter(torch.tensor(-3.0))
        self.Wq = nn.Parameter(torch.randn(16, in_c) * 0.25)
        self.Wk = nn.Parameter(torch.randn(16, in_c) * 0.25)
        self.conf_gate = nn.Sequential(nn.Linear(17, 17), nn.Sigmoid())
        self.bn = nn.BatchNorm2d(out_c)

    def forward(self, x, A, conf):
        N, C, T, V = x.shape
        feat = self.W(x).reshape(N, 3, -1, T, V)
        xm = x.mean(2).permute(0, 2, 1)
        xm = F.normalize(xm, p=2, dim=-1)
        logits = (xm @ self.Wq.T @ (xm @ self.Wk.T).transpose(1, 2)).clamp(-10, 10) * 0.25
        A_dyn = F.softmax(logits, dim=-1)
        gate = self.conf_gate(conf.mean(1))
        A_eff = (
            A.unsqueeze(0)
            + self.B.unsqueeze(0)
            + torch.clamp(self.log_alpha, max=5.0).exp() * A_dyn.unsqueeze(1)
        ) * (gate[:, :, None] * gate[:, None, :]).unsqueeze(1)
        return self.bn(torch.einsum("nkctv,nkvw->nkctw", feat, A_eff).sum(1))


class MultiScaleTCN(nn.Module):
    def __init__(self, in_c, out_c, stride=1):
        super().__init__()
        b = out_c // 4

        def br(k, d=1):
            pad = (k + (k - 1) * (d - 1)) // 2
            return nn.Sequential(
                nn.Conv2d(in_c, b, 1, bias=False),
                nn.BatchNorm2d(b),
                nn.ReLU(True),
                nn.Conv2d(
                    b, b, (k, 1),
                    stride=(stride, 1),
                    padding=(pad, 0),
                    dilation=(d, 1),
                    bias=False,
                ),
                nn.BatchNorm2d(b),
            )

        self.br1 = br(3)
        self.br2 = br(5)
        self.br3 = br(7, 2)
        self.br4 = nn.Sequential(
            nn.Conv2d(in_c, b, 1, bias=False),
            nn.BatchNorm2d(b),
            nn.ReLU(True),
            nn.AvgPool2d((3, 1), stride=(stride, 1), padding=(1, 0)),
            nn.BatchNorm2d(b),
        )

    def forward(self, x):
        return torch.cat([self.br1(x), self.br2(x), self.br3(x), self.br4(x)], dim=1)


class TemporalAttn(nn.Module):
    def __init__(self, d, max_len=64):
        super().__init__()
        self.norm1 = nn.LayerNorm(d)
        self.norm2 = nn.LayerNorm(d)
        self.attn = nn.MultiheadAttention(d, 8, dropout=0.1, batch_first=True)
        self.ffn = nn.Sequential(
            nn.Linear(d, d * 2),
            nn.GELU(),
            nn.Dropout(0.1),
            nn.Linear(d * 2, d),
            nn.Dropout(0.1),
        )
        self.pos_embed = nn.Parameter(torch.zeros(1, max_len, d))
        nn.init.trunc_normal_(self.pos_embed, std=0.02)

    def forward(self, x):
        z = x.mean(3).permute(0, 2, 1)
        z = z + self.pos_embed[:, :z.shape[1]]
        n = self.norm1(z)
        z2, _ = self.attn(n, n, n)
        z = z + z2 + self.ffn(self.norm2(z + z2))
        return x + z.permute(0, 2, 1).unsqueeze(3)


class CrimeSkelBlock(nn.Module):
    def __init__(self, in_c, out_c, stride=1, use_attn=False, dpr=0.0, use_grad_ckpt=False):
        super().__init__()
        self._stride = stride
        self._use_grad_ckpt = use_grad_ckpt
        self.register_buffer("A", Graph().A)
        self.agc = AdaptiveGC(in_c, out_c)
        self.act1 = nn.ReLU(True)
        self.tcn = MultiScaleTCN(out_c, out_c, stride)
        self.bn = nn.BatchNorm2d(out_c)
        if in_c != out_c or stride != 1:
            self.res = nn.Sequential(
                nn.Conv2d(in_c, out_c, 1, stride=(stride, 1), bias=False),
                nn.BatchNorm2d(out_c),
            )
        else:
            self.res = nn.Identity()
        self.drop = DropPath(dpr)
        self.attn = TemporalAttn(out_c) if use_attn else None
        self.act2 = nn.ReLU(True)

    def _inner(self, x, conf, A):
        res = self.res(x)
        out = self.act1(self.agc(x, A, conf))
        return self.act2(self.drop(self.bn(self.tcn(out))) + res)

    def forward(self, x, conf):
        if self._use_grad_ckpt and self.training:
            out = grad_ckpt(self._inner, x, conf, self.A, use_reentrant=False)
        else:
            out = self._inner(x, conf, self.A)
        if self.attn:
            out = self.attn(out)
        if self._stride > 1:
            conf = F.max_pool1d(conf.permute(0, 2, 1), self._stride, stride=self._stride).permute(0, 2, 1)
        return out, conf


AdaptiveGraphConv = AdaptiveGC
MultiScaleTemporalConv = MultiScaleTCN
TemporalAttention = TemporalAttn
