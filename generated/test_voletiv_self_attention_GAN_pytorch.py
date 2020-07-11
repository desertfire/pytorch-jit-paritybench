import sys
_module = sys.modules[__name__]
del sys
parameters = _module
sagan_models = _module
test = _module
train = _module
trainer = _module
utils = _module

from _paritybench_helpers import _mock_config, patch_functional
from unittest.mock import mock_open, MagicMock
from torch.autograd import Function
from torch.nn import Module
import abc, collections, copy, enum, functools, inspect, itertools, logging, math, matplotlib, numbers, numpy, pandas, queue, random, re, scipy, sklearn, string, tensorflow, time, torch, torchaudio, torchtext, torchvision, types, typing, uuid, warnings
import numpy as np
from torch import Tensor
patch_functional()
open = mock_open()
yaml = logging = sys = argparse = MagicMock()
ArgumentParser = argparse.ArgumentParser
_global_config = args = argv = cfg = config = params = _mock_config()
argparse.ArgumentParser.return_value.parse_args.return_value = _global_config
yaml.load.return_value = _global_config
sys.argv = _global_config
__version__ = '1.0.0'
xrange = range
wraps = functools.wraps


import numpy as np


import torch


import torch.nn as nn


import torch.nn.functional as F


from torch.nn.utils import spectral_norm


from torch.nn.init import xavier_uniform_


import random


import time


import torchvision.utils as vutils


from torch.backends import cudnn


import matplotlib


import matplotlib.pyplot as plt


import torchvision.datasets as dset


from torchvision import transforms


def snconv2d(in_channels, out_channels, kernel_size, stride=1, padding=0, dilation=1, groups=1, bias=True):
    return spectral_norm(nn.Conv2d(in_channels=in_channels, out_channels=out_channels, kernel_size=kernel_size, stride=stride, padding=padding, dilation=dilation, groups=groups, bias=bias))


class Self_Attn(nn.Module):
    """ Self attention Layer"""

    def __init__(self, in_channels):
        super(Self_Attn, self).__init__()
        self.in_channels = in_channels
        self.snconv1x1_theta = snconv2d(in_channels=in_channels, out_channels=in_channels // 8, kernel_size=1, stride=1, padding=0)
        self.snconv1x1_phi = snconv2d(in_channels=in_channels, out_channels=in_channels // 8, kernel_size=1, stride=1, padding=0)
        self.snconv1x1_g = snconv2d(in_channels=in_channels, out_channels=in_channels // 2, kernel_size=1, stride=1, padding=0)
        self.snconv1x1_attn = snconv2d(in_channels=in_channels // 2, out_channels=in_channels, kernel_size=1, stride=1, padding=0)
        self.maxpool = nn.MaxPool2d(2, stride=2, padding=0)
        self.softmax = nn.Softmax(dim=-1)
        self.sigma = nn.Parameter(torch.zeros(1))

    def forward(self, x):
        """
            inputs :
                x : input feature maps(B X C X W X H)
            returns :
                out : self attention value + input feature 
                attention: B X N X N (N is Width*Height)
        """
        _, ch, h, w = x.size()
        theta = self.snconv1x1_theta(x)
        theta = theta.view(-1, ch // 8, h * w)
        phi = self.snconv1x1_phi(x)
        phi = self.maxpool(phi)
        phi = phi.view(-1, ch // 8, h * w // 4)
        attn = torch.bmm(theta.permute(0, 2, 1), phi)
        attn = self.softmax(attn)
        g = self.snconv1x1_g(x)
        g = self.maxpool(g)
        g = g.view(-1, ch // 2, h * w // 4)
        attn_g = torch.bmm(g, attn.permute(0, 2, 1))
        attn_g = attn_g.view(-1, ch // 2, h, w)
        attn_g = self.snconv1x1_attn(attn_g)
        out = x + self.sigma * attn_g
        return out


class ConditionalBatchNorm2d(nn.Module):

    def __init__(self, num_features, num_classes):
        super().__init__()
        self.num_features = num_features
        self.bn = nn.BatchNorm2d(num_features, momentum=0.001, affine=False)
        self.embed = nn.Embedding(num_classes, num_features * 2)
        self.embed.weight.data[:, :num_features].fill_(1.0)
        self.embed.weight.data[:, num_features:].zero_()

    def forward(self, x, y):
        out = self.bn(x)
        gamma, beta = self.embed(y).chunk(2, 1)
        out = gamma.view(-1, self.num_features, 1, 1) * out + beta.view(-1, self.num_features, 1, 1)
        return out


class GenBlock(nn.Module):

    def __init__(self, in_channels, out_channels, num_classes):
        super(GenBlock, self).__init__()
        self.cond_bn1 = ConditionalBatchNorm2d(in_channels, num_classes)
        self.relu = nn.ReLU(inplace=True)
        self.snconv2d1 = snconv2d(in_channels=in_channels, out_channels=out_channels, kernel_size=3, stride=1, padding=1)
        self.cond_bn2 = ConditionalBatchNorm2d(out_channels, num_classes)
        self.snconv2d2 = snconv2d(in_channels=out_channels, out_channels=out_channels, kernel_size=3, stride=1, padding=1)
        self.snconv2d0 = snconv2d(in_channels=in_channels, out_channels=out_channels, kernel_size=1, stride=1, padding=0)

    def forward(self, x, labels):
        x0 = x
        x = self.cond_bn1(x, labels)
        x = self.relu(x)
        x = F.interpolate(x, scale_factor=2, mode='nearest')
        x = self.snconv2d1(x)
        x = self.cond_bn2(x, labels)
        x = self.relu(x)
        x = self.snconv2d2(x)
        x0 = F.interpolate(x0, scale_factor=2, mode='nearest')
        x0 = self.snconv2d0(x0)
        out = x + x0
        return out


def init_weights(m):
    if type(m) == nn.Linear or type(m) == nn.Conv2d:
        xavier_uniform_(m.weight)
        m.bias.data.fill_(0.0)


def snlinear(in_features, out_features):
    return spectral_norm(nn.Linear(in_features=in_features, out_features=out_features))


class Generator(nn.Module):
    """Generator."""

    def __init__(self, z_dim, g_conv_dim, num_classes):
        super(Generator, self).__init__()
        self.z_dim = z_dim
        self.g_conv_dim = g_conv_dim
        self.snlinear0 = snlinear(in_features=z_dim, out_features=g_conv_dim * 16 * 4 * 4)
        self.block1 = GenBlock(g_conv_dim * 16, g_conv_dim * 16, num_classes)
        self.block2 = GenBlock(g_conv_dim * 16, g_conv_dim * 8, num_classes)
        self.block3 = GenBlock(g_conv_dim * 8, g_conv_dim * 4, num_classes)
        self.self_attn = Self_Attn(g_conv_dim * 4)
        self.block4 = GenBlock(g_conv_dim * 4, g_conv_dim * 2, num_classes)
        self.block5 = GenBlock(g_conv_dim * 2, g_conv_dim, num_classes)
        self.bn = nn.BatchNorm2d(g_conv_dim, eps=1e-05, momentum=0.0001, affine=True)
        self.relu = nn.ReLU(inplace=True)
        self.snconv2d1 = snconv2d(in_channels=g_conv_dim, out_channels=3, kernel_size=3, stride=1, padding=1)
        self.tanh = nn.Tanh()
        self.apply(init_weights)

    def forward(self, z, labels):
        act0 = self.snlinear0(z)
        act0 = act0.view(-1, self.g_conv_dim * 16, 4, 4)
        act1 = self.block1(act0, labels)
        act2 = self.block2(act1, labels)
        act3 = self.block3(act2, labels)
        act3 = self.self_attn(act3)
        act4 = self.block4(act3, labels)
        act5 = self.block5(act4, labels)
        act5 = self.bn(act5)
        act5 = self.relu(act5)
        act6 = self.snconv2d1(act5)
        act6 = self.tanh(act6)
        return act6


class DiscOptBlock(nn.Module):

    def __init__(self, in_channels, out_channels):
        super(DiscOptBlock, self).__init__()
        self.snconv2d1 = snconv2d(in_channels=in_channels, out_channels=out_channels, kernel_size=3, stride=1, padding=1)
        self.relu = nn.ReLU(inplace=True)
        self.snconv2d2 = snconv2d(in_channels=out_channels, out_channels=out_channels, kernel_size=3, stride=1, padding=1)
        self.downsample = nn.AvgPool2d(2)
        self.snconv2d0 = snconv2d(in_channels=in_channels, out_channels=out_channels, kernel_size=1, stride=1, padding=0)

    def forward(self, x):
        x0 = x
        x = self.snconv2d1(x)
        x = self.relu(x)
        x = self.snconv2d2(x)
        x = self.downsample(x)
        x0 = self.downsample(x0)
        x0 = self.snconv2d0(x0)
        out = x + x0
        return out


class DiscBlock(nn.Module):

    def __init__(self, in_channels, out_channels):
        super(DiscBlock, self).__init__()
        self.relu = nn.ReLU(inplace=True)
        self.snconv2d1 = snconv2d(in_channels=in_channels, out_channels=out_channels, kernel_size=3, stride=1, padding=1)
        self.snconv2d2 = snconv2d(in_channels=out_channels, out_channels=out_channels, kernel_size=3, stride=1, padding=1)
        self.downsample = nn.AvgPool2d(2)
        self.ch_mismatch = False
        if in_channels != out_channels:
            self.ch_mismatch = True
        self.snconv2d0 = snconv2d(in_channels=in_channels, out_channels=out_channels, kernel_size=1, stride=1, padding=0)

    def forward(self, x, downsample=True):
        x0 = x
        x = self.relu(x)
        x = self.snconv2d1(x)
        x = self.relu(x)
        x = self.snconv2d2(x)
        if downsample:
            x = self.downsample(x)
        if downsample or self.ch_mismatch:
            x0 = self.snconv2d0(x0)
            if downsample:
                x0 = self.downsample(x0)
        out = x + x0
        return out


def sn_embedding(num_embeddings, embedding_dim):
    return spectral_norm(nn.Embedding(num_embeddings=num_embeddings, embedding_dim=embedding_dim))


class Discriminator(nn.Module):
    """Discriminator."""

    def __init__(self, d_conv_dim, num_classes):
        super(Discriminator, self).__init__()
        self.d_conv_dim = d_conv_dim
        self.opt_block1 = DiscOptBlock(3, d_conv_dim)
        self.block1 = DiscBlock(d_conv_dim, d_conv_dim * 2)
        self.self_attn = Self_Attn(d_conv_dim * 2)
        self.block2 = DiscBlock(d_conv_dim * 2, d_conv_dim * 4)
        self.block3 = DiscBlock(d_conv_dim * 4, d_conv_dim * 8)
        self.block4 = DiscBlock(d_conv_dim * 8, d_conv_dim * 16)
        self.block5 = DiscBlock(d_conv_dim * 16, d_conv_dim * 16)
        self.relu = nn.ReLU(inplace=True)
        self.snlinear1 = snlinear(in_features=d_conv_dim * 16, out_features=1)
        self.sn_embedding1 = sn_embedding(num_classes, d_conv_dim * 16)
        self.apply(init_weights)
        xavier_uniform_(self.sn_embedding1.weight)

    def forward(self, x, labels):
        h0 = self.opt_block1(x)
        h1 = self.block1(h0)
        h1 = self.self_attn(h1)
        h2 = self.block2(h1)
        h3 = self.block3(h2)
        h4 = self.block4(h3)
        h5 = self.block5(h4, downsample=False)
        h5 = self.relu(h5)
        h6 = torch.sum(h5, dim=[2, 3])
        output1 = torch.squeeze(self.snlinear1(h6))
        h_labels = self.sn_embedding1(labels)
        proj = torch.mul(h6, h_labels)
        output2 = torch.sum(proj, dim=[1])
        output = output1 + output2
        return output


import torch
from torch.nn import MSELoss, ReLU
from _paritybench_helpers import _mock_config, _mock_layer, _paritybench_base, _fails_compile


TESTCASES = [
    # (nn.Module, init_args, forward_args, jit_compiles)
    (ConditionalBatchNorm2d,
     lambda: ([], {'num_features': 4, 'num_classes': 4}),
     lambda: ([torch.rand([4, 4, 4, 4]), torch.zeros([4], dtype=torch.int64)], {}),
     True),
    (DiscBlock,
     lambda: ([], {'in_channels': 4, 'out_channels': 4}),
     lambda: ([torch.rand([4, 4, 4, 4])], {}),
     False),
    (DiscOptBlock,
     lambda: ([], {'in_channels': 4, 'out_channels': 4}),
     lambda: ([torch.rand([4, 4, 4, 4])], {}),
     True),
    (Discriminator,
     lambda: ([], {'d_conv_dim': 4, 'num_classes': 4}),
     lambda: ([torch.rand([4, 3, 64, 64]), torch.zeros([4], dtype=torch.int64)], {}),
     False),
    (Generator,
     lambda: ([], {'z_dim': 4, 'g_conv_dim': 4, 'num_classes': 4}),
     lambda: ([torch.rand([4, 4, 4, 4]), torch.zeros([64], dtype=torch.int64)], {}),
     False),
    (Self_Attn,
     lambda: ([], {'in_channels': 18}),
     lambda: ([torch.rand([4, 18, 64, 64])], {}),
     True),
]

class Test_voletiv_self_attention_GAN_pytorch(_paritybench_base):
    def test_000(self):
        self._check(*TESTCASES[0])

    def test_001(self):
        self._check(*TESTCASES[1])

    def test_002(self):
        self._check(*TESTCASES[2])

    def test_003(self):
        self._check(*TESTCASES[3])

    def test_004(self):
        self._check(*TESTCASES[4])

    def test_005(self):
        self._check(*TESTCASES[5])

