import os
import sys
import torch
import numpy as np
import pandas as pd
import librosa
import librosa.display
import matplotlib.pyplot as plt
import seaborn as sns
import streamlit as st
from sklearn.metrics import confusion_matrix, f1_score, accuracy_score, precision_score, recall_score

# Ensure the parent directory is in the path to import backend modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.ml_engine.processing import audio_processor
from app.ml_engine.embedding import speaker_model
from app.api.endpoints.verification import VERIFICATION_THRESHOLD

st.set_page_config(page_title="Voice Attendance AI Visualization", layout="wide")

st.title("🎙️ Voice Biometrics: Internal AI Visualizer")
st.markdown("""
This dashboard provides a transparent look into exactly how your **Fine-Tuned ECAPA-TDNN System** processes human voice, prevents spoofing, and makes decisions.
""")

tab1, tab2 = st.tabs(["🔍 Internal Pipeline (Audio -> Math)", "📊 Fine-Tuned Model Performance"])

def plot_waveform(signal, sr, title, color="blue"):
    fig, ax = plt.subplots(figsize=(8, 2))
    librosa.display.waveshow(signal, sr=sr, ax=ax, color=color)
    ax.set_title(f"{title}: Time-Domain Waveform")
    ax.set_ylabel("Amplitude")
    ax.set_xlabel("Time (s)")
    return fig

def plot_spectrogram(signal, sr, title):
    fig, ax = plt.subplots(figsize=(8, 3))
    D = librosa.amplitude_to_db(np.abs(librosa.stft(signal)), ref=np.max)
    img = librosa.display.specshow(D, y_axis='mel', x_axis='time', sr=sr, ax=ax)
    fig.colorbar(img, ax=ax, format="%+2.0f dB")
    ax.set_title(f"{title}: Mel-Spectrogram (Frequency Domain)")
    return fig

def plot_fbank(fbank_tensor, title):
    fbank_np = fbank_tensor.squeeze().cpu().numpy().T
    fig, ax = plt.subplots(figsize=(8, 3))
    img = ax.imshow(fbank_np, aspect='auto', origin='lower', cmap='viridis')
    fig.colorbar(img, ax=ax)
    ax.set_title(f"{title}: ECAPA-TDNN Actual Input (80-Dim Filterbank)")
    ax.set_ylabel("Filterbank Channel")
    ax.set_xlabel("Time Frames")
    return fig

with tab1:
    st.header("1. Upload Audio to Trace the Pipeline")
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Base Voice (Enrolled)")
        base_file = st.file_uploader("Upload Base Audio File (.wav, .ogg)", type=['wav', 'ogg'], key="base")
        if base_file:
            st.audio(base_file)
            
    with col2:
        st.subheader("Test Voice (Attempt)")
        test_file = st.file_uploader("Upload Test Audio File (.wav, .ogg)", type=['wav', 'ogg'], key="test")
        if test_file:
            st.audio(test_file)

    if base_file and test_file:
        with st.spinner("Processing through AI Pipeline..."):
            # Save temp files for backend processor
            with open("/tmp/viz_base.wav", "wb") as f: f.write(base_file.getbuffer())
            with open("/tmp/viz_test.wav", "wb") as f: f.write(test_file.getbuffer())

            # Pipeline Step 1: Loading & Normalization
            st.markdown("---")
            st.header("Step 1: Audio Signal Preprocessing")
            st.markdown("Raw audio is loaded, resampled to 16kHz, bandpass filtered to isolate human speech frequencies, and volume-normalized.")
            
            base_sig = audio_processor.load_audio("/tmp/viz_base.wav")
            base_sig = audio_processor.normalize_volume(base_sig)
            base_np = base_sig.squeeze().numpy()

            test_sig = audio_processor.load_audio("/tmp/viz_test.wav")
            test_sig = audio_processor.normalize_volume(test_sig)
            test_np = test_sig.squeeze().numpy()

            c1, c2 = st.columns(2)
            with c1:
                st.pyplot(plot_waveform(base_np, 16000, "Base", "indigo"))
                st.pyplot(plot_spectrogram(base_np, 16000, "Base"))
            with c2:
                st.pyplot(plot_waveform(test_np, 16000, "Test", "teal"))
                st.pyplot(plot_spectrogram(test_np, 16000, "Test"))

            # Pipeline Step 2: Liveness
            st.markdown("---")
            st.header("Step 2: Anti-Spoofing Liveness Check")
            live_score = audio_processor.check_liveness(test_sig)
            st.metric("Liveness Score", f"{live_score:.2f} / 1.00", delta="Human passing threshold: 0.50" if live_score >= 0.5 else "SPOOF DETECTED", delta_color="normal" if live_score >= 0.5 else "inverse")

            # Pipeline Step 3: Neural Network Processing
            st.markdown("---")
            st.header("Step 3: ECAPA-TDNN Neural Network Processing")
            st.markdown("The system converts the audio into an 80-channel filterbank, which is the exact mathematical matrix fed into the convolutional layers.")
            
            with torch.no_grad():
                base_fbank_tensor = speaker_model.classifier.mods.compute_features(base_sig)
                test_fbank_tensor = speaker_model.classifier.mods.compute_features(test_sig)
            
            c3, c4 = st.columns(2)
            with c3: st.pyplot(plot_fbank(base_fbank_tensor, "Base"))
            with c4: st.pyplot(plot_fbank(test_fbank_tensor, "Test"))

            # Pipeline Step 4: Embeddings
            st.markdown("---")
            st.header("Step 4: Deep Embeddings & Decision")
            emb_base = speaker_model.get_embedding(base_sig)
            emb_test = speaker_model.get_embedding(test_sig)
            
            # Show embedding heatmap
            fig_emb, ax_emb = plt.subplots(figsize=(10, 2))
            emb_stacked = np.vstack([emb_base.flatten(), emb_test.flatten()])
            sns.heatmap(emb_stacked, cmap="coolwarm", cbar=True, ax=ax_emb, yticklabels=["Base (192-dim)", "Test (192-dim)"])
            ax_emb.set_title("Biometric Fingerprints (192-Dimensional Vectors)")
            ax_emb.set_xlabel("Vector Dimension")
            st.pyplot(fig_emb)

            similarity = speaker_model.compute_similarity(emb_base, emb_test)
            st.markdown(f"### Mathematical Cosine Distance: `{similarity:.4f}`")
            st.markdown(f"**Verification Threshold:** `{VERIFICATION_THRESHOLD:.4f}`")
            
            if similarity >= VERIFICATION_THRESHOLD:
                st.success(f"✅ ACCESS GRANTED! The AI verified these voices belong to the identical speaker with a {(similarity*100):.1f}% match score.")
            else:
                st.error(f"❌ ACCESS DENIED! Voice mis-match. The system correctly blocked the attempt.")


with tab2:
    st.header("📊 Dataset Evaluation & Fine-Tuned Metrics")
    st.markdown("Click below to run your fine-tuned model across all test samples in your validation dataset to generate the live Confusion Matrix and F1 Scores.")
    
    if st.button("Run Model against Validation Dataset"):
        val_csv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'dataset_processed', 'val.csv'))
        
        if not os.path.exists(val_csv_path):
            st.error(f"Validation dataset not found at {val_csv_path}")
        else:
            with st.spinner("Extracting embeddings for all 50 validation files..."):
                df = pd.read_csv(val_csv_path)
                
                # Pre-calculate embeddings to save time
                embeddings = {} # file_path -> embedding
                for idx, row in df.iterrows():
                    path = row['file_path']
                    if os.path.exists(path):
                        sig = audio_processor.load_audio(path)
                        sig = audio_processor.normalize_volume(sig)
                        emb = speaker_model.get_embedding(sig)
                        embeddings[path] = emb
                
                st.write(f"✅ Extracted {len(embeddings)} biometric embeddings.")
                
            with st.spinner("Computing pairwise combinations... (This tests Same Speaker vs Different Speaker)"):
                labels_true = []
                labels_pred = []
                similarities = []
                types = []
                
                # Pair every file against every other file
                files = list(embeddings.keys())
                for i in range(len(files)):
                    for j in range(i+1, len(files)):
                        f1, f2 = files[i], files[j]
                        
                        speaker1 = df[df['file_path'] == f1]['speaker_id'].values[0]
                        speaker2 = df[df['file_path'] == f2]['speaker_id'].values[0]
                        
                        is_same_speaker = 1 if speaker1 == speaker2 else 0
                        labels_true.append(is_same_speaker)
                        types.append("Same Speaker" if is_same_speaker else "Different Speaker")
                        
                        sim = speaker_model.compute_similarity(embeddings[f1], embeddings[f2])
                        similarities.append(sim)
                        
                        # Apply application threshold
                        prediction = 1 if sim >= VERIFICATION_THRESHOLD else 0
                        labels_pred.append(prediction)
                
                st.write(f"✅ Evaluated {len(similarities)} total access attempts.")
                
                # Metrics
                f1 = f1_score(labels_true, labels_pred)
                acc = accuracy_score(labels_true, labels_pred)
                prec = precision_score(labels_true, labels_pred)
                rec = recall_score(labels_true, labels_pred)
                
                st.markdown("---")
                st.markdown("### Fine-Tuned Model Performance Metrics")
                
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("System Accuracy", f"{acc*100:.1f}%")
                m2.metric("F1 Score", f"{f1*100:.1f}%")
                m3.metric("Precision (Security)", f"{prec*100:.1f}%")
                m4.metric("Recall (Convenience)", f"{rec*100:.1f}%")
                
                st.markdown("#### Performance Comparison")
                metrics_df = pd.DataFrame({
                    'Score (%)': [acc*100, f1*100, prec*100, rec*100]
                }, index=['Accuracy', 'F1 Score', 'Precision', 'Recall'])
                st.bar_chart(metrics_df)
                
                st.markdown("---")
                c1, c2 = st.columns(2)
                
                with c1:
                    st.markdown("### Confusion Matrix")
                    st.markdown("Based on standard application threshold of `0.20`")
                    cm = confusion_matrix(labels_true, labels_pred)
                    fig_cm, ax_cm = plt.subplots(figsize=(6, 5))
                    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues', ax=ax_cm,
                               xticklabels=['Predicted Imposter', 'Predicted Genuine'],
                               yticklabels=['Actual Imposter', 'Actual Genuine'])
                    st.pyplot(fig_cm)
                    
                with c2:
                    st.markdown("### Score Distribution (Separation Gap)")
                    st.markdown("Shows how well the fine-tuned model separates true students from imposters.")
                    df_viz = pd.DataFrame({'Similarity': similarities, 'Type': types})
                    fig_dist, ax_dist = plt.subplots(figsize=(7, 5))
                    sns.kdeplot(data=df_viz, x="Similarity", hue="Type", fill=True, alpha=0.5, ax=ax_dist)
                    ax_dist.axvline(x=VERIFICATION_THRESHOLD, color='red', linestyle='--', label=f'Threshold ({VERIFICATION_THRESHOLD})')
                    ax_dist.legend()
                    st.pyplot(fig_dist)
