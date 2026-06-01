"""
Module for loading an audio classification model and performing inference on audio files.
"""

import os
import torch
import torchaudio
import torchaudio.transforms as T
from torch import nn
from torchvision.transforms import Resize
from assistant.automation.clap_detection.cnn_sound_model import AudioClassifier
import warnings


class AudioModelHandler:
    """
    Handles loading the audio classification model and processing audio for inference.
    """

    def __init__(self, model_path: str):
        """
        Initializes the handler and loads the model into evaluation mode.
        """
        self.model = self.load_model(model_path)
        self.model.eval()

    @staticmethod
    def load_model(model_path: str) -> nn.Module:
        """
        Loads the model state dictionary from a file.
        """
        model = AudioClassifier()
        try:
            model.load_state_dict(
                torch.load(model_path, map_location=torch.device("cpu"))
            )
            print("Model loaded successfully")
        except Exception as e:
            print(f"Error loading model: {e}")
            print("Loading model with strict=False")
            model.load_state_dict(
                torch.load(model_path, map_location=torch.device("cpu")), strict=False
            )
        return model

    @staticmethod
    def transform_audio(
        audio_path_index: str,
        n_mels: int = 64,
        n_fft: int = 400,
        hop_length: int = 200,
    ) -> torch.Tensor:
        """
        Loads, resamples, and converts audio into a normalized mel spectrogram tensor.
        """
        try:
            try:
                waveform, sample_rate = torchaudio.load_with_torchcodec(
                    audio_path_index
                )
            except AttributeError:
                try:
                    with warnings.catch_warnings():
                        warnings.filterwarnings(
                            "ignore",
                            message="In 2.9, this function's implementation will be changed to use torchaudio.load_with_torchcodec.*",
                            category=UserWarning,
                        )
                        waveform, sample_rate = torchaudio.load(audio_path_index)
                except Exception:
                    waveform, sample_rate = torchaudio.load(
                        audio_path_index, backend="soundfile"
                    )
            except Exception:
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

            if waveform.shape[0] > 1:
                waveform = torch.mean(waveform, dim=0, keepdim=True)

            if sample_rate != 22050:
                resampler = T.Resample(sample_rate, 22050)
                waveform = resampler(waveform)
                sample_rate = 22050

            mel_spectrogram = T.MelSpectrogram(
                sample_rate=sample_rate,
                n_fft=n_fft,
                win_length=n_fft,
                hop_length=hop_length,
                n_mels=n_mels,
            )(waveform)

            mel_spectrogram = torchaudio.transforms.AmplitudeToDB()(mel_spectrogram)

            mel_spectrogram = Resize((256, 256))(mel_spectrogram)

            if mel_spectrogram.std() > 0:
                normalized_spec = (
                    mel_spectrogram - mel_spectrogram.mean()
                ) / mel_spectrogram.std()
            else:
                normalized_spec = mel_spectrogram - mel_spectrogram.mean()

            return normalized_spec.unsqueeze(0)

        except Exception as e:
            print(f"Error transforming audio: {e}")
            return torch.zeros((1, 1, 256, 256))

    def predict(
        self, audio_path_index: str, confidence_threshold: float = 0.8
    ) -> tuple:
        """
        Runs inference on an audio file and returns the class, confidence, and probabilities.
        """
        try:
            spec = self.transform_audio(audio_path_index)
            with torch.no_grad():
                output = self.model(spec)
                probabilities = torch.softmax(output, dim=1)
                confidence, predicted = torch.max(probabilities, 1)

                confidence_value = confidence.item()
                predicted_class = predicted.item()

                if predicted_class == 1 and confidence_value < confidence_threshold:
                    predicted_class = 0

                return predicted_class, confidence_value, probabilities[0].tolist()

        except Exception as e:
            print(f"Prediction error: {e}")
            return 0, 0.0, [0.5, 0.5]


def main(audio_path_index: str) -> None:
    """
    Executes the prediction workflow for a given audio file path.
    """
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    model_path = os.path.join(project_root, "data", "Clap_Detect_Model.pth")


    if not os.path.exists(model_path):
        print(f"Model file not found at: {model_path}")
        print("Please train the model first using model_trainer.py")
        return

    audio_handler = AudioModelHandler(model_path)

    prediction, confidence, probs = audio_handler.predict(
        audio_path_index, confidence_threshold=0.8
    )

    print("Noise = 0, Clap = 1")
    print(f"Probabilities: [Noise: {probs[0]:.3f}, Clap: {probs[1]:.3f}]")
    print(f"Confidence: {confidence:.3f}")
    print(f"The predicted class for {audio_path_index} is {prediction}")

    if prediction == 1 and confidence >= 0.8:
        print("✅ Confident clap detected!")
    elif prediction == 1 and confidence < 0.8:
        print("❓ Weak clap signal (below confidence threshold)")
    else:
        print("🔇 Noise detected")


if __name__ == "__main__":
    audio_path_index = input("Enter the path to an audio file: ").strip().strip('"')
    if os.path.exists(audio_path_index):
        main(audio_path_index)
    else:
        print(f"File not found: {audio_path_index}")
