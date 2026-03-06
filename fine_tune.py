#!/usr/bin/env python3
"""
fine_tune.py
============
Fine-tunes the ECAPA-TDNN model on a custom voice dataset using
Contrastive Learning (Triplet Loss).

Usage:
    python fine_tune.py

After training, the fine-tuned model is saved to fine_tuned_model/
"""

import os
import sys
import csv
import random
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
import soundfile as sf
from collections import defaultdict

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_DIR)

DATASET_DIR = os.path.join(PROJECT_DIR, "dataset_processed")
TRAIN_CSV = os.path.join(DATASET_DIR, "train.csv")
VAL_CSV = os.path.join(DATASET_DIR, "val.csv")
OUTPUT_DIR = os.path.join(PROJECT_DIR, "fine_tuned_model")
SAMPLE_RATE = 16000

# Hyperparameters
EPOCHS = 20
BATCH_SIZE = 8  # Use 8 for better gradient stability
LEARNING_RATE = 1e-4  # Higher LR since the first run learned too slowly
MARGIN = 0.4  # Push negative speakers further away
MIN_AUDIO_LEN = 16000  # 1 second minimum
MAX_AUDIO_LEN = 48000  # 3 seconds max


# ============================================================
# DATASET
# ============================================================

class SpeakerTripletDataset(Dataset):
    """Dataset that generates (anchor, positive, negative) triplets."""
    
    def __init__(self, csv_path):
        self.samples = defaultdict(list)
        
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                sid = int(row['speaker_id'])
                self.samples[sid].append(row['file_path'])
        
        self.all_speaker_ids = list(self.samples.keys())
        
        # Create all possible anchor-positive pairs
        self.pairs = []
        for sid in self.all_speaker_ids:
            files = self.samples[sid]
            for i in range(len(files)):
                for j in range(i + 1, len(files)):
                    self.pairs.append((sid, files[i], files[j]))
    
    def __len__(self):
        return len(self.pairs)
    
    def _load_audio(self, path):
        """Load audio and return raw waveform as tensor [1, time]."""
        data, sr = sf.read(path)
        if len(data.shape) > 1:
            data = np.mean(data, axis=1)
        
        # Pad if too short
        if len(data) < MIN_AUDIO_LEN:
            data = np.pad(data, (0, MIN_AUDIO_LEN - len(data)))
        
        # Crop if too long
        if len(data) > MAX_AUDIO_LEN:
            start = random.randint(0, len(data) - MAX_AUDIO_LEN)
            data = data[start:start + MAX_AUDIO_LEN]
        
        return torch.FloatTensor(data)
    
    def __getitem__(self, idx):
        sid, anchor_path, positive_path = self.pairs[idx]
        
        # Pick a random negative speaker
        neg_sid = random.choice([s for s in self.all_speaker_ids if s != sid])
        neg_path = random.choice(self.samples[neg_sid])
        
        anchor = self._load_audio(anchor_path)
        positive = self._load_audio(positive_path)
        negative = self._load_audio(neg_path)
        
        return anchor, positive, negative, sid


def collate_fn(batch):
    """Custom collate: pad all waveforms to the max length in the batch."""
    anchors, positives, negatives, sids = zip(*batch)
    
    max_len = max(
        max(a.shape[0] for a in anchors),
        max(p.shape[0] for p in positives),
        max(n.shape[0] for n in negatives),
    )
    
    def pad_batch(tensors):
        padded = torch.zeros(len(tensors), max_len)
        lens = torch.zeros(len(tensors))
        for i, t in enumerate(tensors):
            padded[i, :t.shape[0]] = t
            lens[i] = t.shape[0] / max_len  # Relative length
        return padded, lens
    
    a_padded, a_lens = pad_batch(anchors)
    p_padded, p_lens = pad_batch(positives)
    n_padded, n_lens = pad_batch(negatives)
    
    return a_padded, a_lens, p_padded, p_lens, n_padded, n_lens, torch.tensor(sids)


# ============================================================
# TRIPLET LOSS
# ============================================================

class TripletLoss(nn.Module):
    def __init__(self, margin=0.2):
        super().__init__()
        self.margin = margin
        self.cos = nn.CosineSimilarity(dim=1)
    
    def forward(self, anchor, positive, negative):
        pos_sim = self.cos(anchor, positive)
        neg_sim = self.cos(anchor, negative)
        loss = torch.clamp(self.margin - (pos_sim - neg_sim), min=0.0)
        return loss.mean(), pos_sim.mean().item(), neg_sim.mean().item()


# ============================================================
# FORWARD PASS USING FULL SPEECHBRAIN PIPELINE
# ============================================================

def get_embedding(model, wavs, wav_lens):
    """
    Pass audio through the FULL SpeechBrain pipeline:
    raw audio → compute_features (Fbank) → mean_var_norm → embedding_model → embedding
    """
    feats = model.mods.compute_features(wavs)
    feats = model.mods.mean_var_norm(feats, wav_lens)
    embeddings = model.mods.embedding_model(feats, wav_lens)
    return embeddings.squeeze(1)  # (batch, 192)


# ============================================================
# EVALUATION
# ============================================================

def evaluate(model, val_csv, device):
    """Evaluate: compute avg same-speaker & diff-speaker cosine similarity."""
    samples = defaultdict(list)
    with open(val_csv, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            samples[int(row['speaker_id'])].append(row['file_path'])
    
    embeddings = {}
    model.mods.embedding_model.eval()
    
    with torch.no_grad():
        for sid, files in samples.items():
            for fpath in files:
                data, sr = sf.read(fpath)
                if len(data.shape) > 1:
                    data = np.mean(data, axis=1)
                wavs = torch.FloatTensor(data).unsqueeze(0).to(device)
                wav_lens = torch.ones(1).to(device)
                emb = get_embedding(model, wavs, wav_lens)
                embeddings[(sid, fpath)] = emb.squeeze().cpu()
    
    cos = nn.CosineSimilarity(dim=0)
    same_scores = []
    diff_scores = []
    
    keys = list(embeddings.keys())
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            sid_i, _ = keys[i]
            sid_j, _ = keys[j]
            score = cos(embeddings[keys[i]], embeddings[keys[j]]).item()
            if sid_i == sid_j:
                same_scores.append(score)
            else:
                diff_scores.append(score)
    
    avg_same = np.mean(same_scores) if same_scores else 0
    avg_diff = np.mean(diff_scores) if diff_scores else 0
    return avg_same, avg_diff


# ============================================================
# MAIN TRAINING LOOP
# ============================================================

def main():
    print("=" * 60)
    print("  ECAPA-TDNN FINE-TUNING")
    print("=" * 60)
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"  Device: {device}")
    print(f"  Epochs: {EPOCHS}")
    print(f"  Batch:  {BATCH_SIZE}")
    print(f"  LR:     {LEARNING_RATE}")
    print(f"  Margin: {MARGIN}")
    
    # Load pre-trained ECAPA-TDNN
    print("\n📦 Loading pre-trained ECAPA-TDNN...")
    
    import torchaudio
    if not hasattr(torchaudio, "list_audio_backends"):
        torchaudio.list_audio_backends = lambda: ["soundfile"]
    
    from speechbrain.inference.speaker import EncoderClassifier
    
    model = EncoderClassifier.from_hparams(
        source="speechbrain/spkrec-ecapa-voxceleb",
        savedir="pretrained_models/spkrec-ecapa-voxceleb",
        revision="5c0be3875fda05e81f3c004ed8c7c06be308de1e"
    )
    model.to(device)
    
    # Freeze compute_features and mean_var_norm (these are fixed Fbank extractors)
    for param in model.mods.compute_features.parameters():
        param.requires_grad = False
    for param in model.mods.mean_var_norm.parameters():
        param.requires_grad = False
    
    # For the embedding_model: freeze early blocks, train later ones
    ecapa = model.mods.embedding_model
    trainable_params = []
    frozen_count = 0
    trainable_count = 0
    
    for name, param in ecapa.named_parameters():
        # Freeze blocks 0 and 1 (first two TDNN-Res blocks)
        if name.startswith("blocks.0.") or name.startswith("blocks.1."):
            param.requires_grad = False
            frozen_count += param.numel()
        else:
            param.requires_grad = True
            trainable_params.append(param)
            trainable_count += param.numel()
    
    print(f"  Frozen params:    {frozen_count:,}")
    print(f"  Trainable params: {trainable_count:,}")
    
    # Dataset
    print("\n📊 Loading dataset...")
    train_dataset = SpeakerTripletDataset(TRAIN_CSV)
    train_loader = DataLoader(
        train_dataset, batch_size=BATCH_SIZE, shuffle=True,
        num_workers=0, drop_last=True, collate_fn=collate_fn
    )
    print(f"  Training pairs: {len(train_dataset)}")
    print(f"  Batches/epoch:  {len(train_loader)}")
    
    # Optimizer & Loss
    optimizer = optim.Adam(trainable_params, lr=LEARNING_RATE, weight_decay=1e-5)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)
    criterion = TripletLoss(margin=MARGIN)
    
    # Baseline evaluation
    print("\n📏 Baseline evaluation (before fine-tuning)...")
    avg_same_pre, avg_diff_pre = evaluate(model, VAL_CSV, device)
    print(f"  Same-speaker similarity:  {avg_same_pre:.4f}")
    print(f"  Diff-speaker similarity:  {avg_diff_pre:.4f}")
    print(f"  Separation gap:           {avg_same_pre - avg_diff_pre:.4f}")
    
    # Training
    print(f"\n🚀 Starting training for {EPOCHS} epochs...")
    print("-" * 60)
    
    best_gap = avg_same_pre - avg_diff_pre
    
    for epoch in range(1, EPOCHS + 1):
        ecapa.train()
        total_loss = 0
        total_pos_sim = 0
        total_neg_sim = 0
        num_batches = 0
        
        for batch_idx, (a_wav, a_len, p_wav, p_len, n_wav, n_len, sids) in enumerate(train_loader):
            a_wav, a_len = a_wav.to(device), a_len.to(device)
            p_wav, p_len = p_wav.to(device), p_len.to(device)
            n_wav, n_len = n_wav.to(device), n_len.to(device)
            
            # Forward through full pipeline
            a_emb = get_embedding(model, a_wav, a_len)
            p_emb = get_embedding(model, p_wav, p_len)
            n_emb = get_embedding(model, n_wav, n_len)
            
            loss, pos_sim, neg_sim = criterion(a_emb, p_emb, n_emb)
            
            optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(trainable_params, max_norm=5.0)
            optimizer.step()
            
            total_loss += loss.item()
            total_pos_sim += pos_sim
            total_neg_sim += neg_sim
            num_batches += 1
        
        scheduler.step()
        
        avg_loss = total_loss / max(num_batches, 1)
        avg_pos = total_pos_sim / max(num_batches, 1)
        avg_neg = total_neg_sim / max(num_batches, 1)
        
        # Evaluate every 5 epochs
        if epoch % 5 == 0 or epoch == 1 or epoch == EPOCHS:
            avg_same, avg_diff = evaluate(model, VAL_CSV, device)
            gap = avg_same - avg_diff
            improved = "⬆️" if gap > best_gap else ""
            
            print(f"  Epoch {epoch:02d}/{EPOCHS} | Loss: {avg_loss:.4f} | "
                  f"P/N: {avg_pos:.3f}/{avg_neg:.3f} | "
                  f"Val Same: {avg_same:.3f} Diff: {avg_diff:.3f} Gap: {gap:.3f} {improved}")
            
            if gap > best_gap:
                best_gap = gap
                os.makedirs(OUTPUT_DIR, exist_ok=True)
                torch.save(ecapa.state_dict(), os.path.join(OUTPUT_DIR, "embedding_model.ckpt"))
                print(f"         💾 Best model saved (gap: {gap:.4f})")
        else:
            print(f"  Epoch {epoch:02d}/{EPOCHS} | Loss: {avg_loss:.4f} | "
                  f"pos: {avg_pos:.3f} neg: {avg_neg:.3f}")
    
    # Final save
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    torch.save(ecapa.state_dict(), os.path.join(OUTPUT_DIR, "embedding_model_final.ckpt"))
    
    # Copy necessary config files from pretrained model
    import shutil
    src_dir = os.path.join(PROJECT_DIR, "pretrained_models", "spkrec-ecapa-voxceleb")
    for fname in os.listdir(src_dir):
        src = os.path.join(src_dir, fname)
        dst = os.path.join(OUTPUT_DIR, fname)
        if os.path.isfile(src) and fname != "embedding_model.ckpt":
            shutil.copy2(src, dst)
    
    # Ensure fine-tuned embedding weights are the best ones
    best_ckpt = os.path.join(OUTPUT_DIR, "embedding_model.ckpt")
    if not os.path.exists(best_ckpt):
        torch.save(ecapa.state_dict(), best_ckpt)
    
    # Final evaluation
    print(f"\n{'='*60}")
    print("  📊 FINAL RESULTS")
    print(f"{'='*60}")
    avg_same_post, avg_diff_post = evaluate(model, VAL_CSV, device)
    
    print(f"\n  BEFORE Fine-Tuning:")
    print(f"    Same-speaker sim:  {avg_same_pre:.4f}")
    print(f"    Diff-speaker sim:  {avg_diff_pre:.4f}")
    print(f"    Gap:               {avg_same_pre - avg_diff_pre:.4f}")
    
    print(f"\n  AFTER Fine-Tuning:")
    print(f"    Same-speaker sim:  {avg_same_post:.4f}")
    print(f"    Diff-speaker sim:  {avg_diff_post:.4f}")
    print(f"    Gap:               {avg_same_post - avg_diff_post:.4f}")
    
    gap_before = avg_same_pre - avg_diff_pre
    gap_after = avg_same_post - avg_diff_post
    improvement = gap_after - gap_before
    pct = improvement / (gap_before + 1e-9) * 100
    
    print(f"\n  Gap Improvement:     {improvement:+.4f} ({pct:+.1f}%)")
    print(f"\n  ✅ Fine-tuned model: {OUTPUT_DIR}/")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
