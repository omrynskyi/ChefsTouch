import { useEffect, useRef, useState } from "react";
import type { CameraData } from "@pair-cooking/types";
// T-052: import useWebSocket here to send captured frames
// import { useWebSocket } from "../../contexts/WebSocketContext";

type CameraState = "requesting" | "active" | "denied" | "error";

interface Props {
  data: CameraData;
  focused?: boolean;
  onDismiss?: () => void;
}

export function Camera({ data, focused, onDismiss }: Props) {
  const [camState, setCamState] = useState<CameraState>("requesting");
  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);

  useEffect(() => {
    let cancelled = false;

    navigator.mediaDevices
      .getUserMedia({ video: { facingMode: "environment" } })
      .then((stream) => {
        if (cancelled) {
          stream.getTracks().forEach((t) => t.stop());
          return;
        }
        streamRef.current = stream;
        if (videoRef.current) {
          videoRef.current.srcObject = stream;
        }
        setCamState("active");
      })
      .catch((err: Error) => {
        if (cancelled) return;
        if (err.name === "NotAllowedError" || err.name === "PermissionDeniedError") {
          setCamState("denied");
        } else {
          setCamState("error");
        }
      });

    return () => {
      cancelled = true;
      streamRef.current?.getTracks().forEach((t) => t.stop());
    };
  }, []);

  // T-052: capture frame from video, send via WebSocket, then dismiss
  const handleCapture = () => {
    onDismiss?.();
  };

  return (
    <div
      className={`card camera-card${focused ? " elevated" : ""}`}
      style={{ display: "flex", flexDirection: "column", gap: "var(--space-sm)", position: "relative" }}
    >
      {onDismiss && (
        <button onClick={onDismiss} className="camera-dismiss" aria-label="Dismiss camera">
          ✕
        </button>
      )}

      {camState === "requesting" && (
        <div className="camera-frame camera-requesting">
          <span>Opening camera…</span>
        </div>
      )}

      {camState === "active" && (
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          className="camera-frame"
          aria-label="Camera feed"
        />
      )}

      {camState === "denied" && (
        <div className="camera-frame camera-error">
          <span>Camera access denied. Check browser permissions.</span>
          {onDismiss && (
            <button onClick={onDismiss} className="btn-primary">
              Dismiss
            </button>
          )}
        </div>
      )}

      {camState === "error" && (
        <div className="camera-frame camera-error">
          <span>Camera unavailable. Please try again.</span>
          {onDismiss && (
            <button onClick={onDismiss} className="btn-primary">
              Dismiss
            </button>
          )}
        </div>
      )}

      <p className="text-secondary size-sm">{data.prompt}</p>

      {camState === "active" && (
        <button className="btn-primary" onClick={handleCapture}>
          Capture
        </button>
      )}
    </div>
  );
}
