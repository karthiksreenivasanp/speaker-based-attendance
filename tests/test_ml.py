import sys
import os
sys.path.append(os.getcwd())

import torch
import shutil
import numpy as np
import scipy.io.wavfile as wav
from app.ml_engine.processing import AudioProcessor
from app.ml_engine.embedding import SpeakerEmbedding

# Setup
TEST_FILE = "test_audio.wav"
processor = AudioProcessor()
model = SpeakerEmbedding()

def generate_test_wav(filename):
    sample_rate = 16000
    t = np.linspace(0, 3, sample_rate * 3, endpoint=False)
    # Sine wave
    audio = np.sin(2 * np.pi * 440 * t)
    # Normalize
    audio = np.int16(audio / np.max(np.abs(audio)) * 32767)
    wav.write(filename, sample_rate, audio)

def test_ml_pipeline():
    print("Generating test file...")
    generate_test_wav(TEST_FILE)
    
    print("Testing AudioProcessor...")
    signal = processor.load_audio(TEST_FILE)
    print(f"Loaded signal shape: {signal.shape}")
    assert signal.shape[1] == 16000 * 3, "Length mismatch"
    assert not processor.is_silent(signal), "Should not be silent"
    
    signal_norm = processor.normalize_volume(signal)
    print("Normalization done.")

    print("Testing SpeakerEmbedding...")
    emb = model.get_embedding(signal_norm)
    print(f"Embedding shape: {emb.shape}")
    assert emb.shape[0] == 192, "ECAPA-TDNN should output 192-dim vector" # Check dim, might clarify if it's 192 or 512 depending on exact model version, usually 192 for ECAPA

    # Self-similarity
    score = model.compute_similarity(emb, emb)
    print(f"Self-similarity score: {score}")
    assert score > 0.99, "Self-similarity should be ~1.0"
    
    print("ML Pipeline Tests Passed!")
    
    # Cleanup
    if os.path.exists(TEST_FILE):
        os.remove(TEST_FILE)

if __name__ == "__main__":
    test_ml_pipeline()
