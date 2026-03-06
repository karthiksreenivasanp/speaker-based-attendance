import torch
import torchaudio
import numpy as np
from app.core.config import settings
import noisereduce as nr
import soundfile as sf
import scipy.signal as signal

class AudioProcessor:
    def __init__(self, sample_rate=16000):
        self.sample_rate = sample_rate
        self.resamplers = {} # Cache resamplers
    
    def load_audio(self, file_path: str, reduce_noise: bool = True):
        """Loads audio and resamples to target sample rate."""
        try:
            signal_np, fs = sf.read(file_path)
        except Exception as e:
            raise e
        
        # Determine if it's stereo or mono, ensuring shape (channels, frames)
        if len(signal_np.shape) == 1:
            # Mono case
            # signal_np is (time,)
             signal_np = signal_np[np.newaxis, :] # (1, time)
        else:
             # Stereo case (time, channels) -> (channels, time)
             signal_np = signal_np.T

        # --- STEP 1: BANDPASS FILTER ---
        # Keep only human voice frequencies (80Hz - 7000Hz)
        # Removes low rumble and high hiss
        try:
            signal_np = self._apply_bandpass(signal_np, fs)
        except Exception:
            pass # Fallback if filter fails

        # --- STEP 2: NOISE REDUCTION ---
        if reduce_noise:
            try:
                 signal_denoised = nr.reduce_noise(y=signal_np, sr=fs, prop_decrease=0.75, stationarity=True)
            except:
                 signal_denoised = signal_np # Fallback
        else:
            signal_denoised = signal_np

        # Convert to tensor
        # Fix for "negative strides" error: ensure array is contiguous
        signal = torch.from_numpy(signal_denoised.copy()).float()
        
        # Convert to mono if stereo
        if signal.shape[0] > 1:
            signal = torch.mean(signal, dim=0, keepdim=True)
            
        # Resample if needed
        if fs != self.sample_rate:
            if fs not in self.resamplers:
                self.resamplers[fs] = torchaudio.transforms.Resample(fs, self.sample_rate)
            signal = self.resamplers[fs](signal)
            
        return signal

    def _apply_bandpass(self, audio: np.ndarray, sr: int, lowcut=80, highcut=7000):
        """Apply Butterworth bandpass filter to keep voice frequencies."""
        import scipy.signal as signal
        nyq = 0.5 * sr
        low = lowcut / nyq
        high = highcut / nyq
        # Order 4 Butterworth filter
        b, a = signal.butter(4, [low, high], btype='band')
        return signal.filtfilt(b, a, audio)

    def normalize_volume(self, signal: torch.Tensor, target_db: float = -20.0):
        """RMS-based normalization for consistent volume."""
        # Calculate RMS
        rms = torch.sqrt(torch.mean(signal**2))
        if rms < 1e-6:
             return signal
        
        # Target RMS
        target_rms = 10 ** (target_db / 20)
        gain = target_rms / rms
        return signal * gain

    def is_silent(self, signal: torch.Tensor, threshold: float = 0.005) -> bool: # Lowered threshold due to cleaner audio
        """Simple energy-based silence detection."""
        return torch.mean(torch.abs(signal)) < threshold

    def check_liveness(self, signal: torch.Tensor) -> float:
        """
        Heuristic Liveness Score (0.0 to 1.0).
        Checks for natural frequency distribution. 
        Replayed audio often has 'gaps' or unnatural spectral flatness.
        """
        # Convert to numpy
        sig_np = signal.squeeze().numpy()
        
        # 1. Zero Crossing Rate (ZCR) - Simple texture check
        # High ZCR can indicate electronic noise or sibilance
        zcr = ((sig_np[:-1] * sig_np[1:]) < 0).sum() / len(sig_np)
        
        # 2. Dynamic Range Check
        # Recorded/Compressed audio often has lower dynamic range
        dynamic_range = np.max(np.abs(sig_np)) / (np.mean(np.abs(sig_np)) + 1e-9)
        
        # 3. Simple decision logic
        # Ideally we would use a trained model (ASVspoof), but for this project:
        # We penalize very low dynamic range (compression) or extreme ZCR.
        
        liveness_score = 1.0
        
        if dynamic_range < 8.0: # Increased from 3.0 to 8.0 (Live speech is very dynamic)
            liveness_score -= 0.4 # Heavily penalize compressed audio
            
        if zcr > 0.2: # Decreased from 0.5 (Live speech usually < 0.15)
            liveness_score -= 0.3 # Penalize noise/hiss
            
        # 3. Energy Fluctuation
        # Live speech has pauses. Continuous noise (fan/static) has low variance.
        energy_variance = np.var(sig_np**2)
        if energy_variance < 0.0001: 
             liveness_score -= 0.3           
            
        return max(0.0, liveness_score)

audio_processor = AudioProcessor(sample_rate=settings.SAMPLE_RATE)
