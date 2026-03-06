#!/usr/bin/env python3
"""
prepare_dataset.py
==================
Converts voice-set/ (.ogg) → processed .wav files (16kHz mono).
Creates train.csv and val.csv manifests for fine-tuning.

Split: Clips 1-5 → train, Clips 6-7 → validation
"""

import os
import sys
import csv
import numpy as np
import soundfile as sf

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
VOICE_SET_DIR = os.path.join(PROJECT_DIR, "voice-set")
OUTPUT_DIR = os.path.join(PROJECT_DIR, "dataset_processed")
TRAIN_CSV = os.path.join(OUTPUT_DIR, "train.csv")
VAL_CSV = os.path.join(OUTPUT_DIR, "val.csv")
SAMPLE_RATE = 16000


def convert_ogg_to_wav(ogg_path, wav_path):
    """Convert .ogg to .wav at 16kHz mono using soundfile."""
    try:
        # Read OGG (soundfile supports OGG via libsndfile)
        data, sr = sf.read(ogg_path)
        
        # Convert stereo to mono if needed
        if len(data.shape) > 1:
            data = np.mean(data, axis=1)
        
        # Resample if needed
        if sr != SAMPLE_RATE:
            import librosa
            data = librosa.resample(data, orig_sr=sr, target_sr=SAMPLE_RATE)
        
        # Normalize to prevent clipping
        if np.max(np.abs(data)) > 0:
            data = data / np.max(np.abs(data)) * 0.95
        
        # Write WAV
        sf.write(wav_path, data, SAMPLE_RATE, subtype='PCM_16')
        return True, len(data) / SAMPLE_RATE
    except Exception as e:
        print(f"  ⚠️  Error converting {ogg_path}: {e}")
        return False, 0


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # Discover speakers
    speakers = sorted([
        d for d in os.listdir(VOICE_SET_DIR) 
        if os.path.isdir(os.path.join(VOICE_SET_DIR, d))
    ])
    
    print(f"{'='*60}")
    print(f"  DATASET PREPARATION")
    print(f"  Found {len(speakers)} speakers")
    print(f"{'='*60}")
    
    for i, s in enumerate(speakers):
        print(f"  [{i:02d}] {s}")
    
    # Create speaker ID mapping
    speaker_to_id = {name: idx for idx, name in enumerate(speakers)}
    
    # Save speaker mapping for reference
    mapping_path = os.path.join(OUTPUT_DIR, "speaker_mapping.csv")
    with open(mapping_path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(["speaker_id", "speaker_name"])
        for name, sid in sorted(speaker_to_id.items(), key=lambda x: x[1]):
            w.writerow([sid, name])
    
    train_rows = []
    val_rows = []
    total_converted = 0
    total_duration = 0
    errors = 0
    
    for speaker_name in speakers:
        speaker_id = speaker_to_id[speaker_name]
        speaker_ogg_dir = os.path.join(VOICE_SET_DIR, speaker_name)
        speaker_wav_dir = os.path.join(OUTPUT_DIR, f"speaker_{speaker_id:03d}")
        os.makedirs(speaker_wav_dir, exist_ok=True)
        
        # Find all .ogg files
        ogg_files = sorted([
            f for f in os.listdir(speaker_ogg_dir) 
            if f.endswith('.ogg')
        ], key=lambda x: int(x.replace('.ogg', '')) if x.replace('.ogg', '').isdigit() else 0)
        
        print(f"\n[{speaker_id:02d}] {speaker_name}: {len(ogg_files)} clips")
        
        for ogg_file in ogg_files:
            ogg_path = os.path.join(speaker_ogg_dir, ogg_file)
            clip_num_str = ogg_file.replace('.ogg', '')
            clip_num = int(clip_num_str) if clip_num_str.isdigit() else 0
            wav_filename = f"clip_{clip_num}.wav"
            wav_path = os.path.join(speaker_wav_dir, wav_filename)
            
            success, duration = convert_ogg_to_wav(ogg_path, wav_path)
            if not success:
                errors += 1
                continue
            
            total_converted += 1
            total_duration += duration
            
            # Split: clips 1-5 → train, 6-7 → val
            row = {
                "file_path": os.path.abspath(wav_path),
                "speaker_id": speaker_id,
                "speaker_name": speaker_name,
                "clip_num": clip_num,
                "duration": f"{duration:.2f}"
            }
            
            if clip_num <= 5:
                train_rows.append(row)
            else:
                val_rows.append(row)
            
            split_label = "TRAIN" if clip_num <= 5 else "VAL"
            print(f"  ✅ {ogg_file} → {wav_filename} ({duration:.1f}s) [{split_label}]")
    
    # Write CSVs
    fieldnames = ["file_path", "speaker_id", "speaker_name", "clip_num", "duration"]
    
    with open(TRAIN_CSV, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(train_rows)
    
    with open(VAL_CSV, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(val_rows)
    
    print(f"\n{'='*60}")
    print(f"  ✅ DATASET PREPARATION COMPLETE!")
    print(f"  Speakers      : {len(speakers)}")
    print(f"  Converted      : {total_converted} files")
    print(f"  Total Duration : {total_duration:.1f} seconds ({total_duration/60:.1f} min)")
    print(f"  Errors         : {errors}")
    print(f"  Training Set   : {len(train_rows)} clips → {TRAIN_CSV}")
    print(f"  Validation Set : {len(val_rows)} clips → {VAL_CSV}")
    print(f"  Speaker Map    : {mapping_path}")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
