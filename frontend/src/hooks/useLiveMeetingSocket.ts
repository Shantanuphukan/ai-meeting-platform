import { useEffect, useMemo, useRef, useState } from "react";

type TranscriptSegment = {
  id?: string | number;
  speaker_label?: string;
  text?: string;
  confidence?: number;
  language?: string;
  _partial?: boolean;
};

function normalizeText(text?: string): string {
  return String(text || "").replace(/\s+/g, " ").trim();
}

function normalizeCompare(text?: string): string {
  return normalizeText(text).toLowerCase();
}

function extractIncrementalSuffix(previousText?: string, newText?: string, maxWindow = 40): string {
  const prevRaw = normalizeText(previousText);
  const nextRaw = normalizeText(newText);

  if (!nextRaw) return "";
  if (!prevRaw) return nextRaw;

  const prevCmp = prevRaw.toLowerCase();
  const nextCmp = nextRaw.toLowerCase();

  if (prevCmp === nextCmp) return "";

  const prevWordsRaw = prevRaw.split(" ");
  const nextWordsRaw = nextRaw.split(" ");

  const prevWords = prevWordsRaw.map((w) => w.toLowerCase());
  const nextWords = nextWordsRaw.map((w) => w.toLowerCase());

  const maxOverlap = Math.min(prevWords.length, nextWords.length, maxWindow);

  for (let size = maxOverlap; size > 0; size -= 1) {
    const prevTail = prevWords.slice(prevWords.length - size).join(" ");
    const nextHead = nextWords.slice(0, size).join(" ");
    if (prevTail === nextHead) {
      return normalizeText(nextWordsRaw.slice(size).join(" "));
    }
  }

  if (nextCmp.startsWith(prevCmp)) {
    return normalizeText(nextWordsRaw.slice(prevWordsRaw.length).join(" "));
  }

  if (prevCmp.includes(nextCmp)) {
    return "";
  }

  return nextRaw;
}

function shouldSkipAsDuplicate(existing: TranscriptSegment[], incomingText: string): boolean {
  const cleanIncoming = normalizeCompare(incomingText);
  if (!cleanIncoming) return true;

  const lastFinal = [...existing].reverse().find((seg) => !seg._partial);
  if (!lastFinal) return false;

  const cleanLast = normalizeCompare(lastFinal.text);

  if (!cleanLast) return false;
  if (cleanLast === cleanIncoming) return true;
  if (cleanLast.includes(cleanIncoming)) return true;

  return false;
}

function buildSafeFinalTranscript(
  prev: TranscriptSegment[],
  incoming: TranscriptSegment
): TranscriptSegment[] {
  const incomingText = normalizeText(incoming.text);
  if (!incomingText) return prev;

  const finalsOnly = prev.filter((seg) => !seg._partial);

  if (shouldSkipAsDuplicate(finalsOnly, incomingText)) {
    return finalsOnly;
  }

  const lastFinal = finalsOnly[finalsOnly.length - 1];
  const incomingSpeaker = normalizeText(incoming.speaker_label) || "Live Speaker";

  if (!lastFinal) {
    return [
      ...finalsOnly,
      {
        ...incoming,
        speaker_label: incomingSpeaker,
        text: incomingText,
        _partial: false,
      },
    ];
  }

  const lastSpeaker = normalizeText(lastFinal.speaker_label) || "Live Speaker";

  if (lastSpeaker === incomingSpeaker) {
    const suffix = extractIncrementalSuffix(lastFinal.text, incomingText);

    if (!suffix) {
      return finalsOnly;
    }

    const updatedLast: TranscriptSegment = {
      ...lastFinal,
      text: normalizeText(`${lastFinal.text || ""} ${suffix}`),
      _partial: false,
    };

    return [...finalsOnly.slice(0, -1), updatedLast];
  }

  return [
    ...finalsOnly,
    {
      ...incoming,
      speaker_label: incomingSpeaker,
      text: incomingText,
      _partial: false,
    },
  ];
}

function buildSafePartialSegment(
  currentPartial: TranscriptSegment | null,
  currentFinals: TranscriptSegment[],
  incoming: TranscriptSegment
): TranscriptSegment | null {
  const incomingText = normalizeText(incoming.text);
  if (!incomingText) return null;

  const lastFinal = [...currentFinals].reverse().find((seg) => !seg._partial);
  const suffixFromFinal = lastFinal
    ? extractIncrementalSuffix(lastFinal.text, incomingText)
    : incomingText;

  const cleanedText = normalizeText(suffixFromFinal || incomingText);
  if (!cleanedText) return null;

  if (currentPartial) {
    const oldText = normalizeCompare(currentPartial.text);
    const newText = normalizeCompare(cleanedText);

    if (oldText === newText) {
      return currentPartial;
    }

    if (newText.includes(oldText) || oldText.includes(newText)) {
      return {
        ...incoming,
        text: cleanedText,
        _partial: true,
      };
    }
  }

  return {
    ...incoming,
    text: cleanedText,
    _partial: true,
  };
}

export function useLiveMeetingSocket(meetingId: string) {
  const socketRef = useRef<WebSocket | null>(null);
  const transientErrorTimerRef = useRef<number | null>(null);
  const readyRef = useRef(false);
  const endingRef = useRef(false);
  const completedRef = useRef(false);
  const finalTranscriptRef = useRef<TranscriptSegment[]>([]);

  const [finalTranscript, setFinalTranscript] = useState<TranscriptSegment[]>([]);
  const [livePartialSegment, setLivePartialSegment] = useState<TranscriptSegment | null>(null);
  const [liveMinutes, setLiveMinutes] = useState<any>(null);

  const [ready, setReady] = useState(false);
  const [sessionCompleted, setSessionCompleted] = useState(false);
  const [sessionError, setSessionError] = useState<string | null>(null);

  useEffect(() => {
    readyRef.current = ready;
  }, [ready]);

  useEffect(() => {
    completedRef.current = sessionCompleted;
  }, [sessionCompleted]);

  useEffect(() => {
    finalTranscriptRef.current = finalTranscript;
  }, [finalTranscript]);

  useEffect(() => {
    if (!meetingId) return;

    setFinalTranscript([]);
    setLivePartialSegment(null);
    setLiveMinutes(null);
    setReady(false);
    setSessionCompleted(false);
    setSessionError(null);

    finalTranscriptRef.current = [];
    readyRef.current = false;
    endingRef.current = false;
    completedRef.current = false;

    const protocol = window.location.protocol === "https:" ? "wss" : "ws";

    const host =
      (import.meta as any)?.env?.VITE_WS_HOST ||
      window.location.hostname;

    const port =
      (import.meta as any)?.env?.VITE_WS_PORT ||
      "8000";

    const ws = new WebSocket(`${protocol}://${host}:${port}/ws/live/${meetingId}`);

    ws.binaryType = "arraybuffer";
    socketRef.current = ws;

    ws.onopen = () => {
      setSessionError(null);

      ws.send(
        JSON.stringify({
          type: "session.init",
          meeting_id: meetingId,
        })
      );
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.type === "session.ready") {
          if (transientErrorTimerRef.current) {
            window.clearTimeout(transientErrorTimerRef.current);
            transientErrorTimerRef.current = null;
          }

          setReady(true);
          readyRef.current = true;
          setSessionError(null);
        }

        if (data.type === "session.error") {
          if (transientErrorTimerRef.current) {
            window.clearTimeout(transientErrorTimerRef.current);
            transientErrorTimerRef.current = null;
          }

          console.error("Session error:", data.message);
          setReady(false);
          readyRef.current = false;
          setSessionError(data.message || "Session failed");
        }

        if (data.type === "transcript.partial") {
          const text = normalizeText(data?.segment?.text);
          if (!text) return;

          setLivePartialSegment((prevPartial) =>
            buildSafePartialSegment(prevPartial, finalTranscriptRef.current, {
              ...data.segment,
              text,
              _partial: true,
            })
          );
        }

        if (data.type === "transcript.final") {
          const text = normalizeText(data?.segment?.text);
          if (!text) return;

          setFinalTranscript((prev) => {
            const next = buildSafeFinalTranscript(prev, {
              ...data.segment,
              text,
              _partial: false,
            });
            finalTranscriptRef.current = next;
            return next;
          });

          setLivePartialSegment(null);
        }

        if (data.type === "minutes.live") {
          setLiveMinutes(data.minutes);
        }

        if (data.type === "session.completed") {
          if (transientErrorTimerRef.current) {
            window.clearTimeout(transientErrorTimerRef.current);
            transientErrorTimerRef.current = null;
          }

          setLiveMinutes(data.final);
          setSessionCompleted(true);
          completedRef.current = true;
          setReady(false);
          readyRef.current = false;
          setLivePartialSegment(null);
          setSessionError(null);
        }
      } catch (err) {
        console.error("WebSocket message parse error:", err);
      }
    };

    ws.onclose = () => {
      setReady(false);
      readyRef.current = false;

      if (endingRef.current || completedRef.current) {
        return;
      }

      if (transientErrorTimerRef.current) {
        window.clearTimeout(transientErrorTimerRef.current);
      }

      transientErrorTimerRef.current = window.setTimeout(() => {
        setSessionError((prev) => prev || "WebSocket connection closed");
      }, 300);
    };

    ws.onerror = () => {
      setReady(false);
      readyRef.current = false;

      if (endingRef.current || completedRef.current) {
        return;
      }

      if (transientErrorTimerRef.current) {
        window.clearTimeout(transientErrorTimerRef.current);
      }

      transientErrorTimerRef.current = window.setTimeout(() => {
        setSessionError((prev) => prev || "WebSocket connection error");
      }, 300);
    };

    return () => {
      if (transientErrorTimerRef.current) {
        window.clearTimeout(transientErrorTimerRef.current);
        transientErrorTimerRef.current = null;
      }

      try {
        ws.close();
      } catch (e) {}

      socketRef.current = null;
    };
  }, [meetingId]);

  const transcript = useMemo(() => {
    if (livePartialSegment?.text?.trim()) {
      return [...finalTranscript, livePartialSegment];
    }
    return finalTranscript;
  }, [finalTranscript, livePartialSegment]);

  const sendAudioChunk = (chunk: ArrayBuffer) => {
    const ws = socketRef.current;

    if (!ws || ws.readyState !== WebSocket.OPEN) return;

    ws.send(chunk);
  };

  const endSession = () => {
    const ws = socketRef.current;

    if (!ws || ws.readyState !== WebSocket.OPEN) return;

    endingRef.current = true;
    setSessionError(null);

    ws.send(
      JSON.stringify({
        type: "session.end",
        meeting_id: meetingId,
      })
    );
  };

  return {
    ready,
    transcript,
    finalTranscript,
    livePartialSegment,
    liveMinutes,
    sendAudioChunk,
    endSession,
    sessionCompleted,
    sessionError,
  };
}