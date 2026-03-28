import { useCallback, useRef, useState } from "react";

type AudioChunkHandler = (chunk: ArrayBuffer, chunkIndex: number) => void;

function float32ToInt16Buffer(float32Array: Float32Array): ArrayBuffer {
  const buffer = new ArrayBuffer(float32Array.length * 2);
  const view = new DataView(buffer);

  let offset = 0;
  for (let i = 0; i < float32Array.length; i += 1) {
    let sample = Math.max(-1, Math.min(1, float32Array[i]));
    sample = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
    view.setInt16(offset, sample, true);
    offset += 2;
  }

  return buffer;
}

function mergeFloat32Chunks(chunks: Float32Array[]): Float32Array {
  if (!chunks.length) return new Float32Array(0);

  let totalLength = 0;
  for (const chunk of chunks) totalLength += chunk.length;

  const merged = new Float32Array(totalLength);
  let offset = 0;

  for (const chunk of chunks) {
    merged.set(chunk, offset);
    offset += chunk.length;
  }

  return merged;
}

export function useMicrophoneStream(onChunk: AudioChunkHandler) {
  const rawStreamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const sourceNodeRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const highPassRef = useRef<BiquadFilterNode | null>(null);
  const lowPassRef = useRef<BiquadFilterNode | null>(null);
  const compressorRef = useRef<DynamicsCompressorNode | null>(null);
  const gainNodeRef = useRef<GainNode | null>(null);
  const processorNodeRef = useRef<ScriptProcessorNode | null>(null);

  const chunkIndexRef = useRef(0);
  const isStartingRef = useRef(false);

  const preSpeechFramesRef = useRef<Float32Array[]>([]);
  const activeSpeechFramesRef = useRef<Float32Array[]>([]);
  const inSpeechRef = useRef(false);
  const speechCandidateFramesRef = useRef(0);
  const silentFramesRef = useRef(0);
  const speechHoldFramesRef = useRef(0);
  const noiseFloorRef = useRef(0.00035);
  const smoothedRmsRef = useRef(0);

  const [isRecording, setIsRecording] = useState(false);

  const flushFrames = useCallback(
    (frames: Float32Array[]) => {
      if (!frames.length) return;

      const merged = mergeFloat32Chunks(frames);
      if (!merged.length) return;

      const pcmBuffer = float32ToInt16Buffer(merged);
      onChunk(pcmBuffer, chunkIndexRef.current++);
    },
    [onChunk]
  );

  const start = useCallback(async () => {
    if (isStartingRef.current || isRecording) return;
    isStartingRef.current = true;

    try {
      const rawStream = await navigator.mediaDevices.getUserMedia({
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
          channelCount: 1,
          sampleRate: 16000,
        },
      });

      rawStreamRef.current = rawStream;

      const AudioCtx =
        window.AudioContext ||
        (window as any).webkitAudioContext;

      const audioContext = new AudioCtx({ sampleRate: 16000 });
      audioContextRef.current = audioContext;

      if (audioContext.state === "suspended") {
        await audioContext.resume();
      }

      const sourceNode = audioContext.createMediaStreamSource(rawStream);
      sourceNodeRef.current = sourceNode;

      const highPass = audioContext.createBiquadFilter();
      highPass.type = "highpass";
      highPass.frequency.value = 90;

      const lowPass = audioContext.createBiquadFilter();
      lowPass.type = "lowpass";
      lowPass.frequency.value = 4200;

      const compressor = audioContext.createDynamicsCompressor();
      compressor.threshold.value = -28;

      const gainNode = audioContext.createGain();
      gainNode.gain.value = 1.1;

      const processorNode = audioContext.createScriptProcessor(512, 1, 1);
      processorNodeRef.current = processorNode;

      processorNode.onaudioprocess = (event) => {
        const input = event.inputBuffer.getChannelData(0);
        if (!input || input.length === 0) return;

        const frame = new Float32Array(input);

        let peak = 0;
        let sum = 0;

        for (let i = 0; i < frame.length; i++) {
          const v = frame[i];
          const abs = Math.abs(v);
          if (abs > peak) peak = abs;
          sum += v * v;
        }

        const rms = Math.sqrt(sum / frame.length);

        smoothedRmsRef.current =
          smoothedRmsRef.current * 0.82 + rms * 0.18;

        if (!inSpeechRef.current) {
          noiseFloorRef.current =
            noiseFloorRef.current * 0.97 +
            Math.min(smoothedRmsRef.current, 0.003) * 0.03;
        }

        const adaptiveRmsThreshold = Math.max(
          noiseFloorRef.current * 2.2,
          0.00075
        );

        const adaptivePeakThreshold = Math.max(
          noiseFloorRef.current * 6.0,
          0.0028
        );

        const looksLikeSpeech =
          peak > adaptivePeakThreshold &&
          smoothedRmsRef.current > adaptiveRmsThreshold;

        preSpeechFramesRef.current.push(frame);
        if (preSpeechFramesRef.current.length > 4) {
          preSpeechFramesRef.current.shift();
        }

        if (looksLikeSpeech) {
          speechCandidateFramesRef.current++;
          silentFramesRef.current = 0;
          speechHoldFramesRef.current = 6; // 🔥 increased hold
        } else {
          speechCandidateFramesRef.current = 0;
          silentFramesRef.current++;
        }

        if (!inSpeechRef.current) {
          if (speechCandidateFramesRef.current >= 2) {
            inSpeechRef.current = true;
            activeSpeechFramesRef.current.push(...preSpeechFramesRef.current);
            preSpeechFramesRef.current = [];
          } else return;
        }

        if (looksLikeSpeech || speechHoldFramesRef.current > 0) {
          if (!looksLikeSpeech && speechHoldFramesRef.current > 0) {
            speechHoldFramesRef.current--;
          }

          activeSpeechFramesRef.current.push(frame);

          // 🔥 KEY FIX: accumulate before flush
          if (activeSpeechFramesRef.current.length >= 6) {
            flushFrames(activeSpeechFramesRef.current);
            activeSpeechFramesRef.current = [];
          }

          return;
        }

        // 🔥 Add trailing silence frames before flush
        if (activeSpeechFramesRef.current.length > 0) {
          flushFrames(activeSpeechFramesRef.current);
          activeSpeechFramesRef.current = [];
        }

        inSpeechRef.current = false;
        preSpeechFramesRef.current = [];
      };

      sourceNode.connect(highPass);
      highPass.connect(lowPass);
      lowPass.connect(compressor);
      compressor.connect(gainNode);
      gainNode.connect(processorNode);
      processorNode.connect(audioContext.destination);

      setIsRecording(true);
    } catch (error) {
      console.error("Mic start failed:", error);
      setIsRecording(false);
    } finally {
      isStartingRef.current = false;
    }
  }, [flushFrames, isRecording]);

  const stop = useCallback(() => {
    try {
      if (activeSpeechFramesRef.current.length > 0) {
        flushFrames(activeSpeechFramesRef.current);
      }
    } catch {}

    if (processorNodeRef.current) processorNodeRef.current.disconnect();
    if (sourceNodeRef.current) sourceNodeRef.current.disconnect();
    if (rawStreamRef.current) {
      rawStreamRef.current.getTracks().forEach((t) => t.stop());
    }

    setIsRecording(false);
  }, [flushFrames]);

  return { start, stop, isRecording };
}