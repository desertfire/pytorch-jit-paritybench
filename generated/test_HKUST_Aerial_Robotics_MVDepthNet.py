import sys
_module = sys.modules[__name__]
del sys
depthNet_model = _module
example = _module
example2 = _module
visualize = _module

from _paritybench_helpers import _mock_config, patch_functional
from unittest.mock import mock_open, MagicMock
from torch.autograd import Function
from torch.nn import Module
import abc, collections, copy, enum, functools, inspect, itertools, logging, math, numbers, numpy, queue, random, re, scipy, sklearn, string, tensorflow, time, torch, torchaudio, torchtext, torchvision, types, typing, uuid, warnings
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


import torch


import torch.nn as nn


import torch.nn.functional as F


import torch.nn.init as init


from torch.autograd import Variable


from torch import Tensor


import math


import numpy as np


import time


from numpy.linalg import inv


import torch.backends.cudnn as cudnn


def conv_layer(input_channels, output_channels, kernel_size):
    return nn.Sequential(nn.Conv2d(input_channels, output_channels, kernel_size, padding=(kernel_size - 1) / 2, bias=False), nn.BatchNorm2d(output_channels), nn.ReLU())


def depth_layer(input_channels):
    return nn.Sequential(nn.Conv2d(input_channels, 1, 3, padding=1), nn.Sigmoid())


def down_conv_layer(input_channels, output_channels, kernel_size):
    return nn.Sequential(nn.Conv2d(input_channels, output_channels, kernel_size, padding=(kernel_size - 1) / 2, stride=1, bias=False), nn.BatchNorm2d(output_channels), nn.ReLU(), nn.Conv2d(output_channels, output_channels, kernel_size, padding=(kernel_size - 1) / 2, stride=2, bias=False), nn.BatchNorm2d(output_channels), nn.ReLU())


def get_trainable_number(variable):
    num = 1
    shape = list(variable.shape)
    for i in shape:
        num *= i
    return num


def up_conv_layer(input_channels, output_channels, kernel_size):
    return nn.Sequential(nn.Upsample(scale_factor=2, mode='bilinear'), nn.Conv2d(input_channels, output_channels, kernel_size, padding=(kernel_size - 1) / 2, bias=False), nn.BatchNorm2d(output_channels), nn.ReLU())


class depthNet(nn.Module):
    """docstring for depthNet"""

    def __init__(self):
        super(depthNet, self).__init__()
        self.conv1 = down_conv_layer(67, 128, 7)
        self.conv2 = down_conv_layer(128, 256, 5)
        self.conv3 = down_conv_layer(256, 512, 3)
        self.conv4 = down_conv_layer(512, 512, 3)
        self.conv5 = down_conv_layer(512, 512, 3)
        self.upconv5 = up_conv_layer(512, 512, 3)
        self.iconv5 = conv_layer(1024, 512, 3)
        self.upconv4 = up_conv_layer(512, 512, 3)
        self.iconv4 = conv_layer(1024, 512, 3)
        self.disp4 = depth_layer(512)
        self.upconv3 = up_conv_layer(512, 256, 3)
        self.iconv3 = conv_layer(513, 256, 3)
        self.disp3 = depth_layer(256)
        self.upconv2 = up_conv_layer(256, 128, 3)
        self.iconv2 = conv_layer(257, 128, 3)
        self.disp2 = depth_layer(128)
        self.upconv1 = up_conv_layer(128, 64, 3)
        self.iconv1 = conv_layer(65, 64, 3)
        self.disp1 = depth_layer(64)
        total_num = 0
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                init.kaiming_normal(m.weight, mode='fan_out')
                total_num += get_trainable_number(m.weight)
                if m.bias is not None:
                    init.constant(m.bias, 0)
                    total_num += get_trainable_number(m.bias)
            elif isinstance(m, nn.BatchNorm2d):
                init.constant(m.weight, 1)
                total_num += get_trainable_number(m.weight)
                init.constant(m.bias, 0)
                total_num += get_trainable_number(m.bias)
            elif isinstance(m, nn.Linear):
                init.normal(m.weight, std=0.001)
                total_num += get_trainable_number(m.weight)
                if m.bias is not None:
                    init.constant(m.bias, 0)
                    total_num += get_trainable_number(m.bias)

    def getVolume(self, left_image, right_image, KRKiUV_T, KT_T):
        idepth_base = 1.0 / 50.0
        idepth_step = (1.0 / 0.5 - 1.0 / 50.0) / 63.0
        costvolume = Variable(torch.FloatTensor(left_image.shape[0], 64, left_image.shape[2], left_image.shape[3]))
        image_height = 256
        image_width = 320
        batch_number = left_image.shape[0]
        normalize_base = torch.FloatTensor([image_width / 2.0, image_height / 2.0])
        normalize_base = normalize_base.unsqueeze(0).unsqueeze(-1)
        for depth_i in range(64):
            this_depth = 1.0 / (idepth_base + depth_i * idepth_step)
            transformed = KRKiUV_T * this_depth + KT_T
            demon = transformed[:, (2), :].unsqueeze(1)
            warp_uv = transformed[:, 0:2, :] / (demon + 1e-06)
            warp_uv = (warp_uv - normalize_base) / normalize_base
            warp_uv = warp_uv.view(batch_number, 2, image_width, image_height)
            warp_uv = Variable(warp_uv.permute(0, 3, 2, 1))
            warped = F.grid_sample(right_image, warp_uv)
            costvolume[:, (depth_i), :, :] = torch.sum(torch.abs(warped - left_image), dim=1)
        return costvolume

    def forward(self, left_image, right_image, KRKiUV_T, KT_T):
        plane_sweep_volume = self.getVolume(left_image, right_image, KRKiUV_T, KT_T)
        x = torch.cat((left_image, plane_sweep_volume), 1)
        conv1 = self.conv1(x)
        conv2 = self.conv2(conv1)
        conv3 = self.conv3(conv2)
        conv4 = self.conv4(conv3)
        conv5 = self.conv5(conv4)
        upconv5 = self.upconv5(conv5)
        iconv5 = self.iconv5(torch.cat((upconv5, conv4), 1))
        upconv4 = self.upconv4(iconv5)
        iconv4 = self.iconv4(torch.cat((upconv4, conv3), 1))
        disp4 = 2.0 * self.disp4(iconv4)
        udisp4 = F.upsample(disp4, scale_factor=2)
        upconv3 = self.upconv3(iconv4)
        iconv3 = self.iconv3(torch.cat((upconv3, conv2, udisp4), 1))
        disp3 = 2.0 * self.disp3(iconv3)
        udisp3 = F.upsample(disp3, scale_factor=2)
        upconv2 = self.upconv2(iconv3)
        iconv2 = self.iconv2(torch.cat((upconv2, conv1, udisp3), 1))
        disp2 = 2.0 * self.disp2(iconv2)
        udisp2 = F.upsample(disp2, scale_factor=2)
        upconv1 = self.upconv1(iconv2)
        iconv1 = self.iconv1(torch.cat((upconv1, udisp2), 1))
        disp1 = 2.0 * self.disp1(iconv1)
        return [disp1, disp2, disp3, disp4]

