import torch
import torchaudio
import torchaudio.transforms as T
from torch import nn
from torchvision.transforms import Resize
from assistant.automation.clap_detection.cnn_sound_model import AudioClassifier
import warnings


class AudioModelHandler:
    """
    Handler class for loading and using the audio classification model.
    """

    def __init__(self, model_path: str):
        """
        Initializes the AudioModelHandler.

        Args:
            model_path (str): Path to the saved model file.
        """
        self.model = self.load_model(model_path)

    @staticmethod
    def load_model(model_path: str) -> nn.Module:
        """
        Loads the saved model from the specified path.

        Args:
            model_path (str): Path to the saved model file.

        Returns:
            nn.Module: Loaded model.
        """
        model = AudioClassifier()
        model.load_state_dict(torch.load(model_path, map_location=torch.device("cpu")))
        model.eval()
        return model

    @staticmethod
    def transform_audio(
        audio_path_index: str,
        n_mels: int = 64,
        n_fft: int = 400,
        hop_length: int = 200,
    ) -> torch.Tensor:
        """
        Transforms the audio file into a normalized mel spectrogram tensor.

        Args:
            audio_path_index (str): Path to the audio file.
            n_mels (int, optional): Number of mel frequency channels. Defaults to 128.
            n_fft (int, optional): Size of FFT. Defaults to 400.
            hop_length (int, optional): Hop length of the STFT. Defaults to 200.

        Returns:
            torch.Tensor: Normalized mel spectrogram tensor.
        """
        try:
            waveform, sample_rate = torchaudio.load_with_torchcodec(audio_path_index)
        except AttributeError:
            # Fallback for older TorchAudio versions that don't have load_with_torchcodec
            try:
                # Suppress the specific deprecation warning
                with warnings.catch_warnings():
                    warnings.filterwarnings(
                        "ignore",
                        message="In 2.9, this function's implementation will be changed to use torchaudio.load_with_torchcodec.*",
                        category=UserWarning,
                    )
                    waveform, sample_rate = torchaudio.load(audio_path_index)
            except Exception:
                # Final fallback with backend specification
                waveform, sample_rate = torchaudio.load(
                    audio_path_index, backend="soundfile"
                )
        except Exception as e:
            # If TorchCodec loading fails, use traditional method with warning suppression
            with warnings.catch_warnings():
                warnings.filterwarnings(
                    "ignore",
                    message="In 2.9, this function's implementation will be changed to use torchaudio.load_with_torchcodec.*",
                    category=UserWarning,
                )
                try:
                    waveform, sample_rate = torchaudio.load(audio_path_index)
                except Exception:
                    waveform, sample_rate = torchaudio.load(
                        audio_path_index, backend="soundfile"
                    )

        mel_spectrogram = T.MelSpectrogram(
            sample_rate=sample_rate,
            n_fft=n_fft,
            win_length=n_fft,
            hop_length=hop_length,
            n_mels=n_mels,
        )(waveform)
        mel_spectrogram = Resize((256, 256))(mel_spectrogram)
        normalized_spec = (
            mel_spectrogram - mel_spectrogram.mean()
        ) / mel_spectrogram.std()
        return normalized_spec.unsqueeze(0)

    def predict(self, audio_path_index: str) -> int:
        """
        Predicts the class of the audio file using the loaded model.

        Args:
            audio_path_index (str): Path to the audio file.

        Returns:
            int: Predicted class (0 for noise, 1 for clap).
        """
        spec = self.transform_audio(audio_path_index)
        output = self.model(spec)
        _, predicted = torch.max(output.data, 1)
        return predicted.item()


def main(audio_path_index) -> None:
    """
    Main function to run the audio classification prediction.
    """
    model_path = (
        r"C:\Users\arnab\OneDrive\Python\Projects\Jarvis 2.0\data\Clap_Detect_Model.pth"
    )
    audio_handler = AudioModelHandler(model_path)

    prediction = audio_handler.predict(audio_path_index)
    print("Noise = 0, Clap = 1")
    print(f"The predicted class for {audio_path_index} is {prediction}")


if __name__ == "__main__":
    audio_path_index = input("Enter the path to an audio file: ")
    main(audio_path_index)
