"""
Module for training a CNN-based audio classifier to detect clap sounds.
"""

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, random_split
from assistant.automation.clap_detection.load_dataset import AudioDataset
from assistant.automation.clap_detection.cnn_sound_model import AudioClassifier
from typing import Tuple
import os


class AudioClassifierTrainer:
    """
    Handles the training pipeline, including data loading, model optimization,
    and checkpointing for the AudioClassifier.
    """

    def __init__(self, noise_dir: str, clap_dir: str, device: torch.device) -> None:
        """
        Initializes the trainer with dataset paths, model, and optimization parameters.
        """
        self.device = device
        self.dataset = AudioDataset(noise_dir, clap_dir)
        self.train_dataloader, self.val_dataloader = self.prepare_dataloaders()
        self.model = AudioClassifier().to(self.device)
        self.criterion = nn.CrossEntropyLoss()
        self.optimizer = torch.optim.AdamW(
            self.model.parameters(), lr=1e-4, weight_decay=0.01
        )
        self.scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            self.optimizer, mode="min", patience=3, factor=0.5
        )

    def prepare_dataloaders(self) -> Tuple[DataLoader, DataLoader]:
        """
        Splits the dataset into training and validation sets and creates DataLoaders.
        """
        train_size = int(0.8 * len(self.dataset))
        val_size = len(self.dataset) - train_size
        train_dataset, val_dataset = random_split(self.dataset, [train_size, val_size])
        train_loader = DataLoader(
            train_dataset, batch_size=16, shuffle=True, num_workers=2
        )
        val_loader = DataLoader(
            val_dataset, batch_size=16, shuffle=False, num_workers=2
        )
        return train_loader, val_loader

    def train(self, num_epochs: int) -> None:
        """
        Executes the training loop over a specified number of epochs.
        """
        best_val_accuracy = 0

        for epoch in range(num_epochs):
            train_loss, train_accuracy = self.run_epoch(
                self.train_dataloader, training=True
            )
            val_loss, val_accuracy = self.run_epoch(self.val_dataloader, training=False)

            self.scheduler.step(val_loss)

            print(
                f"Epoch {epoch + 1}/{num_epochs}, "
                f"Train Loss: {train_loss:.4f}, Train Accuracy: {train_accuracy:.4f}, "
                f"Val Loss: {val_loss:.4f}, Val Accuracy: {val_accuracy:.4f}, "
                f"LR: {self.optimizer.param_groups[0]['lr']:.2e}"
            )

            if val_accuracy > best_val_accuracy:
                best_val_accuracy = val_accuracy
                model_path = os.path.join("data", "Clap_Detect_Model.pth")
                self.save_model(model_path)
                print(f"New best model saved with val accuracy: {val_accuracy:.4f}")

    def run_epoch(self, dataloader: DataLoader, training: bool) -> Tuple[float, float]:
        """
        Performs a single pass over the dataset for training or evaluation.
        """
        if training:
            self.model.train()
        else:
            self.model.eval()

        epoch_loss = 0
        correct_predictions = 0
        total_predictions = 0

        with torch.set_grad_enabled(training):
            for batch_idx, (inputs, labels) in enumerate(dataloader):
                try:
                    inputs, labels = inputs.to(self.device), labels.to(self.device)

                    outputs = self.model(inputs)
                    loss = self.criterion(outputs, labels)

                    if training:
                        self.optimizer.zero_grad()
                        loss.backward()
                        self.optimizer.step()

                    epoch_loss += loss.item()
                    _, predicted = torch.max(outputs, 1)
                    total_predictions += labels.size(0)
                    correct_predictions += (predicted == labels).sum().item()

                    if batch_idx % 10 == 0 and training:
                        print(
                            f"Batch {batch_idx}/{len(dataloader)}, Loss: {loss.item():.4f}"
                        )

                except Exception as e:
                    print(f"Error in batch {batch_idx}: {e}")
                    continue

        avg_loss = epoch_loss / len(dataloader) if len(dataloader) > 0 else 0
        accuracy = (
            correct_predictions / total_predictions if total_predictions > 0 else 0
        )
        return avg_loss, accuracy

    def save_model(self, path: str) -> None:
        """
        Persists the model state dictionary to the specified file path.
        """
        os.makedirs(os.path.dirname(path), exist_ok=True)
        torch.save(self.model.state_dict(), path)


if __name__ == "__main__":
    torch.manual_seed(42)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")

    base_dir = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    )
    noise_dir = os.path.join(base_dir, "data", "noise2")
    clap_dir = os.path.join(base_dir, "data", "claps")

    if not os.path.exists(noise_dir):
        print(f"Error: Noise directory not found at {noise_dir}")
    if not os.path.exists(clap_dir):
        print(f"Error: Clap directory not found at {clap_dir}")

    trainer = AudioClassifierTrainer(noise_dir, clap_dir, device)
    trainer.train(num_epochs=20)
