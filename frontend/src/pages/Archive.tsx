import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../services/api";

type MeetingItem = {
  id: string;
  title?: string;
  status?: string;
  created_at?: string;
  ended_at?: string;
  updated_at?: string;
};

function formatDateTime(value?: string) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";

  return date.toLocaleString([], {
    year: "numeric",
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function getStatusStyles(status?: string) {
  const normalized = (status || "").toLowerCase();

  if (normalized === "ended") {
    return {
      bg: "#ecfdf5",
      color: "#166534",
      border: "#bbf7d0",
      label: "Ended",
    };
  }

  if (normalized === "live") {
    return {
      bg: "#eff6ff",
      color: "#1d4ed8",
      border: "#bfdbfe",
      label: "Live",
    };
  }

  if (normalized === "interrupted") {
    return {
      bg: "#fff7ed",
      color: "#c2410c",
      border: "#fdba74",
      label: "Interrupted",
    };
  }

  return {
    bg: "#f8fafc",
    color: "#475569",
    border: "#cbd5e1",
    label: status || "Unknown",
  };
}

function getSortableDate(m: MeetingItem) {
  return m.ended_at || m.updated_at || m.created_at || "";
}

export default function Archive() {
  const [meetings, setMeetings] = useState<MeetingItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [pageSize, setPageSize] = useState(10);
  const [page, setPage] = useState(1);
  const [deletingId, setDeletingId] = useState<string | null>(null);
  const navigate = useNavigate();

  const loadMeetings = async () => {
    try {
      const res = await api.get("/api/meetings");
      setMeetings(res.data || []);
    } catch (error) {
      console.error("Failed to load archive:", error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadMeetings();
  }, []);

  useEffect(() => {
    setPage(1);
  }, [search, pageSize]);

  const handleDeleteMeeting = async (meetingId: string) => {
    const confirmed = window.confirm(
      "Are you sure you want to delete this meeting record? This will also remove its transcript and minutes."
    );

    if (!confirmed) return;

    try {
      setDeletingId(meetingId);
      await api.delete(`/api/meetings/${meetingId}`);
      setMeetings((prev) => prev.filter((m) => m.id !== meetingId));
    } catch (error) {
      console.error("Failed to delete meeting:", error);
      alert("Failed to delete meeting.");
    } finally {
      setDeletingId(null);
    }
  };

  const sortedMeetings = useMemo(() => {
    return [...meetings].sort((a, b) => {
      const aTime = new Date(getSortableDate(a)).getTime() || 0;
      const bTime = new Date(getSortableDate(b)).getTime() || 0;
      return bTime - aTime;
    });
  }, [meetings]);

  const filteredMeetings = useMemo(() => {
    const query = search.trim().toLowerCase();
    if (!query) return sortedMeetings;

    return sortedMeetings.filter((m) => {
      const title = (m.title || "").toLowerCase();
      const status = (m.status || "").toLowerCase();
      const id = (m.id || "").toLowerCase();
      return title.includes(query) || status.includes(query) || id.includes(query);
    });
  }, [sortedMeetings, search]);

  const totalPages = Math.max(1, Math.ceil(filteredMeetings.length / pageSize));

  const paginatedMeetings = useMemo(() => {
    const start = (page - 1) * pageSize;
    const end = start + pageSize;
    return filteredMeetings.slice(start, end);
  }, [filteredMeetings, page, pageSize]);

  const counts = useMemo(() => {
    const total = meetings.length;
    const ended = meetings.filter((m) => (m.status || "").toLowerCase() === "ended").length;
    const live = meetings.filter((m) => (m.status || "").toLowerCase() === "live").length;
    const interrupted = meetings.filter((m) => (m.status || "").toLowerCase() === "interrupted").length;

    return { total, ended, live, interrupted };
  }, [meetings]);

  return (
    <div
      style={{
        minHeight: "100vh",
        background: "linear-gradient(180deg, #f8fbff 0%, #f5f7fb 45%, #eef3f8 100%)",
        padding: "24px",
        color: "#0f172a",
      }}
    >
      <div style={{ maxWidth: "1400px", margin: "0 auto" }}>
        <div
          style={{
            background: "rgba(255,255,255,0.9)",
            backdropFilter: "blur(10px)",
            border: "1px solid #e2e8f0",
            borderRadius: "24px",
            boxShadow: "0 18px 45px rgba(15, 23, 42, 0.08)",
            padding: "24px",
          }}
        >
          <div style={{ marginBottom: "22px" }}>
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
              Meeting History
            </div>

            <h1
              style={{
                margin: 0,
                fontSize: "clamp(28px, 4vw, 42px)",
                lineHeight: 1.05,
                fontWeight: 800,
                color: "#0f172a",
              }}
            >
              Meeting Archive
            </h1>

            <p
              style={{
                margin: "10px 0 0 0",
                color: "#64748b",
                fontSize: "15px",
                maxWidth: "760px",
                lineHeight: 1.7,
              }}
            >
              Browse past meetings, review their final status, and reopen structured minutes anytime.
            </p>

            <div
              style={{
                marginTop: "10px",
                display: "inline-flex",
                alignItems: "center",
                padding: "8px 12px",
                borderRadius: "999px",
                background: "#eff6ff",
                color: "#1d4ed8",
                border: "1px solid #bfdbfe",
                fontWeight: 700,
                fontSize: "13px",
              }}
            >
              Hint: Meetings are sorted from newest to oldest by default.
            </div>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(4, minmax(0, 1fr))",
              gap: "14px",
              marginBottom: "22px",
            }}
          >
            {[
              { label: "Total", value: counts.total, color: "#0f172a" },
              { label: "Ended", value: counts.ended, color: "#166534" },
              { label: "Live", value: counts.live, color: "#1d4ed8" },
              { label: "Interrupted", value: counts.interrupted, color: "#c2410c" },
            ].map((card) => (
              <div
                key={card.label}
                style={{
                  padding: "18px",
                  borderRadius: "18px",
                  border: "1px solid #e2e8f0",
                  background: "#fcfdff",
                  boxShadow: "0 10px 28px rgba(15, 23, 42, 0.05)",
                }}
              >
                <div style={{ fontSize: "13px", color: "#64748b", fontWeight: 700 }}>
                  {card.label}
                </div>
                <div style={{ fontSize: "30px", fontWeight: 800, color: card.color, marginTop: "6px" }}>
                  {card.value}
                </div>
              </div>
            ))}
          </div>

          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              gap: "14px",
              flexWrap: "wrap",
              marginBottom: "20px",
              padding: "16px",
              borderRadius: "20px",
              border: "1px solid #e2e8f0",
              background: "#ffffff",
              boxShadow: "0 10px 28px rgba(15, 23, 42, 0.04)",
            }}
          >
            <div style={{ flex: 1, minWidth: "240px" }}>
              <label
                style={{
                  display: "block",
                  marginBottom: "8px",
                  fontSize: "13px",
                  fontWeight: 700,
                  color: "#64748b",
                  textTransform: "uppercase",
                  letterSpacing: "0.06em",
                }}
              >
                Search Meetings
              </label>
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search by title, status, or meeting ID"
                style={{
                  width: "100%",
                  height: "46px",
                  borderRadius: "14px",
                  border: "1px solid #cbd5e1",
                  padding: "0 14px",
                  fontSize: "14px",
                  outline: "none",
                  background: "#ffffff",
                  color: "#0f172a",
                  boxSizing: "border-box",
                }}
              />
            </div>

            <div style={{ minWidth: "180px" }}>
              <label
                style={{
                  display: "block",
                  marginBottom: "8px",
                  fontSize: "13px",
                  fontWeight: 700,
                  color: "#64748b",
                  textTransform: "uppercase",
                  letterSpacing: "0.06em",
                }}
              >
                Results Per Page
              </label>
              <select
                value={pageSize}
                onChange={(e) => setPageSize(Number(e.target.value))}
                style={{
                  width: "100%",
                  height: "46px",
                  borderRadius: "14px",
                  border: "1px solid #cbd5e1",
                  padding: "0 14px",
                  fontSize: "14px",
                  outline: "none",
                  background: "#ffffff",
                  color: "#0f172a",
                  boxSizing: "border-box",
                }}
              >
                <option value={10}>10</option>
                <option value={25}>25</option>
                <option value={50}>50</option>
                <option value={100}>100</option>
              </select>
            </div>
          </div>

          {loading ? (
            <div
              style={{
                minHeight: "420px",
                display: "grid",
                placeItems: "center",
                border: "1px dashed #cbd5e1",
                borderRadius: "20px",
                background: "#f8fafc",
                textAlign: "center",
                padding: "24px",
              }}
            >
              <div style={{ fontSize: "18px", fontWeight: 700, color: "#334155" }}>
                Loading archive...
              </div>
            </div>
          ) : filteredMeetings.length === 0 ? (
            <div
              style={{
                minHeight: "420px",
                display: "grid",
                placeItems: "center",
                border: "1px dashed #cbd5e1",
                borderRadius: "20px",
                background: "#f8fafc",
                textAlign: "center",
                padding: "24px",
              }}
            >
              <div>
                <div style={{ fontSize: "20px", fontWeight: 800, color: "#334155", marginBottom: "8px" }}>
                  No matching meetings found
                </div>
                <div style={{ color: "#64748b", maxWidth: "520px" }}>
                  Try changing your search text or page size selection to view more results.
                </div>
              </div>
            </div>
          ) : (
            <>
              <div style={{ display: "grid", gap: "16px" }}>
                {paginatedMeetings.map((m) => {
                  const status = getStatusStyles(m.status);
                  const isDeleting = deletingId === m.id;

                  return (
                    <div
                      key={m.id}
                      style={{
                        border: "1px solid #e2e8f0",
                        borderRadius: "22px",
                        background: "#ffffff",
                        padding: "20px",
                        boxShadow: "0 10px 28px rgba(15, 23, 42, 0.05)",
                      }}
                    >
                      <div
                        style={{
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "flex-start",
                          gap: "16px",
                          flexWrap: "wrap",
                        }}
                      >
                        <div style={{ minWidth: 0, flex: 1 }}>
                          <div
                            style={{
                              display: "flex",
                              gap: "10px",
                              alignItems: "center",
                              flexWrap: "wrap",
                              marginBottom: "10px",
                            }}
                          >
                            <span
                              style={{
                                display: "inline-flex",
                                alignItems: "center",
                                padding: "8px 12px",
                                borderRadius: "999px",
                                background: status.bg,
                                color: status.color,
                                border: `1px solid ${status.border}`,
                                fontWeight: 800,
                                fontSize: "13px",
                              }}
                            >
                              {status.label}
                            </span>
                          </div>

                          <h3
                            style={{
                              margin: 0,
                              fontSize: "30px",
                              lineHeight: 1.15,
                              fontWeight: 800,
                              color: "#0f172a",
                              wordBreak: "break-word",
                            }}
                          >
                            {m.title || "Untitled Meeting"}
                          </h3>

                          <div
                            style={{
                              display: "flex",
                              gap: "10px",
                              flexWrap: "wrap",
                              marginTop: "14px",
                            }}
                          >
                            <span
                              style={{
                                display: "inline-flex",
                                alignItems: "center",
                                padding: "8px 12px",
                                borderRadius: "999px",
                                background: "#f8fafc",
                                color: "#334155",
                                border: "1px solid #e2e8f0",
                                fontWeight: 700,
                                fontSize: "13px",
                              }}
                            >
                              Created: {formatDateTime(m.created_at)}
                            </span>

                            <span
                              style={{
                                display: "inline-flex",
                                alignItems: "center",
                                padding: "8px 12px",
                                borderRadius: "999px",
                                background: "#f8fafc",
                                color: "#334155",
                                border: "1px solid #e2e8f0",
                                fontWeight: 700,
                                fontSize: "13px",
                              }}
                            >
                              Ended: {formatDateTime(m.ended_at)}
                            </span>

                            <span
                              style={{
                                display: "inline-flex",
                                alignItems: "center",
                                padding: "8px 12px",
                                borderRadius: "999px",
                                background: "#f8fafc",
                                color: "#334155",
                                border: "1px solid #e2e8f0",
                                fontWeight: 700,
                                fontSize: "13px",
                              }}
                            >
                              ID: {m.id}
                            </span>
                          </div>
                        </div>

                        <div
                          style={{
                            display: "flex",
                            gap: "10px",
                            flexWrap: "wrap",
                          }}
                        >
                          <button
                            onClick={() => navigate(`/review/${m.id}`)}
                            style={{
                              border: "none",
                              borderRadius: "14px",
                              padding: "14px 18px",
                              fontWeight: 800,
                              fontSize: "15px",
                              cursor: "pointer",
                              background: "linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%)",
                              color: "#fff",
                              boxShadow: "0 12px 24px rgba(29, 78, 216, 0.22)",
                              minWidth: "160px",
                            }}
                          >
                            Open Minutes
                          </button>

                          <button
                            onClick={() => handleDeleteMeeting(m.id)}
                            disabled={isDeleting}
                            style={{
                              border: "1px solid #fecaca",
                              borderRadius: "14px",
                              padding: "14px 18px",
                              fontWeight: 800,
                              fontSize: "15px",
                              cursor: isDeleting ? "not-allowed" : "pointer",
                              background: isDeleting ? "#fee2e2" : "#fff1f2",
                              color: "#b91c1c",
                              minWidth: "130px",
                            }}
                          >
                            {isDeleting ? "Deleting..." : "Delete"}
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>

              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  gap: "14px",
                  flexWrap: "wrap",
                  marginTop: "22px",
                  padding: "16px",
                  borderRadius: "20px",
                  border: "1px solid #e2e8f0",
                  background: "#ffffff",
                  boxShadow: "0 10px 28px rgba(15, 23, 42, 0.04)",
                }}
              >
                <div style={{ color: "#475569", fontSize: "14px", fontWeight: 600 }}>
                  Showing {(page - 1) * pageSize + 1}–
                  {Math.min(page * pageSize, filteredMeetings.length)} of {filteredMeetings.length} meetings
                </div>

                <div style={{ display: "flex", gap: "10px", alignItems: "center", flexWrap: "wrap" }}>
                  <button
                    onClick={() => setPage((prev) => Math.max(1, prev - 1))}
                    disabled={page === 1}
                    style={{
                      border: "1px solid #cbd5e1",
                      borderRadius: "12px",
                      padding: "10px 14px",
                      background: page === 1 ? "#f8fafc" : "#ffffff",
                      color: page === 1 ? "#94a3b8" : "#0f172a",
                      fontWeight: 700,
                      cursor: page === 1 ? "not-allowed" : "pointer",
                    }}
                  >
                    Previous
                  </button>

                  <div
                    style={{
                      padding: "10px 14px",
                      borderRadius: "12px",
                      background: "#eff6ff",
                      color: "#1d4ed8",
                      border: "1px solid #bfdbfe",
                      fontWeight: 800,
                    }}
                  >
                    Page {page} of {totalPages}
                  </div>

                  <button
                    onClick={() => setPage((prev) => Math.min(totalPages, prev + 1))}
                    disabled={page === totalPages}
                    style={{
                      border: "1px solid #cbd5e1",
                      borderRadius: "12px",
                      padding: "10px 14px",
                      background: page === totalPages ? "#f8fafc" : "#ffffff",
                      color: page === totalPages ? "#94a3b8" : "#0f172a",
                      fontWeight: 700,
                      cursor: page === totalPages ? "not-allowed" : "pointer",
                    }}
                  >
                    Next
                  </button>
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}