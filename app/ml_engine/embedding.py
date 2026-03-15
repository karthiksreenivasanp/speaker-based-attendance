import torch
import torchaudio

# Monkey-patch for torchaudio > 2.1 compatibility
if not hasattr(torchaudio, "list_audio_backends"):
    torchaudio.list_audio_backends = lambda: ["soundfile"]

import os
import shutil

# Monkey-patch os.symlink for Windows non-admin privileges
_original_symlink = os.symlink
def _safe_symlink(src, dst, target_is_directory=False, **kwargs):
    try:
        _original_symlink(src, dst, target_is_directory, **kwargs)
    except OSError as e:
        if getattr(e, 'winerror', None) == 1314: # A required privilege is not held
            if os.path.isdir(src):
                shutil.copytree(src, dst)
            else:
                shutil.copy2(src, dst)
        else:
            raise

os.symlink = _safe_symlink

from speechbrain.inference.speaker import EncoderClassifier
from app.core.config import settings
import os

class SpeakerEmbedding:
    def __init__(self):
        # Using ECAPA-TDNN from SpeechBrain
        model_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "fine_tuned_model"))
        self.classifier = EncoderClassifier.from_hparams(
            source=model_dir,
            savedir=model_dir
        )
        self.classifier.eval()

    def get_embedding(self, signal: torch.Tensor):
        """Extracts speaker embedding from audio signal."""
        with torch.no_grad():
            embeddings = self.classifier.encode_batch(signal)
            # Minimize to 1D vector
            return embeddings.squeeze().cpu().numpy()

    def compute_similarity(self, emb1, emb2):
        """Computes Cosine Similarity between two embeddings."""
        # Ensure numpy arrays
        score = torch.nn.functional.cosine_similarity(
            torch.tensor(emb1), torch.tensor(emb2), dim=0
        )
        return score.item()

speaker_model = SpeakerEmbedding()
