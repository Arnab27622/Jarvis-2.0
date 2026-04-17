import torch
from torch import nn
from torch.nn import functional


class AudioClassifier(nn.Module):
    """
    Improved Audio Classifier using a Convolutional Neural Network.
    """

    def __init__(self) -> None:
        """
        Initializes the AudioClassifier module.
        """
        super(AudioClassifier, self).__init__()

        # Enhanced architecture with batch normalization and dropout
        self.conv1 = nn.Conv2d(1, 32, kernel_size=3, stride=1, padding=1)
        self.bn1 = nn.BatchNorm2d(32)
        self.pool1 = nn.MaxPool2d(2, 2)  # 256x256 -> 128x128

        self.conv2 = nn.Conv2d(32, 64, kernel_size=3, stride=1, padding=1)
        self.bn2 = nn.BatchNorm2d(64)
        self.pool2 = nn.MaxPool2d(2, 2)  # 128x128 -> 64x64

        self.conv3 = nn.Conv2d(64, 128, kernel_size=3, stride=1, padding=1)
        self.bn3 = nn.BatchNorm2d(128)
        self.pool3 = nn.MaxPool2d(2, 2)  # 64x64 -> 32x32

        self.conv4 = nn.Conv2d(128, 256, kernel_size=3, stride=1, padding=1)
        self.bn4 = nn.BatchNorm2d(256)
        self.pool4 = nn.MaxPool2d(2, 2)  # 32x32 -> 16x16

        # Additional conv layer for better feature extraction
        self.conv5 = nn.Conv2d(256, 512, kernel_size=3, stride=1, padding=1)
        self.bn5 = nn.BatchNorm2d(512)
        self.pool5 = nn.MaxPool2d(2, 2)  # 16x16 -> 8x8

        # Calculate the size after convolutions
        self.fc1 = nn.Linear(512 * 8 * 8, 512)
        self.fc2 = nn.Linear(512, 128)
        self.fc3 = nn.Linear(128, 2)

        self.dropout1 = nn.Dropout(0.3)
        self.dropout2 = nn.Dropout(0.5)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass of the network.

        Args:
            x (torch.Tensor): Input tensor of shape (batch_size, 1, height, width)

        Returns:
            torch.Tensor: Output tensor of shape (batch_size, num_classes)
        """
        # Conv block 1
        x = self.conv1(x)
        x = self.bn1(x)
        x = functional.relu(x)
        x = self.pool1(x)

        # Conv block 2
        x = self.conv2(x)
        x = self.bn2(x)
        x = functional.relu(x)
        x = self.pool2(x)

        # Conv block 3
        x = self.conv3(x)
        x = self.bn3(x)
        x = functional.relu(x)
        x = self.pool3(x)

        # Conv block 4
        x = self.conv4(x)
        x = self.bn4(x)
        x = functional.relu(x)
        x = self.pool4(x)

        # Conv block 5
        x = self.conv5(x)
        x = self.bn5(x)
        x = functional.relu(x)
        x = self.pool5(x)

        # Fully connected layers
        x = x.view(x.size(0), -1)
        x = self.dropout1(x)
        x = functional.relu(self.fc1(x))
        x = self.dropout2(x)
        x = functional.relu(self.fc2(x))
        x = self.fc3(x)

        return x  # Return logits, not softmax
