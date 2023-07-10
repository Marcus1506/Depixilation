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
import pickle

from architectures import SimpleCNN
from submission.submission_serialization import serialize, deserialize
# TODO: Add number of workers for dataloaders
def training_loop(
        network: torch.nn.Module, data: torch.utils.data.Dataset, num_epochs: int,
        optimizer: torch.optim.Optimizer, loss_function: torch.nn.Module, splits: tuple[float, float],
        minibatch_size: int=16, collate_func: callable=None, show_progress: bool = False, try_cuda: bool = False,
        early_stopping: bool = True, patience: int = 3, seed: int=None, model_path: str=None,
        losses_path: str=None) -> None:

    # set device
    device = torch.device("cuda" if torch.cuda.is_available() and try_cuda else "cpu")
    network.to(device)

    if seed:
        if not isinstance(seed, int):
            raise TypeError("Seed must be integer.")
        torch.manual_seed(seed)

    # Handle data
    if int(sum(splits)) != 1:
        raise ValueError("Splits must sum to 1.")
    train_data, eval_data = random_split(data, splits)

    # Maybe set seed here and use shuffling if needed.
    # Also memory could be pinned on CPU
    # to make training less prone to performance problems coming
    # from potential disk I/O operations.
    train_dataloader = torch.utils.data.DataLoader(train_data, collate_fn=collate_func, batch_size=minibatch_size, shuffle=True)
    eval_dataloader = torch.utils.data.DataLoader(eval_data, collate_fn=collate_func, batch_size=minibatch_size, shuffle=True)

    # Hand model parameters to optimizer
    optimizer = optimizer(network.parameters())

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
            loss = loss_function(pred, target_batch)
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
            loss = loss_function(pred, target_batch)

            eval_minibatch_losses.append(loss.detach().cpu())
        eval_losses.append(torch.mean(torch.stack(eval_minibatch_losses)))

        if early_stopping:
            # mabye restrict the search to the last few entries
            min_index = eval_losses.index(min(eval_losses))
            if len(eval_losses) - 1 - min_index == patience:
                # for the sake of completeness, maybe also send network back to cpu here
                network.to('cpu')
                if model_path and isinstance(model_path, str):
                    torch.save(network, model_path)

                if losses_path and isinstance(losses_path, str):
                    plot_losses(training_losses, eval_losses, losses_path)
                return

    # change device back to cpu
    network.to('cpu')
    if model_path and isinstance(model_path, str):
        torch.save(network, model_path)

    if losses_path and isinstance(losses_path, str):
        plot_losses(training_losses, eval_losses, losses_path)
    return

def test_loop_serialized(model_path: str, data_path: str) -> None:
    """
    This function is used to test the specified model (model_path) on the provided
    pickle file, which serves as a test set. The predictions should be gathered in a
    list of 1D Numpy arrays with dtype uint8 (so rescaling necessary!). This list
    should then be serialized to file using the provided submission_serialization.py.
    """
    
    model = torch.load(model_path)
    model.eval()
    predictions = []

    with open(data_path, 'rb') as f:
        dictionary = pickle.load(f)
        with torch.no_grad():
            for (pixelated_image, known_array) in zip(dictionary['pixelated_images'], dictionary['known_arrays']):
                input = np.concatenate((pixelated_image, known_array), axis=0)
                input = torch.from_numpy(input).unsqueeze(0).float()
                pred = model(input).numpy()*255
                pred = pred.astype(np.uint8)
                visualize_flat_u8int(pred)
                break

        

def plot_sample(data_sample: tuple[np.ndarray, np.ndarray, np.ndarray, str]) -> None:
    """
    Used for plotting samples obatained directly from the random pixelation dataset's
    __getitem__ method. The images are expected to be scaled to [0, 1].
    """
    pixelated_image, known_array, target_array, path = data_sample
    fig, axs = plt.subplots(1, 3, figsize=(12, 6))
    axs[0].imshow(pixelated_image[0], cmap='gray', vmin=0, vmax=1)
    axs[1].imshow(known_array[0], cmap='gray', vmin=0, vmax=1)
    axs[2].imshow(target_array[0], cmap='gray', vmin=0, vmax=1)
    plt.suptitle(path)
    plt.show()

def plot_losses(training_losses: list[float], eval_losses: list[float], path: str) -> None:
    """
    Takes in training losses and evaluation losses and saves plots to path-directory.
    """
    plt.plot(training_losses, label='Train loss')
    plt.plot(eval_losses, label='Evaluation loss')
    plt.ylabel('MSE Loss')
    plt.xlabel('Epoch')
    plt.legend()
    plt.savefig(path)

def visualize_flat_u8int(image: np.ndarray) -> None:
    """
    Takes in a 1D Numpy array of type uint8 and visualizes it as a grayscale image.
    """
    print(image.shape)
    dim = image.shape[-1]
    sqrt_dim = int(np.sqrt(dim))
    try:
        img = image.copy().reshape((int(sqrt_dim), int(sqrt_dim)))
    except:
        raise ValueError("Image must be square.")
    plt.imshow(img, cmap='gray', vmin=0, vmax=255)
    plt.show()

if __name__ == '__main__':
    test_loop_serialized("models/SimpleCNN_Sandbox.pt", "submission/test_set.pkl")