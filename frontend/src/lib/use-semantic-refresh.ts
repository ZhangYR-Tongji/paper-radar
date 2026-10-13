"use client";

import { useEffect, useRef, useState } from "react";

import { apiGet } from "@/lib/api";
import type { SemanticSettingsResponse } from "@/lib/types";

type RefreshCallback = () => void | Promise<void>;

/** Refresh the current list after a semantic task observed on this page finishes. */
export function useSemanticRefresh(onComplete: RefreshCallback) {
  const callbackRef = useRef(onComplete);
  const [status, setStatus] = useState<SemanticSettingsResponse | null>(null);

  useEffect(() => {
    callbackRef.current = onComplete;
  }, [onComplete]);

  useEffect(() => {
    let active = true;
    let sawRunningTask = false;
    let timer: ReturnType<typeof setTimeout> | undefined;

    const poll = async () => {
      let next: SemanticSettingsResponse;
      try {
        next = await apiGet<SemanticSettingsResponse>("/settings/semantic");
      } catch {
        // An older/offline backend must not prevent ordinary paper browsing.
        if (active) setStatus(null);
        return;
      }
      if (!active) return;
      setStatus(next);
      if (next.status === "preparing" || next.status === "indexing") {
        sawRunningTask = true;
        timer = setTimeout(poll, 2500);
      } else if (next.status === "completed" && sawRunningTask) {
        sawRunningTask = false;
        try {
          await callbackRef.current();
        } catch {
          // List loaders own their error messages; avoid an unhandled rejection.
        }
      }
    };

    void poll();
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, []);

  return status;
}
