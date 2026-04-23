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

class SpeakerEmbedding:
    def __init__(self):
        self.classifier = None
        self.model_source = None

    def _resolve_model_source(self):
        fine_tuned_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "fine_tuned_model"))
        fine_tuned_hparams = os.path.join(fine_tuned_dir, "hyperparams.yaml")
        if os.path.isdir(fine_tuned_dir) and os.path.exists(fine_tuned_hparams):
            return fine_tuned_dir, fine_tuned_dir

        pretrained_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "pretrained_models", "spkrec-ecapa-voxceleb"))
        return "speechbrain/spkrec-ecapa-voxceleb", pretrained_dir

    def _ensure_classifier(self):
        if self.classifier is not None:
            return
        source, savedir = self._resolve_model_source()
        try:
            self.classifier = EncoderClassifier.from_hparams(source=source, savedir=savedir)
            self.classifier.eval()
            self.model_source = source
        except Exception as e:
            raise RuntimeError(f"Speaker model initialization failed from source '{source}': {str(e)}") from e

    def get_embedding(self, signal: torch.Tensor):
        """Extracts speaker embedding from audio signal."""
        self._ensure_classifier()
        with torch.no_grad():
            embeddings = self.classifier.encode_batch(signal)
            # Minimize to 1D vector
            return embeddings.squeeze().cpu().numpy()

    def compute_similarity(self, emb1, emb2):
        """Computes Cosine Similarity between two embeddings."""
        self._ensure_classifier()
        # Ensure numpy arrays
        score = torch.nn.functional.cosine_similarity(
            torch.tensor(emb1), torch.tensor(emb2), dim=0
        )
        return score.item()

speaker_model = SpeakerEmbedding()
