"use client";

import { useEffect, useRef, useState } from "react";

type LiveMessage = {
  type: string;
  [key: string]: any;
};

export function useLiveSocket(onUpdate?: (msg: LiveMessage) => void) {
  const [connected, setConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<LiveMessage | null>(null);
  const [updateCount, setUpdateCount] = useState(0);
  const socketRef = useRef<WebSocket | null>(null);
  const onUpdateRef = useRef(onUpdate);

  // Keep the callback ref up-to-date without reconnecting
  useEffect(() => {
    onUpdateRef.current = onUpdate;
  }, [onUpdate]);

  useEffect(() => {
    if (typeof window === "undefined") return;

    const API_BASE =
      process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";
    const wsUrl = API_BASE.replace(/^http/, "ws") + "/ws/live";

    let reconnectTimer: any;
    let shouldReconnect = true;

    function connect() {
      const ws = new WebSocket(wsUrl);
      socketRef.current = ws;

      ws.onopen = () => {
        console.log("[ws] connected");
        setConnected(true);
      };

      ws.onmessage = (event) => {
        try {
          const msg: LiveMessage = JSON.parse(event.data);
          console.log("[ws] message:", msg);
          setLastMessage(msg);

          if (msg.type === "live_update") {
            setUpdateCount((c) => c + 1);
            onUpdateRef.current?.(msg);
          }
        } catch (e) {
          console.warn("[ws] parse error:", e);
        }
      };

      ws.onerror = (err) => {
        console.warn("[ws] error:", err);
      };

      ws.onclose = () => {
        console.log("[ws] closed");
        setConnected(false);
        if (shouldReconnect) {
          reconnectTimer = setTimeout(connect, 3000);
        }
      };
    }

    connect();

    return () => {
      shouldReconnect = false;
      clearTimeout(reconnectTimer);
      socketRef.current?.close();
    };
  }, []);

  return { connected, lastMessage, updateCount };
}