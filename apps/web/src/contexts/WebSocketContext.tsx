import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";
import type { ClientMessage, ServerMessage } from "@pair-cooking/types";

export type ConnectionStatus = "connected" | "reconnecting" | "failed";

type MessageHandler = (msg: ServerMessage) => void;

interface WebSocketContextValue {
  status: ConnectionStatus;
  sessionId: string | null;
  send: (msg: ClientMessage) => void;
  subscribe: (handler: MessageHandler) => () => void;
}

const WebSocketContext = createContext<WebSocketContextValue | null>(null);

const SESSION_KEY = "pair_cooking_session_id";
const MAX_RETRIES = 5;
const WS_URL = (import.meta.env.VITE_WS_URL as string | undefined) ?? "ws://localhost:8000/ws";

export function WebSocketProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = useState<ConnectionStatus>("reconnecting");
  const [sessionId, setSessionId] = useState<string | null>(
    localStorage.getItem(SESSION_KEY)
  );

  const wsRef = useRef<WebSocket | null>(null);
  const retryCount = useRef(0);
  const retryTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const isMounted = useRef(true);
  const handlers = useRef<Set<MessageHandler>>(new Set());

  const connect = useCallback(() => {
    if (!isMounted.current) return;
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const socket = new WebSocket(WS_URL);
    wsRef.current = socket;

    socket.onopen = () => {
      if (!isMounted.current) { socket.close(); return; }
      retryCount.current = 0;
      socket.send(
        JSON.stringify({ type: "init", session_id: localStorage.getItem(SESSION_KEY) })
      );
    };

    socket.onmessage = (event: MessageEvent) => {
      if (!isMounted.current) return;
      const msg = JSON.parse(event.data as string) as ServerMessage;

      if (msg.type === "session_ready") {
        localStorage.setItem(SESSION_KEY, msg.session_id);
        setSessionId(msg.session_id);
        setStatus("connected");
      }

      for (const handler of handlers.current) {
        handler(msg);
      }
    };

    socket.onclose = () => {
      if (!isMounted.current) return;
      if (retryCount.current >= MAX_RETRIES) {
        setStatus("failed");
        return;
      }
      setStatus("reconnecting");
      const delay = Math.min(1000 * 2 ** retryCount.current, 30_000);
      retryCount.current += 1;
      retryTimer.current = setTimeout(connect, delay);
    };

    socket.onerror = () => {
      socket.close();
    };
  }, []);

  useEffect(() => {
    isMounted.current = true;
    connect();
    return () => {
      isMounted.current = false;
      if (retryTimer.current) clearTimeout(retryTimer.current);
      wsRef.current?.close();
    };
  }, [connect]);

  const send = useCallback((msg: ClientMessage) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(msg));
    }
  }, []);

  const subscribe = useCallback((handler: MessageHandler) => {
    handlers.current.add(handler);
    return () => { handlers.current.delete(handler); };
  }, []);

  return (
    <WebSocketContext.Provider value={{ status, sessionId, send, subscribe }}>
      {children}
    </WebSocketContext.Provider>
  );
}

export function useWebSocket(): WebSocketContextValue {
  const ctx = useContext(WebSocketContext);
  if (!ctx) throw new Error("useWebSocket must be used within WebSocketProvider");
  return ctx;
}
