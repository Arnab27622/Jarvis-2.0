"""
This module provides a Convolutional Neural Network architecture designed for 
audio classification tasks using spectrogram inputs.
"""

import torch
from torch import nn
from torch.nn import functional


class AudioClassifier(nn.Module):
    """
    A deep CNN architecture for audio classification featuring batch 
    normalization, dropout, and multiple convolutional layers.
    """

    def __init__(self) -> None:
        """
        Initializes the network layers and architecture components.
        """
        super(AudioClassifier, self).__init__()

        self.conv1 = nn.Conv2d(1, 32, kernel_size=3, stride=1, padding=1)
        self.bn1 = nn.BatchNorm2d(32)
        self.pool1 = nn.MaxPool2d(2, 2)

        self.conv2 = nn.Conv2d(32, 64, kernel_size=3, stride=1, padding=1)
        self.bn2 = nn.BatchNorm2d(64)
        self.pool2 = nn.MaxPool2d(2, 2)

        self.conv3 = nn.Conv2d(64, 128, kernel_size=3, stride=1, padding=1)
        self.bn3 = nn.BatchNorm2d(128)
        self.pool3 = nn.MaxPool2d(2, 2)

        self.conv4 = nn.Conv2d(128, 256, kernel_size=3, stride=1, padding=1)
        self.bn4 = nn.BatchNorm2d(256)
        self.pool4 = nn.MaxPool2d(2, 2)

        self.conv5 = nn.Conv2d(256, 512, kernel_size=3, stride=1, padding=1)
        self.bn5 = nn.BatchNorm2d(512)
        self.pool5 = nn.MaxPool2d(2, 2)

        self.fc1 = nn.Linear(512 * 8 * 8, 512)
        self.fc2 = nn.Linear(512, 128)
        self.fc3 = nn.Linear(128, 2)

        self.dropout1 = nn.Dropout(0.3)
        self.dropout2 = nn.Dropout(0.5)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Performs a forward pass through the network.

        Args:
            x: Input tensor of shape (batch_size, 1, height, width).

        Returns:
            Logits tensor of shape (batch_size, 2).
        """
        x = self.conv1(x)
        x = self.bn1(x)
        x = functional.relu(x)
        x = self.pool1(x)

        x = self.conv2(x)
        x = self.bn2(x)
        x = functional.relu(x)
        x = self.pool2(x)

        x = self.conv3(x)
        x = self.bn3(x)
        x = functional.relu(x)
        x = self.pool3(x)

        x = self.conv4(x)
        x = self.bn4(x)
        x = functional.relu(x)
        x = self.pool4(x)

        x = self.conv5(x)
        x = self.bn5(x)
        x = functional.relu(x)
        x = self.pool5(x)

        x = x.view(x.size(0), -1)
        x = self.dropout1(x)
        x = functional.relu(self.fc1(x))
        x = self.dropout2(x)
        x = functional.relu(self.fc2(x))
        x = self.fc3(x)

        return x
