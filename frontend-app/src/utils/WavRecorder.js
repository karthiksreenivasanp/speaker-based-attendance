export class WavRecorder {
    constructor(sampleRate = 16000) {
        this.context = null;
        this.stream = null;
        this.recorder = null;
        this.audioInput = null;
        this.targetSampleRate = sampleRate;
        this._isRecording = false;
        this.chunks = [];
    }

    async start() {
        this.context = new (window.AudioContext || window.webkitAudioContext)();
        this.stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        this.audioInput = this.context.createMediaStreamSource(this.stream);

        // Use ScriptProcessor (legacy but works everywhere) or AudioWorklet
        // For simplicity/compatibility in a single file: ScriptProcessor
        this.recorder = this.context.createScriptProcessor(4096, 1, 1);

        this.chunks = [];
        this.recorder.onaudioprocess = (e) => {
            if (!this._isRecording) return;
            const channelData = e.inputBuffer.getChannelData(0);
            this.chunks.push(new Float32Array(channelData));
        };

        this.audioInput.connect(this.recorder);
        this.recorder.connect(this.context.destination);
        this._isRecording = true;
    }

    async stop() {
        this._isRecording = false;
        if (this.stream) {
            this.stream.getTracks().forEach(t => t.stop());
        }
        if (this.context) {
            this.context.close();
        }
        if (this.recorder) {
            this.recorder.disconnect();
        }
        if (this.audioInput) {
            this.audioInput.disconnect();
        }

        return this.exportWAV();
    }

    exportWAV() {
        const buffer = this.mergeBuffers(this.chunks);
        const downsampledBuffer = this.downsampleBuffer(buffer, this.targetSampleRate);
        const encodedWav = this.encodeWAV(downsampledBuffer);
        return new Blob([encodedWav], { type: 'audio/wav' });
    }

    mergeBuffers(chunks) {
        let length = 0;
        chunks.forEach(c => length += c.length);
        const result = new Float32Array(length);
        let offset = 0;
        chunks.forEach(c => {
            result.set(c, offset);
            offset += c.length;
        });
        return result;
    }

    downsampleBuffer(buffer, targetRate) {
        if (!this.context) return buffer; // Should not happen
        const sampleRate = this.context.sampleRate;
        if (targetRate === sampleRate) return buffer;
        if (targetRate > sampleRate) return buffer;

        const sampleRateRatio = sampleRate / targetRate;
        const newLength = Math.round(buffer.length / sampleRateRatio);
        const result = new Float32Array(newLength);
        let offsetResult = 0;
        let offsetBuffer = 0;

        while (offsetResult < result.length) {
            const nextOffsetBuffer = Math.round((offsetResult + 1) * sampleRateRatio);
            let accum = 0, count = 0;
            for (let i = offsetBuffer; i < nextOffsetBuffer && i < buffer.length; i++) {
                accum += buffer[i];
                count++;
            }
            result[offsetResult] = accum / count;
            offsetResult++;
            offsetBuffer = nextOffsetBuffer;
        }
        return result;
    }

    encodeWAV(samples) {
        const buffer = new ArrayBuffer(44 + samples.length * 2);
        const view = new DataView(buffer);

        /* RIFF identifier */
        this.writeString(view, 0, 'RIFF');
        /* RIFF chunk length */
        view.setUint32(4, 36 + samples.length * 2, true);
        /* RIFF type */
        this.writeString(view, 8, 'WAVE');
        /* format chunk identifier */
        this.writeString(view, 12, 'fmt ');
        /* format chunk length */
        view.setUint32(16, 16, true);
        /* sample format (raw) */
        view.setUint16(20, 1, true);
        /* channel count */
        view.setUint16(22, 1, true);
        /* sample rate */
        view.setUint32(24, this.targetSampleRate, true);
        /* byte rate (sample rate * block align) */
        view.setUint32(28, this.targetSampleRate * 2, true);
        /* block align (channel count * bytes per sample) */
        view.setUint16(32, 2, true);
        /* bits per sample */
        view.setUint16(34, 16, true);
        /* data chunk identifier */
        this.writeString(view, 36, 'data');
        /* data chunk length */
        view.setUint32(40, samples.length * 2, true);

        this.floatTo16BitPCM(view, 44, samples);

        return view;
    }

    floatTo16BitPCM(output, offset, input) {
        for (let i = 0; i < input.length; i++, offset += 2) {
            const s = Math.max(-1, Math.min(1, input[i]));
            output.setInt16(offset, s < 0 ? s * 0x8000 : s * 0x7FFF, true);
        }
    }

    writeString(view, offset, string) {
        for (let i = 0; i < string.length; i++) {
            view.setUint8(offset + i, string.charCodeAt(i));
        }
    }
}
