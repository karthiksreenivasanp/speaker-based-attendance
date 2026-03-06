# =============================================================================
# 🎙️ ECAPA-TDNN Speaker Verification — Baseline Evaluation & Visualization
# =============================================================================
# Google Colab Notebook Code
# Upload your voice-set.zip to Colab, then run all cells
#
# This notebook visualizes:
# 1. Audio waveforms & Mel-Spectrograms for each speaker
# 2. Speaker embeddings extracted by ECAPA-TDNN
# 3. t-SNE visualization of embeddings (2D clustering)
# 4. Cosine similarity heatmap (speaker vs speaker)
# 5. Same-speaker vs Different-speaker score distributions
# 6. Per-speaker accuracy analysis
# =============================================================================

# %%
# ============================================================
# CELL 1: Install Dependencies
# ============================================================
# !pip install speechbrain torch torchaudio soundfile librosa matplotlib
# !pip install scikit-learn seaborn plotly numpy pandas

# %%
# ============================================================
# CELL 2: Imports
# ============================================================
import os
import numpy as np
import torch
import torchaudio
import soundfile as sf
import matplotlib.pyplot as plt
import matplotlib
import seaborn as sns
from collections import defaultdict
from sklearn.manifold import TSNE
from sklearn.metrics import confusion_matrix
import warnings
warnings.filterwarnings('ignore')

# Fix torchaudio backend
if not hasattr(torchaudio, "list_audio_backends"):
    torchaudio.list_audio_backends = lambda: ["soundfile"]

from speechbrain.inference.speaker import EncoderClassifier

print("✅ All imports successful!")

# %%
# ============================================================
# CELL 3: Upload & Extract Dataset
# ============================================================
# For Google Colab: upload voice-set.zip
# from google.colab import files
# uploaded = files.upload()  # Upload voice-set.zip

import zipfile

ZIP_PATH = "voice-set.zip"  # Change this if your zip is elsewhere
EXTRACT_DIR = "voice-set"

if os.path.exists(ZIP_PATH) and not os.path.exists(EXTRACT_DIR):
    with zipfile.ZipFile(ZIP_PATH, 'r') as zip_ref:
        zip_ref.extractall(".")
    print(f"✅ Extracted to {EXTRACT_DIR}/")
elif os.path.exists(EXTRACT_DIR):
    print(f"✅ Dataset already extracted at {EXTRACT_DIR}/")
else:
    print("❌ Please upload voice-set.zip first!")

# Discover speakers
speakers = sorted([
    d for d in os.listdir(EXTRACT_DIR)
    if os.path.isdir(os.path.join(EXTRACT_DIR, d))
])
print(f"\n📊 Found {len(speakers)} speakers:")
for i, s in enumerate(speakers):
    clips = len([f for f in os.listdir(os.path.join(EXTRACT_DIR, s)) if f.endswith('.ogg')])
    print(f"  [{i:02d}] {s} ({clips} clips)")

# %%
# ============================================================
# CELL 4: Load ECAPA-TDNN Model
# ============================================================
print("📦 Loading pre-trained ECAPA-TDNN (VoxCeleb)...")
model = EncoderClassifier.from_hparams(
    source="speechbrain/spkrec-ecapa-voxceleb",
    savedir="pretrained_models/spkrec-ecapa-voxceleb",
)
model.eval()
print("✅ Model loaded!")

# Count parameters
total_params = sum(p.numel() for p in model.mods.embedding_model.parameters())
print(f"   Total parameters: {total_params:,}")
print(f"   Embedding dimension: 192")

# %%
# ============================================================
# CELL 5: Extract Embeddings for ALL Audio Clips
# ============================================================
def load_audio(path, sr=16000):
    """Load and convert audio to 16kHz mono."""
    data, orig_sr = sf.read(path)
    if len(data.shape) > 1:
        data = np.mean(data, axis=1)
    if orig_sr != sr:
        import librosa
        data = librosa.resample(data, orig_sr=orig_sr, target_sr=sr)
    return data, sr

def get_embedding(model, audio_data):
    """Extract 192-dim embedding from audio."""
    signal = torch.FloatTensor(audio_data).unsqueeze(0)
    with torch.no_grad():
        emb = model.encode_batch(signal)
    return emb.squeeze().numpy()

# Extract all embeddings
print("🔄 Extracting embeddings for all clips...")
all_embeddings = []
all_labels = []
all_speaker_names = []
all_clip_nums = []
all_audio_data = {}

speaker_embeddings = defaultdict(list)  # speaker_name -> [embeddings]

for i, speaker in enumerate(speakers):
    speaker_dir = os.path.join(EXTRACT_DIR, speaker)
    ogg_files = sorted([f for f in os.listdir(speaker_dir) if f.endswith('.ogg')])

    for ogg_file in ogg_files:
        clip_num = int(ogg_file.replace('.ogg', '')) if ogg_file.replace('.ogg', '').isdigit() else 0
        file_path = os.path.join(speaker_dir, ogg_file)

        audio_data, sr = load_audio(file_path)
        emb = get_embedding(model, audio_data)

        all_embeddings.append(emb)
        all_labels.append(i)
        all_speaker_names.append(speaker)
        all_clip_nums.append(clip_num)
        all_audio_data[(speaker, clip_num)] = (audio_data, sr)
        speaker_embeddings[speaker].append(emb)

    print(f"  ✅ [{i:02d}] {speaker}: {len(ogg_files)} clips processed")

all_embeddings = np.array(all_embeddings)
all_labels = np.array(all_labels)
print(f"\n📊 Total embeddings: {all_embeddings.shape} (clips × 192-dim)")

# %%
# ============================================================
# CELL 6: VISUALIZATION 1 — Audio Waveforms & Mel-Spectrograms
# ============================================================
fig, axes = plt.subplots(5, 4, figsize=(20, 15))
fig.suptitle('Sample Waveforms & Mel-Spectrograms (5 Speakers)', fontsize=18, fontweight='bold')

sample_speakers = speakers[:5]  # Show first 5 speakers

for row, speaker in enumerate(sample_speakers):
    audio_data, sr = all_audio_data[(speaker, 1)]  # Clip 1

    # Waveform
    ax_wave = axes[row, 0]
    time_axis = np.arange(len(audio_data)) / sr
    ax_wave.plot(time_axis, audio_data, color='#2196F3', linewidth=0.5)
    ax_wave.set_title(f'{speaker} — Waveform', fontsize=10)
    ax_wave.set_xlabel('Time (s)')
    ax_wave.set_ylabel('Amplitude')
    ax_wave.set_ylim(-1, 1)

    # Mel-Spectrogram
    ax_spec = axes[row, 1]
    mel_spec = torchaudio.transforms.MelSpectrogram(
        sample_rate=sr, n_mels=80, n_fft=400, hop_length=160
    )(torch.FloatTensor(audio_data).unsqueeze(0))
    mel_db = torchaudio.transforms.AmplitudeToDB()(mel_spec)
    ax_spec.imshow(mel_db.squeeze().numpy(), aspect='auto', origin='lower', cmap='magma')
    ax_spec.set_title(f'{speaker} — Mel-Spectrogram', fontsize=10)
    ax_spec.set_xlabel('Time Frames')
    ax_spec.set_ylabel('Mel Bins')

    # Waveform clip 2 (different prompt)
    audio_data2, sr2 = all_audio_data.get((speaker, 4), (audio_data, sr))
    ax_wave2 = axes[row, 2]
    time_axis2 = np.arange(len(audio_data2)) / sr2
    ax_wave2.plot(time_axis2, audio_data2, color='#FF5722', linewidth=0.5)
    ax_wave2.set_title(f'{speaker} — Clip 4 Waveform', fontsize=10)
    ax_wave2.set_xlabel('Time (s)')
    ax_wave2.set_ylabel('Amplitude')
    ax_wave2.set_ylim(-1, 1)

    # Mel-Spectrogram clip 2
    ax_spec2 = axes[row, 3]
    mel_spec2 = torchaudio.transforms.MelSpectrogram(
        sample_rate=sr2, n_mels=80, n_fft=400, hop_length=160
    )(torch.FloatTensor(audio_data2).unsqueeze(0))
    mel_db2 = torchaudio.transforms.AmplitudeToDB()(mel_spec2)
    ax_spec2.imshow(mel_db2.squeeze().numpy(), aspect='auto', origin='lower', cmap='magma')
    ax_spec2.set_title(f'{speaker} — Clip 4 Spectrogram', fontsize=10)
    ax_spec2.set_xlabel('Time Frames')
    ax_spec2.set_ylabel('Mel Bins')

plt.tight_layout()
plt.savefig('01_waveforms_spectrograms.png', dpi=150, bbox_inches='tight')
plt.show()
print("✅ Saved: 01_waveforms_spectrograms.png")

# %%
# ============================================================
# CELL 7: VISUALIZATION 2 — t-SNE of Speaker Embeddings
# ============================================================
print("🔄 Computing t-SNE (this may take a minute)...")

tsne = TSNE(n_components=2, random_state=42, perplexity=min(30, len(all_embeddings)-1),
            n_iter=1000, learning_rate='auto')
embeddings_2d = tsne.fit_transform(all_embeddings)

# Create a colormap with distinct colors for 25 speakers
colors = plt.cm.tab20(np.linspace(0, 1, 20))
extra_colors = plt.cm.Set3(np.linspace(0, 1, 12))
all_colors = np.vstack([colors, extra_colors[:5]])

fig, ax = plt.subplots(1, 1, figsize=(16, 12))
fig.suptitle('t-SNE Visualization of Speaker Embeddings (ECAPA-TDNN Baseline)',
             fontsize=18, fontweight='bold')

for i, speaker in enumerate(speakers):
    mask = all_labels == i
    ax.scatter(
        embeddings_2d[mask, 0], embeddings_2d[mask, 1],
        c=[all_colors[i]], label=speaker, s=100, alpha=0.8,
        edgecolors='white', linewidths=0.5
    )
    # Add speaker name near cluster center
    center_x = np.mean(embeddings_2d[mask, 0])
    center_y = np.mean(embeddings_2d[mask, 1])
    ax.annotate(speaker, (center_x, center_y), fontsize=7,
                fontweight='bold', ha='center', va='center',
                bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.7))

ax.set_xlabel('t-SNE Dimension 1', fontsize=12)
ax.set_ylabel('t-SNE Dimension 2', fontsize=12)
ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=8, ncol=2)
ax.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('02_tsne_embeddings.png', dpi=150, bbox_inches='tight')
plt.show()
print("✅ Saved: 02_tsne_embeddings.png")

# %%
# ============================================================
# CELL 8: VISUALIZATION 3 — Cosine Similarity Heatmap
# ============================================================
print("🔄 Computing pairwise cosine similarities...")

# Compute average embedding per speaker
avg_embeddings = []
for speaker in speakers:
    embs = np.array(speaker_embeddings[speaker])
    avg_embeddings.append(np.mean(embs, axis=0))
avg_embeddings = np.array(avg_embeddings)

# Cosine similarity matrix (speaker vs speaker)
from numpy.linalg import norm
def cosine_sim_matrix(embeddings):
    normed = embeddings / (norm(embeddings, axis=1, keepdims=True) + 1e-9)
    return normed @ normed.T

sim_matrix = cosine_sim_matrix(avg_embeddings)

fig, ax = plt.subplots(1, 1, figsize=(14, 12))
mask = np.zeros_like(sim_matrix)
# No masking — show full matrix

sns.heatmap(
    sim_matrix, annot=True, fmt='.2f', cmap='RdYlGn',
    xticklabels=speakers, yticklabels=speakers,
    vmin=-0.1, vmax=1.0, center=0.3,
    square=True, linewidths=0.5,
    cbar_kws={'label': 'Cosine Similarity'}, ax=ax,
    annot_kws={'size': 6}
)
ax.set_title('Speaker-to-Speaker Cosine Similarity (Average Embeddings)\nDiagonal = Same Speaker | Off-diagonal = Different Speakers',
             fontsize=14, fontweight='bold')
ax.set_xticklabels(speakers, rotation=45, ha='right', fontsize=8)
ax.set_yticklabels(speakers, rotation=0, fontsize=8)

plt.tight_layout()
plt.savefig('03_similarity_heatmap.png', dpi=150, bbox_inches='tight')
plt.show()
print("✅ Saved: 03_similarity_heatmap.png")

# %%
# ============================================================
# CELL 9: VISUALIZATION 4 — Same vs Different Speaker Score Distribution
# ============================================================
print("🔄 Computing all pairwise scores...")

cos = torch.nn.CosineSimilarity(dim=0)
same_scores = []
diff_scores = []

for i in range(len(all_embeddings)):
    for j in range(i + 1, len(all_embeddings)):
        score = cos(
            torch.tensor(all_embeddings[i]),
            torch.tensor(all_embeddings[j])
        ).item()

        if all_labels[i] == all_labels[j]:
            same_scores.append(score)
        else:
            diff_scores.append(score)

print(f"  Same-speaker pairs:  {len(same_scores)}")
print(f"  Diff-speaker pairs:  {len(diff_scores)}")
print(f"  Avg same-speaker:    {np.mean(same_scores):.4f} ± {np.std(same_scores):.4f}")
print(f"  Avg diff-speaker:    {np.mean(diff_scores):.4f} ± {np.std(diff_scores):.4f}")

fig, axes = plt.subplots(1, 2, figsize=(18, 6))

# Histogram
ax1 = axes[0]
ax1.hist(same_scores, bins=40, alpha=0.7, color='#4CAF50', label=f'Same Speaker (n={len(same_scores)})', density=True)
ax1.hist(diff_scores, bins=40, alpha=0.7, color='#F44336', label=f'Different Speaker (n={len(diff_scores)})', density=True)
ax1.axvline(x=0.50, color='#FF9800', linestyle='--', linewidth=2, label='Threshold (0.50)')
ax1.set_xlabel('Cosine Similarity Score', fontsize=12)
ax1.set_ylabel('Density', fontsize=12)
ax1.set_title('Score Distribution: Same vs Different Speaker', fontsize=14, fontweight='bold')
ax1.legend(fontsize=10)
ax1.grid(True, alpha=0.3)

# Box plot
ax2 = axes[1]
bp = ax2.boxplot([same_scores, diff_scores],
                  labels=['Same Speaker', 'Different Speaker'],
                  patch_artist=True, showmeans=True,
                  meanprops=dict(marker='D', markerfacecolor='gold', markersize=8))
bp['boxes'][0].set_facecolor('#4CAF50')
bp['boxes'][0].set_alpha(0.7)
bp['boxes'][1].set_facecolor('#F44336')
bp['boxes'][1].set_alpha(0.7)
ax2.axhline(y=0.50, color='#FF9800', linestyle='--', linewidth=2, label='Threshold (0.50)')
ax2.set_ylabel('Cosine Similarity Score', fontsize=12)
ax2.set_title('Score Distribution Comparison', fontsize=14, fontweight='bold')
ax2.legend(fontsize=10)
ax2.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('04_score_distribution.png', dpi=150, bbox_inches='tight')
plt.show()
print("✅ Saved: 04_score_distribution.png")

# %%
# ============================================================
# CELL 10: VISUALIZATION 5 — Per-Clip Similarity Matrix (Full Detail)
# ============================================================
# Compute full clip-to-clip similarity matrix
n = len(all_embeddings)
full_sim = np.zeros((n, n))
for i in range(n):
    for j in range(n):
        full_sim[i, j] = cos(
            torch.tensor(all_embeddings[i]),
            torch.tensor(all_embeddings[j])
        ).item()

# Create labels
clip_labels = [f"{all_speaker_names[i]}_{all_clip_nums[i]}" for i in range(n)]

fig, ax = plt.subplots(1, 1, figsize=(20, 18))
im = ax.imshow(full_sim, cmap='RdYlGn', vmin=-0.1, vmax=1.0, aspect='auto')

# Add speaker boundary lines
boundaries = []
current_label = all_labels[0]
for i in range(1, len(all_labels)):
    if all_labels[i] != current_label:
        boundaries.append(i - 0.5)
        current_label = all_labels[i]

for b in boundaries:
    ax.axhline(y=b, color='black', linewidth=0.5, alpha=0.5)
    ax.axvline(x=b, color='black', linewidth=0.5, alpha=0.5)

ax.set_title('Full Clip-to-Clip Cosine Similarity Matrix\n(Block diagonal = same speaker pairs)',
             fontsize=16, fontweight='bold')
ax.set_xlabel('Clip Index')
ax.set_ylabel('Clip Index')

# Add speaker name labels at block centers
label_positions = []
start = 0
for i in range(1, len(all_labels)):
    if all_labels[i] != all_labels[i-1]:
        mid = (start + i - 1) / 2
        label_positions.append((mid, speakers[all_labels[start]]))
        start = i
mid = (start + len(all_labels) - 1) / 2
label_positions.append((mid, speakers[all_labels[start]]))

ax.set_xticks([pos for pos, _ in label_positions])
ax.set_xticklabels([name for _, name in label_positions], rotation=45, ha='right', fontsize=7)
ax.set_yticks([pos for pos, _ in label_positions])
ax.set_yticklabels([name for _, name in label_positions], fontsize=7)

plt.colorbar(im, ax=ax, label='Cosine Similarity', shrink=0.8)
plt.tight_layout()
plt.savefig('05_full_similarity_matrix.png', dpi=150, bbox_inches='tight')
plt.show()
print("✅ Saved: 05_full_similarity_matrix.png")

# %%
# ============================================================
# CELL 11: VISUALIZATION 6 — Per-Speaker Intra-class Similarity
# ============================================================
intra_similarities = {}
for speaker in speakers:
    embs = speaker_embeddings[speaker]
    scores = []
    for i in range(len(embs)):
        for j in range(i+1, len(embs)):
            s = cos(torch.tensor(embs[i]), torch.tensor(embs[j])).item()
            scores.append(s)
    intra_similarities[speaker] = np.mean(scores) if scores else 0

fig, ax = plt.subplots(1, 1, figsize=(16, 7))
x_pos = range(len(speakers))
colors_bar = ['#4CAF50' if v > 0.5 else '#FF9800' if v > 0.3 else '#F44336'
              for v in intra_similarities.values()]

bars = ax.bar(x_pos, intra_similarities.values(), color=colors_bar, alpha=0.8, edgecolor='white')
ax.axhline(y=0.50, color='red', linestyle='--', linewidth=1.5, label='Verification Threshold (0.50)')
ax.axhline(y=np.mean(list(intra_similarities.values())), color='blue', linestyle=':',
           linewidth=1.5, label=f'Mean ({np.mean(list(intra_similarities.values())):.3f})')

ax.set_xticks(x_pos)
ax.set_xticklabels(speakers, rotation=45, ha='right', fontsize=9)
ax.set_ylabel('Average Intra-Speaker Cosine Similarity', fontsize=12)
ax.set_title('Per-Speaker Voice Consistency\n(How similar are different prompts from the SAME person?)',
             fontsize=14, fontweight='bold')
ax.legend(fontsize=10)
ax.grid(True, alpha=0.3, axis='y')

# Add value labels on bars
for bar_obj, val in zip(bars, intra_similarities.values()):
    ax.text(bar_obj.get_x() + bar_obj.get_width()/2., bar_obj.get_height() + 0.01,
            f'{val:.2f}', ha='center', va='bottom', fontsize=7, fontweight='bold')

plt.tight_layout()
plt.savefig('06_per_speaker_consistency.png', dpi=150, bbox_inches='tight')
plt.show()
print("✅ Saved: 06_per_speaker_consistency.png")

# %%
# ============================================================
# CELL 12: VISUALIZATION 7 — EER Curve (DET Curve)
# ============================================================
from sklearn.metrics import roc_curve, auc

# Create binary labels: 1 = same speaker, 0 = different
y_true = []
y_scores = []
for i in range(len(all_embeddings)):
    for j in range(i + 1, len(all_embeddings)):
        score = cos(torch.tensor(all_embeddings[i]), torch.tensor(all_embeddings[j])).item()
        y_scores.append(score)
        y_true.append(1 if all_labels[i] == all_labels[j] else 0)

y_true = np.array(y_true)
y_scores = np.array(y_scores)

fpr, tpr, thresholds = roc_curve(y_true, y_scores)
roc_auc = auc(fpr, tpr)

# Find EER
fnr = 1 - tpr
eer_idx = np.nanargmin(np.abs(fpr - fnr))
eer = (fpr[eer_idx] + fnr[eer_idx]) / 2
eer_threshold = thresholds[eer_idx]

fig, axes = plt.subplots(1, 2, figsize=(18, 7))

# ROC Curve
ax1 = axes[0]
ax1.plot(fpr, tpr, color='#2196F3', linewidth=2, label=f'ROC (AUC = {roc_auc:.4f})')
ax1.plot([0, 1], [0, 1], 'k--', linewidth=1, alpha=0.5)
ax1.scatter([fpr[eer_idx]], [tpr[eer_idx]], color='red', s=100, zorder=5,
            label=f'EER = {eer:.4f} @ threshold {eer_threshold:.3f}')
ax1.set_xlabel('False Positive Rate', fontsize=12)
ax1.set_ylabel('True Positive Rate', fontsize=12)
ax1.set_title('ROC Curve — Speaker Verification', fontsize=14, fontweight='bold')
ax1.legend(fontsize=10)
ax1.grid(True, alpha=0.3)

# DET Curve
ax2 = axes[1]
ax2.plot(fpr * 100, fnr * 100, color='#FF5722', linewidth=2, label='DET Curve')
ax2.plot([0, 100], [0, 100], 'k--', linewidth=1, alpha=0.5)
ax2.scatter([fpr[eer_idx]*100], [fnr[eer_idx]*100], color='red', s=100, zorder=5,
            label=f'EER = {eer*100:.2f}%')
ax2.set_xlabel('False Positive Rate (%)', fontsize=12)
ax2.set_ylabel('False Negative Rate (%)', fontsize=12)
ax2.set_title('DET Curve — Equal Error Rate', fontsize=14, fontweight='bold')
ax2.legend(fontsize=10)
ax2.grid(True, alpha=0.3)
ax2.set_xlim(0, max(fpr*100) + 5)
ax2.set_ylim(0, max(fnr*100) + 5)

plt.tight_layout()
plt.savefig('07_roc_det_curves.png', dpi=150, bbox_inches='tight')
plt.show()
print("✅ Saved: 07_roc_det_curves.png")

# %%
# ============================================================
# CELL 13: VISUALIZATION 8 — Embedding Dimension Analysis
# ============================================================
fig, axes = plt.subplots(2, 2, figsize=(16, 12))
fig.suptitle('Embedding Analysis', fontsize=18, fontweight='bold')

# 1. Embedding heatmap for first 10 speakers
ax1 = axes[0, 0]
emb_display = []
labels_display = []
for i, speaker in enumerate(speakers[:10]):
    avg = np.mean(speaker_embeddings[speaker], axis=0)
    emb_display.append(avg)
    labels_display.append(speaker)
emb_display = np.array(emb_display)
im1 = ax1.imshow(emb_display, aspect='auto', cmap='coolwarm')
ax1.set_yticks(range(len(labels_display)))
ax1.set_yticklabels(labels_display, fontsize=9)
ax1.set_xlabel('Embedding Dimensions (0-191)')
ax1.set_title('Average Embedding per Speaker (first 10)')
plt.colorbar(im1, ax=ax1)

# 2. Variance across dimensions
ax2 = axes[0, 1]
dim_variance = np.var(all_embeddings, axis=0)
ax2.bar(range(192), dim_variance, color='#2196F3', alpha=0.7)
ax2.set_xlabel('Embedding Dimension')
ax2.set_ylabel('Variance')
ax2.set_title('Per-Dimension Variance Across All Speakers')

# 3. L2 norm distribution
ax3 = axes[1, 0]
norms = np.linalg.norm(all_embeddings, axis=1)
ax3.hist(norms, bins=30, color='#9C27B0', alpha=0.7, edgecolor='white')
ax3.set_xlabel('L2 Norm of Embedding')
ax3.set_ylabel('Count')
ax3.set_title(f'Embedding Norm Distribution (mean={np.mean(norms):.2f})')

# 4. PCA variance explained
from sklearn.decomposition import PCA
pca = PCA(n_components=50)
pca.fit(all_embeddings)
ax4 = axes[1, 1]
cumvar = np.cumsum(pca.explained_variance_ratio_) * 100
ax4.plot(range(1, 51), cumvar, 'o-', color='#FF5722', markersize=3)
ax4.axhline(y=95, color='gray', linestyle='--', alpha=0.5, label='95% threshold')
n_95 = np.argmax(cumvar >= 95) + 1
ax4.axvline(x=n_95, color='green', linestyle='--', alpha=0.5, label=f'{n_95} dims for 95%')
ax4.set_xlabel('Number of Principal Components')
ax4.set_ylabel('Cumulative Variance Explained (%)')
ax4.set_title('PCA — How Many Dims Are Actually Used?')
ax4.legend()
ax4.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('08_embedding_analysis.png', dpi=150, bbox_inches='tight')
plt.show()
print("✅ Saved: 08_embedding_analysis.png")

# %%
# ============================================================
# CELL 14: SUMMARY REPORT
# ============================================================
print("=" * 60)
print("  📊 BASELINE EVALUATION SUMMARY")
print("=" * 60)
print(f"\n  Model:              ECAPA-TDNN (SpeechBrain)")
print(f"  Training Data:      VoxCeleb1 + VoxCeleb2 (7,363 speakers)")
print(f"  Parameters:         {total_params:,}")
print(f"  Embedding Dim:      192")
print(f"\n  YOUR DATASET:")
print(f"  Speakers:           {len(speakers)}")
print(f"  Total Clips:        {len(all_embeddings)}")
print(f"  Total Duration:     ~7.6 minutes")
print(f"\n  PERFORMANCE METRICS:")
print(f"  Avg Same-Speaker:   {np.mean(same_scores):.4f} ± {np.std(same_scores):.4f}")
print(f"  Avg Diff-Speaker:   {np.mean(diff_scores):.4f} ± {np.std(diff_scores):.4f}")
print(f"  Separation Gap:     {np.mean(same_scores) - np.mean(diff_scores):.4f}")
print(f"  EER:                {eer*100:.2f}%")
print(f"  EER Threshold:      {eer_threshold:.3f}")
print(f"  ROC AUC:            {roc_auc:.4f}")
print(f"\n  VERDICT:")
if np.mean(same_scores) > 0.5:
    print(f"  ✅ Same-speaker scores are ABOVE threshold (0.50)")
else:
    print(f"  ⚠️  Same-speaker scores are BELOW threshold — fine-tuning recommended!")
if np.mean(diff_scores) < 0.3:
    print(f"  ✅ Diff-speaker scores are well separated")
else:
    print(f"  ⚠️  Diff-speaker scores are too high — risk of false matches!")
print(f"\n  FILES GENERATED:")
print(f"  01_waveforms_spectrograms.png")
print(f"  02_tsne_embeddings.png")
print(f"  03_similarity_heatmap.png")
print(f"  04_score_distribution.png")
print(f"  05_full_similarity_matrix.png")
print(f"  06_per_speaker_consistency.png")
print(f"  07_roc_det_curves.png")
print(f"  08_embedding_analysis.png")
print("=" * 60)
