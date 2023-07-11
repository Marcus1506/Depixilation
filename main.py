"""
Author: Marcus Pertlwieser, 2023
Main file of project. Executing training loop and testing loop.
"""

import torch
from architectures import SimpleCNN, DepixCNN
import numpy as np
import matplotlib.pyplot as plt

import datasets
from utils import training_loop, check_overfitting
from data_utils import stack_with_padding

if __name__ == '__main__':
    data = datasets.RandomImagePixelationDataset('dataset/training', (4, 32), (4, 32), (4, 16))

    model = DepixCNN(2, 1, 14, (2, 6))

    training_loop(model, data, 1000, torch.optim.Adam, torch.nn.MSELoss(), (0.9, 0.1), 32, stack_with_padding,
                  True, True, True, 10, 'models/DepixCNN_vkernel_steep(2,6)_skip5.pt', 'losses/DepixCNN_vkernel_steep(2,6)_skip5.jpg', 6, True, 10)
    
    check_overfitting(datasets.RandomImagePixelationDataset('data_sandbox', (4, 32), (4, 32), (4, 16)),
                      "models/DepixCNN_vkernel_steep(2,6)_skip5.pt")
    
    
