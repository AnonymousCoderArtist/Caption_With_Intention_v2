/**
 * Browser speech recognition (Web Speech API) for Auto captions.
 *
 * The video never leaves this computer: it plays locally at 1x speed and the
 * browser's own speech recognizer listens to its audio track
 * (SpeechRecognition.start(audioTrack), Chrome/Edge 135+, Firefox 160+).
 *
 * Honest limits, mirrored in the UI copy:
 * - Real time only: a 10 minute video takes 10 minutes.
 * - Utterance-level results with no word timings: words are spread evenly
 *   inside each phrase, so CWI per-word styling needs review afterwards.
 * - On-device recognition (processLocally) needs a one-time language pack
 *   download; server-based recognition sends audio to the browser vendor's
 *   speech service and needs internet. The panel defaults to on-device.
 */

export interface BrowserSpeechSupport {
  /** SpeechRecognition constructor exists at all. */
  engine: boolean;
  /** Media elements can hand their audio to the recognizer. */
  capture: boolean;
  /** start(audioTrack) is believed supported (UA version gate). */
  trackInput: boolean;
  /** True when the whole browser path can run. */
  ok: boolean;
  /** Human-readable reason when not ok. */
  reason?: string;
}

export type OnDeviceStatus = 'available' | 'downloadable' | 'unavailable' | 'unknown';

export interface FinalPiece {
  text: string;
  /** Video time in seconds when the final result arrived. */
  at: number;
  confidence?: number;
}

export interface TranscriptEntry {
  text: string;
  start: number;
  end: number;
  confidence?: number;
}

export interface BrowserTranscript {
  transcript: TranscriptEntry[];
  width: number;
  height: number;
  fps: number;
}

type SpeechRecognitionCtor = new () => SpeechRecognitionLike;

interface SpeechRecognitionResultLike {
  isFinal: boolean;
  0: { transcript: string; confidence: number };
  length: number;
}

interface SpeechRecognitionLike {
  continuous: boolean;
  interimResults: boolean;
  lang: string;
  processLocally?: boolean;
  onresult: ((event: { resultIndex: number; results: ArrayLike<SpeechRecognitionResultLike> }) => void) | null;
  onerror: ((event: { error: string }) => void) | null;
  onend: (() => void) | null;
  start(audioTrack?: MediaStreamTrack): void;
  stop(): void;
  abort(): void;
}

function ctor(): SpeechRecognitionCtor | null {
  const w = window as unknown as { SpeechRecognition?: SpeechRecognitionCtor; webkitSpeechRecognition?: SpeechRecognitionCtor };
  return w.SpeechRecognition || w.webkitSpeechRecognition || null;
}

/** Chrome/Edge 135+ or Firefox 160+ is required for start(audioTrack). */
function versionGate(): boolean {
  const ua = navigator.userAgent;
  const chrome = /(?:Chrome|Edg|EdgA|EdgiOS)\/(\d+)/.exec(ua);
  if (chrome) return Number(chrome[1]) >= 135;
  const firefox = /Firefox\/(\d+)/.exec(ua);
  if (firefox) return Number(firefox[1]) >= 160;
  // Unknown engine (e.g. Safari with SpeechRecognition one day): do not risk
  // the recognizer silently falling back to the microphone.
  return false;
}

export function detectSupport(): BrowserSpeechSupport {
  const engine = ctor() !== null;
  const proto = HTMLMediaElement.prototype as unknown as { captureStream?: unknown; mozCaptureStream?: unknown };
  const capture = typeof proto.captureStream === 'function' || typeof proto.mozCaptureStream === 'function';
  const trackInput = engine && versionGate();
  const ok = engine && capture && trackInput;
  let reason: string | undefined;
  if (!engine) reason = 'Browser speech needs Chrome, Edge or Firefox 160 or newer. Safari cannot do this yet.';
  else if (!capture) reason = 'This browser cannot hand the video audio to its speech recognizer.';
  else if (!trackInput) reason = 'Browser speech from a video file needs Chrome or Edge 135+ or Firefox 160+. Update the browser, or use a speech model below.';
  return { engine, capture, trackInput, ok, reason };
}

/** On-device language pack status; 'unknown' on browsers without available(). */
export async function onDeviceStatus(lang: string): Promise<OnDeviceStatus> {
  const Ctor = (window as unknown as { SpeechRecognition?: { available?: (opts: { langs: string[]; processLocally: boolean }) => Promise<string> } }).SpeechRecognition;
  if (!Ctor || typeof Ctor.available !== 'function') return 'unknown';
  try {
    const status = await Ctor.available({ langs: [lang], processLocally: true });
    return status === 'available' || status === 'downloadable' ? status : 'unavailable';
  } catch {
    return 'unknown';
  }
}

/** Download the on-device language pack. Resolves true when it is ready. */
export async function installOnDevice(lang: string): Promise<boolean> {
  const Ctor = (window as unknown as { SpeechRecognition?: { install?: (opts: { langs: string[]; processLocally: boolean }) => Promise<boolean> } }).SpeechRecognition;
  if (!Ctor || typeof Ctor.install !== 'function') return false;
  try {
    await Ctor.install({ langs: [lang], processLocally: true });
    return (await onDeviceStatus(lang)) === 'available';
  } catch {
    return false;
  }
}

/**
 * Turn final recognition results into caption entries. Utterance-level only:
 * the end is the video time when the result arrived, the start is estimated
 * from word count but never overlaps the previous entry. Pure and tested.
 */
export function assembleTranscript(pieces: FinalPiece[]): TranscriptEntry[] {
  const entries: TranscriptEntry[] = [];
  let prevEnd = 0;
  for (const piece of pieces) {
    const text = piece.text.trim().replace(/\s+/g, ' ');
    if (!text) continue;
    const words = text.split(' ').length;
    const estimated = Math.min(12, Math.max(0.6, 0.34 * words + 0.25));
    const end = Math.max(piece.at, prevEnd + 0.2);
    let start = Math.max(prevEnd, end - estimated);
    if (start >= end) start = Math.max(0, end - 0.4);
    const entry: TranscriptEntry = { text, start: Number(start.toFixed(3)), end: Number(end.toFixed(3)) };
    if (typeof piece.confidence === 'number' && piece.confidence >= 0 && piece.confidence <= 1) {
      entry.confidence = Number(piece.confidence.toFixed(3));
    }
    entries.push(entry);
    prevEnd = entry.end;
  }
  return entries;
}

/** Measures real fps with requestVideoFrameCallback during playback. */
function fpsMeter(video: HTMLVideoElement): () => number | null {
  let startMedia: number | null = null;
  let frames = 0;
  let measured: number | null = null;
  const anyVideo = video as HTMLVideoElement & { requestVideoFrameCallback?: (cb: (now: number, meta: { mediaTime: number }) => void) => number };
  if (typeof anyVideo.requestVideoFrameCallback !== 'function') return () => null;
  const tick = (_now: number, meta: { mediaTime: number }) => {
    if (measured !== null) return;
    if (startMedia === null) {
      startMedia = meta.mediaTime;
    } else {
      frames += 1;
      const elapsed = meta.mediaTime - startMedia;
      if (elapsed >= 2) measured = frames / elapsed;
    }
    if (measured === null) anyVideo.requestVideoFrameCallback!(tick);
  };
  anyVideo.requestVideoFrameCallback(tick);
  return () => measured;
}

export class BrowserSpeechCancelled extends Error {
  constructor() {
    super('Cancelled.');
    this.name = 'BrowserSpeechCancelled';
  }
}

export interface TranscribeOptions {
  file: File;
  lang: string;
  /** Keep recognition on this device (needs the language pack installed). */
  processLocally: boolean;
  onStage: (stage: string) => void;
  onProgress: (percent: number) => void;
  isCancelled: () => boolean;
}

/**
 * Play the video locally and recognize its speech with the browser engine.
 * Resolves with the transcript and video info; rejects with a friendly Error.
 */
export function transcribeFile(options: TranscribeOptions): Promise<BrowserTranscript> {
  const Ctor = ctor();
  if (!Ctor) return Promise.reject(new Error(detectSupport().reason || 'Browser speech is not available here.'));
  const { file, lang, onStage, onProgress, isCancelled } = options;

  return new Promise<BrowserTranscript>((resolve, reject) => {
    const video = document.createElement('video');
    video.muted = true;
    video.preload = 'auto';
    video.playsInline = true;
    const url = URL.createObjectURL(file);
    const pieces: FinalPiece[] = [];
    const meter = fpsMeter(video);
    let recognition: SpeechRecognitionLike | null = null;
    let finishing = false;
    let settled = false;
    let watchdog = 0;

    const cleanup = () => {
      window.clearInterval(watchdog);
      video.pause();
      video.removeAttribute('src');
      video.load();
      URL.revokeObjectURL(url);
    };
    const fail = (message: string) => {
      if (settled) return;
      settled = true;
      try { recognition?.abort(); } catch { /* already stopped */ }
      cleanup();
      reject(new Error(message));
    };
    const done = () => {
      if (settled) return;
      settled = true;
      try { recognition?.stop(); } catch { /* already stopped */ }
      const transcript = assembleTranscript(pieces);
      const fps = meter();
      const width = video.videoWidth || 1920;
      const height = video.videoHeight || 1080;
      cleanup();
      if (!transcript.length) {
        reject(new Error('No speech was found in this video. Try a speech model below instead.'));
        return;
      }
      resolve({
        transcript,
        width,
        height,
        fps: fps ? Math.min(240, Math.max(1, Math.round(fps * 100) / 100)) : 30,
      });
    };

    recognition = new Ctor();
    recognition.continuous = true;
    recognition.interimResults = false;
    recognition.lang = lang;
    if (options.processLocally) recognition.processLocally = true;
    recognition.onresult = (event) => {
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const result = event.results[i];
        if (result.isFinal && result.length > 0) {
          pieces.push({ text: result[0].transcript, at: video.currentTime, confidence: result[0].confidence });
        }
      }
    };
    recognition.onerror = (event) => {
      const code = event.error;
      if (code === 'no-speech' || code === 'aborted') return; // silence or our own cancel; the video keeps playing
      if (code === 'service-not-allowed') fail('On-device recognition is not ready. Install the language pack, or turn off "on this device" below.');
      else if (code === 'network') fail('The browser speech service needs internet. Turn on "on this device", check the connection, or use a speech model below.');
      else if (code === 'not-allowed') fail('The browser blocked speech recognition. Allow it in the site settings and try again.');
      else fail(`Browser speech stopped (${code}). Try again, or use a speech model below.`);
    };
    // Some engines end recognition after pauses even in continuous mode.
    recognition.onend = () => {
      if (settled || finishing) return;
      try { recognition?.start(audioTrack()); } catch { fail('Browser speech stopped. Try again, or use a speech model below.'); }
    };

    const streamOf = video as HTMLVideoElement & { captureStream?: () => MediaStream; mozCaptureStream?: () => MediaStream };
    const audioTrack = (): MediaStreamTrack => {
      const stream = typeof streamOf.captureStream === 'function' ? streamOf.captureStream() : streamOf.mozCaptureStream!();
      const track = stream.getAudioTracks()[0];
      if (!track) throw new Error('none');
      return track;
    };

    video.onerror = () => fail('This video could not be read. Choose a decodable video file.');
    video.onloadedmetadata = () => {
      onStage(`Playing the video for the browser recognizer (real time, ${Math.round(video.duration)} s)`);
      video.play().then(() => {
        try {
          recognition!.start(audioTrack());
        } catch {
          fail('This browser cannot recognize a video file directly. Update the browser, or use a speech model below.');
        }
      }).catch(() => fail('The video could not be played for recognition.'));
    };
    video.onended = () => {
      finishing = true;
      onProgress(99);
      onStage('Finishing the last phrase');
      // Give the recognizer a moment to deliver the final phrase, then wrap up.
      window.setTimeout(done, 1500);
    };
    video.src = url;

    watchdog = window.setInterval(() => {
      if (isCancelled()) {
        try { recognition?.abort(); } catch { /* already stopped */ }
        if (!settled) {
          settled = true;
          cleanup();
          reject(new BrowserSpeechCancelled());
        }
        return;
      }
      if (video.duration > 0) onProgress(Math.min(98, Math.round((video.currentTime / video.duration) * 100)));
    }, 250);
  });
}
