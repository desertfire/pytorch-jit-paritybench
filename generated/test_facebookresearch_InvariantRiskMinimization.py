import sys
_module = sys.modules[__name__]
del sys
main = _module
main = _module
models = _module
plot = _module
sem = _module
penalties = _module

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


import numpy as np


import torch


from torchvision import datasets


from torch import nn


from torch import optim


from torch import autograd


import numpy


import math


from sklearn.linear_model import LinearRegression


from itertools import chain


from itertools import combinations


from scipy.stats import f as fdist


from scipy.stats import ttest_ind


from torch.autograd import grad


import scipy.optimize

