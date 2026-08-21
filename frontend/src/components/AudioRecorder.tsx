"use client";

import { useState, useRef, useEffect, useCallback } from "react";

interface AudioRecorderProps {
  onRecordingComplete: (blob: Blob) => void;
  onTextSubmit: (text: string) => void;
  onLiveTranscript?: (text: string) => void;
  disabled?: boolean;
}

export default function AudioRecorder({ onRecordingComplete, onTextSubmit, onLiveTranscript, disabled = false }: AudioRecorderProps) {
  const [isRecording, setIsRecording] = useState(false);
  const [duration, setDuration] = useState(0);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const recognitionRef = useRef<any>(null);

  useEffect(() => {
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
      if (recognitionRef.current) recognitionRef.current.stop();
    };
  }, []);

  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
      const mimeType = MediaRecorder.isTypeSupported("audio/webm;codecs=opus") ? "audio/webm;codecs=opus" : "audio/webm";
      const rec = new MediaRecorder(stream, { mimeType });
      chunksRef.current = [];
      mediaRecorderRef.current = rec;
      rec.ondataavailable = (e) => { if (e.data.size > 0) chunksRef.current.push(e.data); };
      rec.onstop = () => { onRecordingComplete(new Blob(chunksRef.current, { type: mimeType })); stream.getTracks().forEach((t) => t.stop()); };
      rec.start(250);
      setIsRecording(true);
      setDuration(0);
      timerRef.current = setInterval(() => setDuration((d) => d + 1), 1000);
      // On-device: Web Speech API (Layer 7)
      const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
      if (SR) {
        const recognition = new SR();
        recognition.continuous = true; recognition.interimResults = true; recognition.lang = "en-IN";
        recognition.onresult = (event: any) => { let t = ""; for (let i = 0; i < event.results.length; i++) t += event.results[i][0].transcript; onLiveTranscript?.(t); };
        recognition.onerror = () => {};
        recognition.start();
        recognitionRef.current = recognition;
      }
    } catch { /* mic denied — user can use text mode */ }
  }, [onRecordingComplete, onLiveTranscript]);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      if (timerRef.current) clearInterval(timerRef.current);
      if (recognitionRef.current) { recognitionRef.current.stop(); recognitionRef.current = null; }
    }
  }, [isRecording]);

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => { const f = e.target.files?.[0]; if (f) onRecordingComplete(f); };

  const fmt = (s: number) => `${Math.floor(s / 60)}:${(s % 60).toString().padStart(2, "0")}`;

  return (
    <div className="flex flex-col items-center gap-5">
      {/* Waveform */}
      {isRecording && (
        <div className="flex items-end justify-center gap-[3px] h-8">
          {[...Array(7)].map((_, i) => (
            <div key={i} className="w-[3px] rounded-full bg-gradient-to-t from-indigo-500 to-purple-400 wave-bar" style={{ height: "24px" }} />
          ))}
        </div>
      )}

      {/* Record button */}
      <div className="relative flex items-center justify-center">
        {isRecording && (
          <>
            <div className="absolute w-28 h-28 rounded-full border border-red-300/30 pulse-ring" />
            <div className="absolute w-24 h-24 rounded-full border border-red-300/20 pulse-ring" style={{ animationDelay: "0.5s" }} />
          </>
        )}
        <button
          onClick={isRecording ? stopRecording : startRecording}
          disabled={disabled}
          className={`relative z-10 w-20 h-20 rounded-full flex items-center justify-center transition-all duration-300 focus-ring cursor-pointer ${
            isRecording
              ? "bg-red-500 glow-recording"
              : "bg-gradient-to-br from-indigo-500 via-purple-500 to-indigo-600 shadow-xl shadow-indigo-200 hover:shadow-indigo-300 hover:scale-105 active:scale-95"
          } ${disabled ? "opacity-50 cursor-not-allowed" : ""}`}
        >
          {isRecording ? (
            <div className="w-5 h-5 rounded-sm bg-white" />
          ) : (
            <svg width="28" height="28" viewBox="0 0 24 24" fill="white">
              <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z" />
              <path d="M19 10v2a7 7 0 0 1-14 0v-2" stroke="white" fill="none" strokeWidth="2" strokeLinecap="round" />
              <line x1="12" y1="19" x2="12" y2="23" stroke="white" strokeWidth="2" strokeLinecap="round" />
              <line x1="8" y1="23" x2="16" y2="23" stroke="white" strokeWidth="2" strokeLinecap="round" />
            </svg>
          )}
        </button>
      </div>

      <div className="text-center">
        <p className={`text-sm font-mono ${isRecording ? "text-red-500 font-semibold" : "text-[var(--text-secondary)]"}`}>
          {isRecording ? fmt(duration) : "Tap to record"}
        </p>
        {!isRecording && (
          <p className="text-[11px] text-[var(--text-muted)] mt-1">Hindi · English · Code-mixed speech</p>
        )}
      </div>

      {/* Upload fallback */}
      {!isRecording && (
        <label className="text-xs text-[var(--accent)] hover:underline cursor-pointer flex items-center gap-1">
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
          Or upload audio file
          <input type="file" accept="audio/*" onChange={handleFileUpload} disabled={disabled} className="hidden" />
        </label>
      )}
    </div>
  );
}
