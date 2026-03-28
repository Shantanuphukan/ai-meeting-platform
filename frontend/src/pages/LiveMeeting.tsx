import { useEffect, useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useLiveMeetingSocket } from "../hooks/useLiveMeetingSocket";
import { useMicrophoneStream } from "../hooks/useMicrophoneStream";

type LiveTranscriptSegment = {
  speaker_label?: string;
  text?: string;
  _partial?: boolean;
};

type GroupedLiveTranscriptSegment = {
  speaker_label: string;
  text: string;
  _partial?: boolean;
};

function groupTranscriptSegments(
  segments: LiveTranscriptSegment[]
): GroupedLiveTranscriptSegment[] {
  const grouped: GroupedLiveTranscriptSegment[] = [];

  for (const seg of segments) {
    const speaker = (seg.speaker_label || "Live Speaker").trim();
    const text = (seg.text || "").trim();

    if (!text) continue;

    const last = grouped[grouped.length - 1];

    const canMerge =
      !!last &&
      last.speaker_label === speaker &&
      !last._partial &&
      !seg._partial;

    if (canMerge) {
      const needsSpace =
        !last.text.endsWith(" ") &&
        !text.startsWith(",") &&
        !text.startsWith(".") &&
        !text.startsWith("?") &&
        !text.startsWith("!");

      last.text += (needsSpace ? " " : "") + text;
    } else {
      grouped.push({
        speaker_label: speaker,
        text,
        _partial: seg._partial,
      });
    }
  }

  return grouped;
}

function getLivePartialSegment(
  segments: LiveTranscriptSegment[]
): LiveTranscriptSegment | null {
  for (let i = segments.length - 1; i >= 0; i -= 1) {
    const seg = segments[i];
    const text = (seg?.text || "").trim();

    if (seg?._partial && text) {
      return {
        speaker_label: (seg.speaker_label || "Live Speaker").trim(),
        text,
        _partial: true,
      };
    }
  }

  return null;
}

function formatElapsed(seconds: number) {
  const hrs = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;

  const hh = String(hrs).padStart(2, "0");
  const mm = String(mins).padStart(2, "0");
  const ss = String(secs).padStart(2, "0");

  return `${hh}:${mm}:${ss}`;
}

export default function LiveMeeting() {
  const { meetingId = "" } = useParams();
  const navigate = useNavigate();
  const [ending, setEnding] = useState(false);
  const [elapsed, setElapsed] = useState(0);

  const {
    ready,
    transcript,
    liveMinutes,
    sendAudioChunk,
    endSession,
    sessionCompleted,
    sessionError,
  } = useLiveMeetingSocket(meetingId);

  const { start, stop, isRecording } = useMicrophoneStream(sendAudioChunk);

  useEffect(() => {
    if (ready && !isRecording && !ending) {
      start();
    }
  }, [ready, isRecording, start, ending]);

  useEffect(() => {
    if (!ready || ending) return;

    const timer = window.setInterval(() => {
      setElapsed((prev) => prev + 1);
    }, 1000);

    return () => window.clearInterval(timer);
  }, [ready, ending]);

  useEffect(() => {
    if (sessionCompleted) {
      navigate(`/review/${meetingId}`);
    }
  }, [sessionCompleted, navigate, meetingId]);

  useEffect(() => {
    const handleBeforeUnload = (event: BeforeUnloadEvent) => {
      if (!ending && ready) {
        event.preventDefault();
        event.returnValue = "";
      }
    };

    window.addEventListener("beforeunload", handleBeforeUnload);

    return () => {
      window.removeEventListener("beforeunload", handleBeforeUnload);
    };
  }, [ending, ready]);

  useEffect(() => {
    const handleDocumentClick = (event: MouseEvent) => {
      if (!ready || ending) return;

      const target = event.target as HTMLElement | null;
      if (!target) return;

      const anchor = target.closest("a");
      if (!anchor) return;

      const confirmed = window.confirm(
        "A live meeting is in progress. Leaving this page may interrupt the meeting. Do you want to continue?"
      );

      if (!confirmed) {
        event.preventDefault();
        event.stopPropagation();
      }
    };

    document.addEventListener("click", handleDocumentClick, true);

    return () => {
      document.removeEventListener("click", handleDocumentClick, true);
    };
  }, [ready, ending]);

  const finalTranscriptSegments = useMemo(
    () => transcript.filter((seg) => !seg._partial && (seg.text || "").trim()),
    [transcript]
  );

  const livePartialSegment = useMemo(
    () => getLivePartialSegment(transcript),
    [transcript]
  );

  const groupedTranscript = useMemo(
    () => groupTranscriptSegments(finalTranscriptSegments),
    [finalTranscriptSegments]
  );

  const singleSpeakerFinalText = useMemo(
    () => groupedTranscript.map((seg) => seg.text).join(" "),
    [groupedTranscript]
  );

  const uniqueSpeakers = useMemo(() => {
    const speakers = new Set<string>();

    groupedTranscript.forEach((seg) => {
      const speaker = (seg.speaker_label || "").trim();
      if (speaker) speakers.add(speaker);
    });

    if (livePartialSegment?.speaker_label?.trim()) {
      speakers.add(livePartialSegment.speaker_label.trim());
    }

    return Array.from(speakers);
  }, [groupedTranscript, livePartialSegment]);

  const isSingleSpeaker = uniqueSpeakers.length <= 1;

  const handleEnd = () => {
    if (ending) return;

    setEnding(true);
    stop();
    endSession();
  };

  const statusLabel = sessionError
    ? "Session Error"
    : sessionCompleted
    ? "Completed"
    : ready
    ? "Live"
    : "Connecting";

  const statusBg = sessionError
    ? "#fef2f2"
    : sessionCompleted
    ? "#ecfdf5"
    : ready
    ? "#eff6ff"
    : "#f8fafc";

  const statusColor = sessionError
    ? "#b91c1c"
    : sessionCompleted
    ? "#166534"
    : ready
    ? "#1d4ed8"
    : "#475569";

  const hasTranscriptContent =
    groupedTranscript.length > 0 || !!livePartialSegment?.text?.trim();

  return (
    <div
      style={{
        minHeight: "100vh",
        background:
          "linear-gradient(180deg, #f8fbff 0%, #f5f7fb 45%, #eef3f8 100%)",
        padding: "24px",
        color: "#0f172a",
      }}
    >
      <div
        style={{
          maxWidth: "1400px",
          margin: "0 auto",
        }}
      >
        <div
          style={{
            background: "rgba(255,255,255,0.88)",
            backdropFilter: "blur(10px)",
            border: "1px solid #e2e8f0",
            borderRadius: "24px",
            boxShadow: "0 18px 45px rgba(15, 23, 42, 0.08)",
            padding: "24px",
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "flex-start",
              gap: "16px",
              flexWrap: "wrap",
              marginBottom: "20px",
            }}
          >
            <div>
              <div
                style={{
                  fontSize: "13px",
                  fontWeight: 700,
                  letterSpacing: "0.14em",
                  textTransform: "uppercase",
                  color: "#64748b",
                  marginBottom: "8px",
                }}
              >
                AI Meeting Workspace
              </div>

              <h1
                style={{
                  margin: 0,
                  fontSize: "clamp(28px, 4vw, 44px)",
                  lineHeight: 1.05,
                  fontWeight: 800,
                  color: "#0f172a",
                }}
              >
                Live Meeting
              </h1>

              <div
                style={{
                  marginTop: "12px",
                  display: "flex",
                  gap: "10px",
                  flexWrap: "wrap",
                  alignItems: "center",
                }}
              >
                <span
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "8px",
                    padding: "8px 12px",
                    borderRadius: "999px",
                    background: statusBg,
                    color: statusColor,
                    fontWeight: 700,
                    border: "1px solid #dbeafe",
                    fontSize: "14px",
                  }}
                >
                  <span
                    style={{
                      width: "8px",
                      height: "8px",
                      borderRadius: "50%",
                      background: statusColor,
                      display: "inline-block",
                    }}
                  />
                  {statusLabel}
                </span>

                <span
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    padding: "8px 12px",
                    borderRadius: "999px",
                    background: "#f8fafc",
                    color: "#334155",
                    fontWeight: 700,
                    border: "1px solid #e2e8f0",
                    fontSize: "14px",
                  }}
                >
                  Duration: {formatElapsed(elapsed)}
                </span>

                <span
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    padding: "8px 12px",
                    borderRadius: "999px",
                    background: "#f8fafc",
                    color: "#334155",
                    fontWeight: 700,
                    border: "1px solid #e2e8f0",
                    fontSize: "14px",
                  }}
                >
                  Meeting ID: {meetingId}
                </span>
              </div>
            </div>

            <button
              onClick={handleEnd}
              disabled={ending || sessionCompleted}
              style={{
                border: "none",
                borderRadius: "14px",
                padding: "14px 18px",
                fontWeight: 800,
                fontSize: "15px",
                cursor: ending || sessionCompleted ? "not-allowed" : "pointer",
                background:
                  ending || sessionCompleted
                    ? "#cbd5e1"
                    : "linear-gradient(135deg, #dc2626 0%, #b91c1c 100%)",
                color: "#fff",
                boxShadow:
                  ending || sessionCompleted
                    ? "none"
                    : "0 12px 24px rgba(185, 28, 28, 0.22)",
                minWidth: "160px",
              }}
            >
              {ending ? "Ending..." : sessionCompleted ? "Completed" : "End Meeting"}
            </button>
          </div>

          {ready && !ending && (
            <div
              style={{
                marginBottom: "18px",
                padding: "14px 16px",
                borderRadius: "16px",
                background: "#fff7ed",
                border: "1px solid #fdba74",
                color: "#9a3412",
                fontWeight: 700,
              }}
            >
              Do not leave or refresh this page while the meeting is live.
            </div>
          )}

          {ending && !sessionCompleted && (
            <div
              style={{
                marginBottom: "18px",
                padding: "14px 16px",
                borderRadius: "16px",
                background: "#fff7ed",
                border: "1px solid #fdba74",
                color: "#92400e",
                fontWeight: 700,
              }}
            >
              Finalizing meeting... please wait.
            </div>
          )}

          {sessionError && (
            <div
              style={{
                marginBottom: "18px",
                padding: "14px 16px",
                borderRadius: "16px",
                background: "#fef2f2",
                border: "1px solid #fecaca",
                color: "#b91c1c",
                fontWeight: 700,
              }}
            >
              {sessionError}
            </div>
          )}

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "minmax(0, 1.4fr) minmax(320px, 0.9fr)",
              gap: "22px",
            }}
          >
            <div
              style={{
                background: "#ffffff",
                border: "1px solid #e2e8f0",
                borderRadius: "22px",
                padding: "22px",
                boxShadow: "0 10px 28px rgba(15, 23, 42, 0.05)",
                minHeight: "540px",
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  gap: "12px",
                  marginBottom: "18px",
                  flexWrap: "wrap",
                }}
              >
                <div>
                  <h2
                    style={{
                      margin: 0,
                      fontSize: "28px",
                      fontWeight: 800,
                      color: "#0f172a",
                    }}
                  >
                    Live Transcript
                  </h2>
                  <p
                    style={{
                      margin: "6px 0 0 0",
                      color: "#64748b",
                      fontSize: "14px",
                    }}
                  >
                    Real-time conversation capture for the current meeting.
                  </p>
                </div>

                <div
                  style={{
                    padding: "8px 12px",
                    borderRadius: "999px",
                    background: "#eef2ff",
                    color: "#4338ca",
                    fontWeight: 700,
                    fontSize: "13px",
                    border: "1px solid #c7d2fe",
                  }}
                >
                  {isSingleSpeaker ? "Single Speaker View" : "Multi Speaker View"}
                </div>
              </div>

              {!hasTranscriptContent ? (
                <div
                  style={{
                    minHeight: "420px",
                    display: "grid",
                    placeItems: "center",
                    border: "1px dashed #cbd5e1",
                    borderRadius: "18px",
                    background: "#f8fafc",
                    textAlign: "center",
                    padding: "24px",
                  }}
                >
                  <div>
                    <div
                      style={{
                        fontSize: "18px",
                        fontWeight: 700,
                        color: "#334155",
                        marginBottom: "6px",
                      }}
                    >
                      No transcript yet
                    </div>
                    <div style={{ color: "#64748b" }}>
                      Start speaking and the live transcript will appear here.
                    </div>
                  </div>
                </div>
              ) : isSingleSpeaker ? (
                <div
                  style={{
                    border: "1px solid #e2e8f0",
                    borderRadius: "18px",
                    background: "#fcfdff",
                    padding: "20px",
                    minHeight: "420px",
                    display: "grid",
                    gap: "16px",
                    alignContent: "start",
                  }}
                >
                  <p
                    style={{
                      margin: 0,
                      lineHeight: 1.95,
                      fontSize: "18px",
                      color: "#0f172a",
                      whiteSpace: "pre-wrap",
                    }}
                  >
                    {singleSpeakerFinalText}
                  </p>

                  {livePartialSegment?.text && (
                    <div
                      style={{
                        borderTop: singleSpeakerFinalText ? "1px dashed #cbd5e1" : "none",
                        paddingTop: singleSpeakerFinalText ? "14px" : 0,
                      }}
                    >
                      <div
                        style={{
                          display: "inline-flex",
                          alignItems: "center",
                          gap: "8px",
                          padding: "7px 12px",
                          borderRadius: "999px",
                          background: "#eff6ff",
                          color: "#1d4ed8",
                          fontWeight: 800,
                          fontSize: "12px",
                          letterSpacing: "0.04em",
                          textTransform: "uppercase",
                          border: "1px solid #bfdbfe",
                          marginBottom: "10px",
                        }}
                      >
                        <span
                          style={{
                            width: "8px",
                            height: "8px",
                            borderRadius: "50%",
                            background: "#2563eb",
                            display: "inline-block",
                          }}
                        />
                        Currently Speaking
                      </div>

                      <p
                        style={{
                          margin: 0,
                          lineHeight: 1.95,
                          fontSize: "18px",
                          color: "#1e40af",
                          whiteSpace: "pre-wrap",
                          fontStyle: "italic",
                          opacity: 0.95,
                        }}
                      >
                        {livePartialSegment.text}
                      </p>
                    </div>
                  )}
                </div>
              ) : (
                <div
                  style={{
                    display: "grid",
                    gap: "14px",
                  }}
                >
                  {groupedTranscript.map((seg, idx) => (
                    <div
                      key={`${seg.speaker_label}-${idx}`}
                      style={{
                        border: "1px solid #e2e8f0",
                        borderRadius: "18px",
                        background: "#fcfdff",
                        padding: "18px",
                      }}
                    >
                      <div
                        style={{
                          display: "inline-flex",
                          alignItems: "center",
                          padding: "6px 10px",
                          borderRadius: "999px",
                          background: "#eef2ff",
                          color: "#4338ca",
                          fontWeight: 700,
                          fontSize: "13px",
                          marginBottom: "10px",
                        }}
                      >
                        {seg.speaker_label}
                      </div>

                      <p
                        style={{
                          margin: 0,
                          lineHeight: 1.8,
                          fontSize: "16px",
                          color: "#0f172a",
                          whiteSpace: "pre-wrap",
                        }}
                      >
                        {seg.text}
                      </p>
                    </div>
                  ))}

                  {livePartialSegment?.text && (
                    <div
                      style={{
                        border: "1px solid #bfdbfe",
                        borderRadius: "18px",
                        background: "#eff6ff",
                        padding: "18px",
                      }}
                    >
                      <div
                        style={{
                          display: "inline-flex",
                          alignItems: "center",
                          gap: "8px",
                          padding: "6px 10px",
                          borderRadius: "999px",
                          background: "#dbeafe",
                          color: "#1d4ed8",
                          fontWeight: 800,
                          fontSize: "13px",
                          marginBottom: "10px",
                        }}
                      >
                        {livePartialSegment.speaker_label || "Live Speaker"} • Speaking
                      </div>

                      <p
                        style={{
                          margin: 0,
                          lineHeight: 1.8,
                          fontSize: "16px",
                          color: "#1e3a8a",
                          whiteSpace: "pre-wrap",
                          fontStyle: "italic",
                        }}
                      >
                        {livePartialSegment.text}
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>

            <div
              style={{
                background: "#ffffff",
                border: "1px solid #e2e8f0",
                borderRadius: "22px",
                padding: "22px",
                boxShadow: "0 10px 28px rgba(15, 23, 42, 0.05)",
                minHeight: "540px",
              }}
            >
              <div style={{ marginBottom: "18px" }}>
                <h2
                  style={{
                    margin: 0,
                    fontSize: "28px",
                    fontWeight: 800,
                    color: "#0f172a",
                  }}
                >
                  Live MoM
                </h2>
                <p
                  style={{
                    margin: "6px 0 0 0",
                    color: "#64748b",
                    fontSize: "14px",
                  }}
                >
                  AI-assisted notes and extracted items from the ongoing meeting.
                </p>
              </div>

              {liveMinutes ? (
                <div style={{ display: "grid", gap: "18px" }}>
                  {liveMinutes.active_topic && (
                    <div
                      style={{
                        border: "1px solid #e2e8f0",
                        borderRadius: "18px",
                        padding: "16px",
                        background: "#f8fafc",
                      }}
                    >
                      <div
                        style={{
                          fontSize: "13px",
                          fontWeight: 800,
                          letterSpacing: "0.08em",
                          textTransform: "uppercase",
                          color: "#64748b",
                          marginBottom: "8px",
                        }}
                      >
                        Active Topic
                      </div>
                      <div
                        style={{
                          fontSize: "16px",
                          fontWeight: 700,
                          color: "#0f172a",
                          lineHeight: 1.6,
                        }}
                      >
                        {liveMinutes.active_topic}
                      </div>
                    </div>
                  )}

                  {Array.isArray(liveMinutes.summary_points) &&
                    liveMinutes.summary_points.length > 0 && (
                      <div
                        style={{
                          border: "1px solid #e2e8f0",
                          borderRadius: "18px",
                          padding: "16px",
                          background: "#f8fafc",
                        }}
                      >
                        <h3
                          style={{
                            margin: "0 0 12px 0",
                            fontSize: "18px",
                            fontWeight: 800,
                            color: "#0f172a",
                          }}
                        >
                          Summary Points
                        </h3>
                        <ul
                          style={{
                            margin: 0,
                            paddingLeft: "20px",
                            lineHeight: 1.8,
                            color: "#334155",
                          }}
                        >
                          {liveMinutes.summary_points.map(
                            (item: string, idx: number) => (
                              <li key={idx}>{item}</li>
                            )
                          )}
                        </ul>
                      </div>
                    )}

                  {Array.isArray(liveMinutes.decision_candidates) &&
                    liveMinutes.decision_candidates.length > 0 && (
                      <div
                        style={{
                          border: "1px solid #e2e8f0",
                          borderRadius: "18px",
                          padding: "16px",
                          background: "#f8fafc",
                        }}
                      >
                        <h3
                          style={{
                            margin: "0 0 12px 0",
                            fontSize: "18px",
                            fontWeight: 800,
                            color: "#0f172a",
                          }}
                        >
                          Decision Candidates
                        </h3>
                        <ul
                          style={{
                            margin: 0,
                            paddingLeft: "20px",
                            lineHeight: 1.8,
                            color: "#334155",
                          }}
                        >
                          {liveMinutes.decision_candidates.map(
                            (item: string, idx: number) => (
                              <li key={idx}>{item}</li>
                            )
                          )}
                        </ul>
                      </div>
                    )}

                  {Array.isArray(liveMinutes.action_item_candidates) &&
                    liveMinutes.action_item_candidates.length > 0 && (
                      <div
                        style={{
                          border: "1px solid #e2e8f0",
                          borderRadius: "18px",
                          padding: "16px",
                          background: "#f8fafc",
                        }}
                      >
                        <h3
                          style={{
                            margin: "0 0 12px 0",
                            fontSize: "18px",
                            fontWeight: 800,
                            color: "#0f172a",
                          }}
                        >
                          Action Item Candidates
                        </h3>
                        <ul
                          style={{
                            margin: 0,
                            paddingLeft: "20px",
                            lineHeight: 1.8,
                            color: "#334155",
                          }}
                        >
                          {liveMinutes.action_item_candidates.map(
                            (item: string, idx: number) => (
                              <li key={idx}>{item}</li>
                            )
                          )}
                        </ul>
                      </div>
                    )}
                </div>
              ) : (
                <div
                  style={{
                    minHeight: "420px",
                    display: "grid",
                    placeItems: "center",
                    border: "1px dashed #cbd5e1",
                    borderRadius: "18px",
                    background: "#f8fafc",
                    textAlign: "center",
                    padding: "24px",
                  }}
                >
                  <div>
                    <div
                      style={{
                        fontSize: "18px",
                        fontWeight: 700,
                        color: "#334155",
                        marginBottom: "6px",
                      }}
                    >
                      No live notes yet
                    </div>
                    <div style={{ color: "#64748b" }}>
                      AI-generated notes will appear here as the meeting progresses.
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}