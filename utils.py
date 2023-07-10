"""
Author: Marcus Pertlwieser, 2023

Provides general utility for the project.
"""

import numpy as np
from tqdm import tqdm
import torch
from torch.utils.data.dataloader import DataLoader
from torch.utils.data import random_split
import matplotlib.pyplot as plt

def training_loop(
        network: torch.nn.Module, data: torch.utils.data.Dataset, num_epochs: int,
        optimizer: torch.optim.Optimizer, loss_function: torch.nn.Module, splits: tuple[float, float],
        minibatch_size: int=16, show_progress: bool = False, try_cuda: bool = False,
        early_stopping: bool = True, patience: int = 3, seed: int=None) -> tuple[list[float], list[float]]:

    # set device
    device = torch.device("cuda" if torch.cuda.is_available() and try_cuda else "cpu")
    network.to(device)

    if seed:
        if seed is not int:
            raise TypeError("Seed must be int.")
        torch.manual_seed(seed)

    # handle data
    if int(sum(splits)) != 1:
        raise ValueError("Splits must sum to 1.")
    train_data, eval_data = random_split(data, [*tuple])

    # Maybe set seed here and use shuffling if needed.
    # Also memory could be pinned on CPU
    # to make training less prone to performance problems coming
    # from potential disk I/O operations.
    train_dataloader = torch.utils.data.DataLoader(train_data, batch_size=minibatch_size, shuffle=True)
    eval_dataloader = torch.utils.data.DataLoader(eval_data, batch_size=minibatch_size, shuffle=True)

    # hand model parameters to optimizer
    optimizer = optimizer(network.parameters())
    # instantiate loss
    loss_function = torch.nn.MSELoss()

    training_losses = []
    eval_losses = []
    for epoch in tqdm(range(num_epochs), disable=not show_progress):
        # set model to training mode
        network.train()
        train_minibatch_losses = []
        for train_batch, target_batch in train_dataloader:
            train_batch = train_batch.to(device)
            target_batch = target_batch.to(device)

            # clear gradients
            network.zero_grad()

            # compute loss and propagate back
            pred = network(train_batch)
            loss = loss_function(torch.squeeze(pred, dim=0), target_batch)
            loss.backward()

            # update model parameters
            optimizer.step()

            # append loss to list, detach gradients from tensor and move to cpu
            train_minibatch_losses.append(loss.detach().cpu())
        training_losses.append(torch.mean(torch.stack(train_minibatch_losses)))
        
        eval_minibatch_losses = []
        # set model to eval mode
        network.eval()
        for eval_batch, target_batch in eval_dataloader:
            eval_batch = eval_batch.to(device)
            target_batch = target_batch.to(device)

            pred = network(eval_batch)
            loss = loss_function(torch.squeeze(pred, dim=0), target_batch)

            eval_minibatch_losses.append(loss.detach().cpu())
        eval_losses.append(torch.mean(torch.stack(eval_minibatch_losses)))

        if early_stopping:
            # mabye restrict the search to the last few entries
            min_index = eval_losses.index(min(eval_losses))
            if len(eval_losses) - 1 - min_index == patience:
                # for the sake of completeness, maybe also send network back to cpu here 
                return training_losses, eval_losses

    # change device back to cpu
    network.to('cpu')

    return training_losses, eval_losses

def plot_sample(data_sample: tuple[np.ndarray, np.ndarray, np.ndarray, str]) -> None:
    pixelated_image, known_array, target_array, path = data_sample
    fig, axs = plt.subplots(1, 3, figsize=(12, 6))
    axs[0].imshow(pixelated_image[0], cmap='gray', vmin=0, vmax=255)
    axs[1].imshow(known_array[0], cmap='gray', vmin=0, vmax=1)
    axs[2].imshow(target_array[0], cmap='gray', vmin=0, vmax=255)
    plt.suptitle(path)
    plt.show()
    