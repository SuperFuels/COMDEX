"use client";

import { useRef, useState, useCallback } from "react";

/**
 * useCanvasRecorder
 * 
 * Hook to record a <Canvas> (or any DOM video element) as .mp4 using MediaRecorder.
 * Returns start/stop controls and recording state with download link support.
 */
export function useCanvasRecorder() {
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const recordedChunksRef = useRef<Blob[]>([]);
  const [isRecording, setIsRecording] = useState(false);
  const [downloadUrl, setDownloadUrl] = useState<string | null>(null);

  /**
   * Start recording a given HTMLCanvasElement or video element.
   */
  const startRecording = useCallback((canvas: HTMLCanvasElement) => {
    if (!canvas) {
      console.warn("[useCanvasRecorder] No canvas element provided!");
      return;
    }

    const stream = canvas.captureStream(30); // 🎥 30 FPS stream capture
    const recorder = new MediaRecorder(stream, {
      mimeType: "video/webm; codecs=vp9", // MP4-like WebM fallback (convertible)
      videoBitsPerSecond: 5_000_000,
    });

    recordedChunksRef.current = [];
    setDownloadUrl(null);

    recorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        recordedChunksRef.current.push(event.data);
      }
    };

    recorder.onstop = () => {
      const blob = new Blob(recordedChunksRef.current, { type: "video/webm" });
      const url = URL.createObjectURL(blob);
      setDownloadUrl(url);
    };

    recorder.start();
    mediaRecorderRef.current = recorder;
    setIsRecording(true);

    console.log("🎬 Recording started (MediaRecorder)");
  }, []);

  /**
   * Stop recording and finalize the video.
   */
  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      console.log("🛑 Recording stopped");
    }
  }, [isRecording]);

  /**
   * Download the recorded video as .mp4/webm
   */
  const downloadRecording = useCallback((filename: string = "holographic_replay.webm") => {
    if (downloadUrl) {
      const a = document.createElement("a");
      a.href = downloadUrl;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      console.log(`💾 Downloaded recording as ${filename}`);
    }
  }, [downloadUrl]);

  return {
    isRecording,
    downloadUrl,
    startRecording,
    stopRecording,
    downloadRecording,
  };
}