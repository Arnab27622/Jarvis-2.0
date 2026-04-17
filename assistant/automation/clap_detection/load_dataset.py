import os
import torch
import torchaudio
from torch.utils.data import Dataset
from torchvision.transforms import Resize
import torchaudio.transforms as T
import warnings

warnings.filterwarnings("ignore", category=UserWarning)


def get_wav_files(directory: str) -> list:
    """
    Get a list of WAV file paths in the given directory.

    Args:
        directory (str): Path to the directory containing WAV files.

    Returns:
        list: List of WAV file paths.
    """
    wav_files = []
    for filename in os.listdir(directory):
        if filename.endswith(".wav"):
            wav_files.append(os.path.join(directory, filename))
    return wav_files


class AudioDataset(Dataset):
    """
    Dataset for audio classification.
    """

    def __init__(self, noise_dir: str, clap_dir: str) -> None:
        """
        Initializes the AudioDataset.

        Args:
            noise_dir (str): Path to the directory containing noise audio files.
            clap_dir (str): Path to the directory containing clap audio files.
        """
        noise_files = get_wav_files(noise_dir)
        clap_files = get_wav_files(clap_dir)

        self.noise_dir = noise_dir
        self.clap_dir = clap_dir
        self.file_list = noise_files + clap_files
        self.labels = [0] * len(noise_files) + [1] * len(clap_files)

        print(f"Loaded {len(noise_files)} noise files and {len(clap_files)} clap files")

    def __len__(self) -> int:
        """
        Returns the total number of samples in the dataset.
        """
        return len(self.file_list)

    def __getitem__(
        self, idx: int, n_mels: int = 64, n_fft: int = 400, hop_length: int = 200
    ) -> tuple:
        """
        Gets the item at the specified index.

        Args:
            idx (int): Index of the sample to retrieve.
            n_mels (int, optional): Number of mel frequency channels. Defaults to 64.
            n_fft (int, optional): Size of FFT. Defaults to 400.
            hop_length (int, optional): Hop length of the STFT. Defaults to 200.

        Returns:
            tuple: A tuple containing the spectrogram and the label.
        """
        try:
            waveform, sample_rate = torchaudio.load(self.file_list[idx])

            # Ensure we have mono audio
            if waveform.shape[0] > 1:
                waveform = torch.mean(waveform, dim=0, keepdim=True)

            # Resample to consistent rate if needed
            if sample_rate != 22050:
                resampler = T.Resample(sample_rate, 22050)
                waveform = resampler(waveform)
                sample_rate = 22050

            # Generate mel spectrogram
            mel_spectrogram = T.MelSpectrogram(
                sample_rate=sample_rate,
                n_fft=n_fft,
                win_length=n_fft,
                hop_length=hop_length,
                n_mels=n_mels,
            )(waveform)

            # Convert to log scale (dB)
            mel_spectrogram = torchaudio.transforms.AmplitudeToDB()(mel_spectrogram)

            # Resize to consistent dimensions
            mel_spectrogram = Resize((256, 256))(mel_spectrogram)

            # Normalize
            if mel_spectrogram.std() > 0:
                mel_spectrogram = (
                    mel_spectrogram - mel_spectrogram.mean()
                ) / mel_spectrogram.std()
            else:
                mel_spectrogram = mel_spectrogram - mel_spectrogram.mean()

            label = self.labels[idx]
            return mel_spectrogram, torch.tensor(label, dtype=torch.long)

        except Exception as e:
            print(f"Error loading {self.file_list[idx]}: {e}")
            # Return a properly shaped dummy tensor
            dummy_spec = torch.zeros((1, 256, 256))
            label = self.labels[idx]
            return dummy_spec, torch.tensor(label, dtype=torch.long)
