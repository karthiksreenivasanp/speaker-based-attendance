import io
import os
import sys
import base64
import traceback
import torch
import numpy as np
import librosa
import librosa.display
import matplotlib.pyplot as plt
from fastapi import FastAPI, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse
import uvicorn

# We must adjust the matplotlib backend to non-interactive to avoid GUI thread errors
plt.switch_backend('Agg')

# Import the ML engine from parent directory
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.ml_engine.processing import audio_processor
from app.ml_engine.embedding import speaker_model
from app.api.endpoints.verification import VERIFICATION_THRESHOLD

app = FastAPI(title="Voice AI Internals Viz")

def fig_to_base64(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight')
    buf.seek(0)
    img_b64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)
    return img_b64

def generate_plots(signal_np, sr, title_prefix, color):
    # Waveform
    fig1, ax1 = plt.subplots(figsize=(6, 2))
    librosa.display.waveshow(signal_np, sr=sr, ax=ax1, color=color)
    ax1.set_title(f"{title_prefix} Waveform (Time Domain)")
    ax1.set_xlabel('Time (s)')
    ax1.set_ylabel('Amplitude')
    wave_b64 = fig_to_base64(fig1)

    # Spectrogram
    fig2, ax2 = plt.subplots(figsize=(6, 2.5))
    D = librosa.amplitude_to_db(np.abs(librosa.stft(signal_np)), ref=np.max)
    img = librosa.display.specshow(D, y_axis='mel', x_axis='time', sr=sr, ax=ax2)
    fig2.colorbar(img, ax=ax2, format="%+2.0f dB")
    ax2.set_title(f"{title_prefix} Mel-Spectrogram (Librosa)")
    spec_b64 = fig_to_base64(fig2)

    return wave_b64, spec_b64

def generate_fbank_plot(fbank_tensor, title_prefix):
    # fbank_tensor corresponds to SpeechBrain's internal representation
    # Shape is usually [batch, time, features (80)]
    fbank_np = fbank_tensor.squeeze().cpu().numpy().T # Transpose for standard (feat, time)
    fig, ax = plt.subplots(figsize=(10, 2))
    img = ax.imshow(fbank_np, aspect='auto', origin='lower', cmap='viridis')
    fig.colorbar(img, ax=ax)
    ax.set_title(f"{title_prefix} ECAPA-TDNN Input (Fbank Features)")
    ax.set_ylabel("Filterbank Channel")
    ax.set_xlabel("Time Frames")
    fbank_b64 = fig_to_base64(fig)
    return fbank_b64

@app.get("/")
def get_dashboard():
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Voice AI transparent Viewer</title>
        <style>
            body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #0f172a; color: #f8fafc; padding: 20px; }
            h1, h2, h3 { color: #38bdf8; }
            .container { max-width: 1200px; margin: 0 auto; }
            .card { background: #1e293b; border: 1px solid #334155; padding: 20px; border-radius: 12px; margin-bottom: 20px; box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1); }
            .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
            .btn { background: #38bdf8; color: #0f172a; border: none; padding: 10px 20px; border-radius: 6px; font-weight: bold; cursor: pointer; font-size: 16px; margin-top: 10px; }
            .btn:hover { background: #7dd3fc; }
            img { width: 100%; border-radius: 6px; margin-top: 10px; border: 1px solid #334155; }
            .metric { font-size: 24px; font-weight: bold; padding: 10px; border-radius: 8px; margin-top: 10px; text-align: center; }
            .pass { background: rgba(16, 185, 129, 0.2); color: #34d399; border: 1px solid #059669; }
            .fail { background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid #dc2626; }
            table { width: 100%; text-align: left; margin-top: 10px; border-collapse: collapse; }
            th, td { padding: 8px; border-bottom: 1px solid #334155; }
            .file-input-wrapper { margin-bottom: 20px; }
            label { font-weight: bold; display: block; margin-bottom: 8px; }
            input[type=file] { padding: 10px; background: #0f172a; border-radius: 6px; width: 100%; box-sizing: border-box; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎙️ Voice Verification AI: Internal Transparent Viewer</h1>
            <p>This visualization tool bypasses the standard API to let you inspect the internal states of the Machine Learning models used in your Attendance System.</p>
            
            <div class="card">
                <h2>1. Upload Audio Samples</h2>
                <form id="uploadForm">
                    <div class="grid">
                        <div class="file-input-wrapper">
                            <label>Base / Enrolled Voice (.wav)</label>
                            <input type="file" id="baseAudio" accept="audio/wav" required>
                        </div>
                        <div class="file-input-wrapper">
                            <label>Test / Attempt Voice (.wav)</label>
                            <input type="file" id="testAudio" accept="audio/wav" required>
                        </div>
                    </div>
                    <button type="submit" class="btn" id="analyzeBtn">Analyze Voice Internals</button>
                </form>
            </div>

            <div id="loading" style="display: none; text-align: center; margin: 40px;">
                <h2 style="color: #94a3b8;">Processing Neural Networks... Please wait...</h2>
            </div>
            
            <div id="results" style="display: none;">
                <div class="card">
                    <h2>2. Audio Signal Processing</h2>
                    <p>The system resamples to 16kHz, bandpass filters (80-7000Hz) to isolate human voice, reduces noise, and normalizes volume.</p>
                    <div class="grid">
                        <div>
                            <h3>Base Voice</h3>
                            <img id="baseWave" src="" alt="Base Waveform">
                            <img id="baseSpec" src="" alt="Base Spectrogram">
                        </div>
                        <div>
                            <h3>Test Voice</h3>
                            <img id="testWave" src="" alt="Test Waveform">
                            <img id="testSpec" src="" alt="Test Spectrogram">
                        </div>
                    </div>
                </div>

                <div class="card">
                    <h2>3. ECAPA-TDNN Architecture (Deep Learning)</h2>
                    <p>Before computing the final Cosine Similarity, the <strong>ECAPA-TDNN</strong> (Emphasized Channel Attention, Propagation and Aggregation in Time Delay Neural Network) processes the audio natively. It first computes its own 80-channel Filterbank (Fbank) features.</p>
                    <img id="baseFbank" src="" alt="Base Fbank" style="width: 100%; border: 1px solid #38bdf8; margin-bottom: 10px;">
                    <img id="testFbank" src="" alt="Test Fbank" style="width: 100%; border: 1px solid #38bdf8;">
                    <p style="margin-top: 10px; font-size: 14px; color: #cbd5e1;">^ These are the exact mathematical matrices that the neural network layers process.</p>
                </div>

                <div class="grid">
                    <div class="card">
                        <h2>4. Liveness Check (Anti-Spoofing)</h2>
                        <p>Checks Dynamic Range and Zero-Crossing Rate to try to stop playback spoofing.</p>
                        <div id="livenessMetric" class="metric pass">Score: 0.00 / 1.0</div>
                        <p id="livenessDetail" style="margin-top: 10px; text-align: center;"></p>
                    </div>

                    <div class="card">
                        <h2>5. Extracted AI Embeddings</h2>
                        <p>The TDNN compresses the above Fbank sequence down into a fixed 1-Dimensional biometric fingerprint.</p>
                        <table>
                            <tr><th>Property</th><th>Value</th></tr>
                            <tr><td>Vector Shape</td><td>[192]</td></tr>
                            <tr><td>Network Depth</td><td>TDNN + Attention</td></tr>
                            <tr><td>Vector Type</td><td>Float32 Tensor</td></tr>
                        </table>
                    </div>
                </div>

                <div class="card" style="text-align: center;">
                    <h2>6. Final Decision Matrix</h2>
                    <p>Finally, the system calculates the <strong>Cosine Similarity Distance</strong> between the Base 192-vector and Test 192-vector.</p>
                    <div id="similarityMetric" class="metric" style="font-size: 32px; padding: 20px;">0.00% Match</div>
                    <h3 id="finalVerdict" style="margin-top: 20px;"></h3>
                </div>
            </div>
        </div>

        <script>
            document.getElementById('uploadForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                
                const baseFile = document.getElementById('baseAudio').files[0];
                const testFile = document.getElementById('testAudio').files[0];
                
                if (!baseFile || !testFile) return;

                document.getElementById('analyzeBtn').disabled = true;
                document.getElementById('loading').style.display = 'block';
                document.getElementById('results').style.display = 'none';

                const formData = new FormData();
                formData.append('base_audio', baseFile);
                formData.append('test_audio', testFile);

                try {
                    const response = await fetch('/analyze_audio', {
                        method: 'POST',
                        body: formData
                    });
                    
                    const data = await response.json();
                    
                    // Display Visuals
                    document.getElementById('baseWave').src = 'data:image/png;base64,' + data.base_wave;
                    document.getElementById('baseSpec').src = 'data:image/png;base64,' + data.base_spec;
                    document.getElementById('testWave').src = 'data:image/png;base64,' + data.test_wave;
                    document.getElementById('testSpec').src = 'data:image/png;base64,' + data.test_spec;
                    
                    document.getElementById('baseFbank').src = 'data:image/png;base64,' + data.base_fbank;
                    document.getElementById('testFbank').src = 'data:image/png;base64,' + data.test_fbank;
                    
                    // Liveness
                    const liveEl = document.getElementById('livenessMetric');
                    const liveScore = data.liveness_score;
                    liveEl.innerText = `Liveness Score: ${liveScore.toFixed(2)} / 1.00`;
                    if (liveScore < 0.5) {
                        liveEl.className = 'metric fail';
                        document.getElementById('livenessDetail').innerText = "🚨 SPOOFING DETECTED: Compressed/Noisy audio";
                    } else {
                        liveEl.className = 'metric pass';
                        document.getElementById('livenessDetail').innerText = "✅ Live human recording verified";
                    }

                    // Similarity
                    const simEl = document.getElementById('similarityMetric');
                    const simScore = data.similarity_score;
                    const matchPercent = (simScore * 100).toFixed(2);
                    simEl.innerText = `${matchPercent}% Match`;
                    
                    const verdictEl = document.getElementById('finalVerdict');
                    if (simScore > data.threshold && liveScore >= 0.5) {
                        simEl.className = 'metric pass';
                        verdictEl.innerText = "ACCESS GRANTED. Identities match.";
                        verdictEl.style.color = "#34d399";
                    } else if (simScore > data.threshold && liveScore < 0.5) {
                        simEl.className = 'metric fail';
                        verdictEl.innerText = "ACCESS DENIED. AI matched the voice, but anti-spoofing rejected the recording.";
                        verdictEl.style.color = "#f87171";
                    } else {
                        simEl.className = 'metric fail';
                        verdictEl.innerText = "ACCESS DENIED. Voice signature mismatch.";
                        verdictEl.style.color = "#f87171";
                    }
                    
                    document.getElementById('results').style.display = 'block';
                } catch (err) {
                    console.error(err);
                    alert("Analysis failed: " + (err.message || "Unknown error. Check terminal."));
                } finally {
                    document.getElementById('analyzeBtn').disabled = false;
                    document.getElementById('loading').style.display = 'none';
                }
            });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.post("/analyze_audio")
async def analyze_audio(base_audio: UploadFile = File(...), test_audio: UploadFile = File(...)):
  try:
    # Save to temp
    with open("viz_tmp_base.wav", "wb") as f:
        f.write(await base_audio.read())
    with open("viz_tmp_test.wav", "wb") as f:
        f.write(await test_audio.read())

    # --- Step 1: Process Audio ---
    base_sig = audio_processor.load_audio("viz_tmp_base.wav")
    base_sig = audio_processor.normalize_volume(base_sig)
    base_np = base_sig.squeeze().numpy()

    test_sig = audio_processor.load_audio("viz_tmp_test.wav")
    test_sig = audio_processor.normalize_volume(test_sig)
    test_np = test_sig.squeeze().numpy()

    # --- Step 2: Visualization Plots ---
    b_wv, b_sp = generate_plots(base_np, 16000, "Base", "indigo")
    t_wv, t_sp = generate_plots(test_np, 16000, "Test", "teal")

    # --- Step 3: Liveness & Embedding ---
    live_score = audio_processor.check_liveness(test_sig)
    
    # Internal PyTorch computations for SpeechBrain features to show ECAPA logic
    with torch.no_grad():
        base_fbank_tensor = speaker_model.classifier.mods.compute_features(base_sig)
        test_fbank_tensor = speaker_model.classifier.mods.compute_features(test_sig)
        # Normalize just for plotting purposes (like SpeechBrain mean_var_norm does)
        base_fbank = generate_fbank_plot(base_fbank_tensor, "Base")
        test_fbank = generate_fbank_plot(test_fbank_tensor, "Test")
        
    emb_base = speaker_model.get_embedding(base_sig)
    emb_test = speaker_model.get_embedding(test_sig)
    similarity = speaker_model.compute_similarity(emb_base, emb_test)

    # Cleanup
    os.remove("viz_tmp_base.wav")
    os.remove("viz_tmp_test.wav")

    return {
        "base_wave": b_wv,
        "base_spec": b_sp,
        "test_wave": t_wv,
        "test_spec": t_sp,
        "base_fbank": base_fbank,
        "test_fbank": test_fbank,
        "liveness_score": live_score,
        "similarity_score": similarity,
        "threshold": VERIFICATION_THRESHOLD
    }
  except Exception as e:
    traceback.print_exc()
    return JSONResponse(status_code=500, content={"detail": str(e)})

if __name__ == "__main__":
    print("🚀 Starting Voice AI Visualization Dashboard on http://localhost:8501")
    uvicorn.run(app, host="0.0.0.0", port=8501)
