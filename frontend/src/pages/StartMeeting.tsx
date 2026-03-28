import { useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../services/api";

export default function StartMeeting() {
  const [title, setTitle] = useState("");
  const [language, setLanguage] = useState("en");
  const [template, setTemplate] = useState("standard");
  const navigate = useNavigate();

  const handleStart = async () => {
    const createRes = await api.post("/api/meetings", {
      title,
      language,
      template,
    });

    const meetingId = createRes.data.meeting_id;
    await api.post(`/api/meetings/${meetingId}/start`);
    navigate(`/live/${meetingId}`);
  };

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
          maxWidth: "1100px",
          margin: "0 auto",
        }}
      >
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
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "flex-start",
              gap: "16px",
              flexWrap: "wrap",
              marginBottom: "24px",
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
                Meeting Setup
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
                Start Meeting
              </h1>

              <p
                style={{
                  margin: "10px 0 0 0",
                  color: "#64748b",
                  fontSize: "15px",
                  maxWidth: "720px",
                }}
              >
                Configure your meeting title, language, and template before
                launching the live workspace.
              </p>
            </div>

            <div
              style={{
                display: "inline-flex",
                alignItems: "center",
                padding: "10px 14px",
                borderRadius: "999px",
                background: "#eff6ff",
                color: "#1d4ed8",
                border: "1px solid #bfdbfe",
                fontWeight: 700,
                fontSize: "14px",
              }}
            >
              Live Session Ready
            </div>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "minmax(0, 1.2fr) minmax(320px, 0.8fr)",
              gap: "22px",
              alignItems: "stretch",
            }}
          >
            <div
              style={{
                border: "1px solid #e2e8f0",
                borderRadius: "22px",
                background: "#ffffff",
                padding: "24px",
                boxShadow: "0 10px 28px rgba(15, 23, 42, 0.05)",
              }}
            >
              <div
                style={{
                  marginBottom: "18px",
                }}
              >
                <h2
                  style={{
                    margin: 0,
                    fontSize: "28px",
                    fontWeight: 800,
                    color: "#0f172a",
                  }}
                >
                  Meeting Details
                </h2>
                <p
                  style={{
                    margin: "6px 0 0 0",
                    color: "#64748b",
                    fontSize: "14px",
                  }}
                >
                  Fill in the basic details to start a new live meeting session.
                </p>
              </div>

              <div
                style={{
                  display: "grid",
                  gap: "18px",
                }}
              >
                <div>
                  <label
                    style={{
                      display: "block",
                      marginBottom: "8px",
                      fontSize: "14px",
                      fontWeight: 700,
                      color: "#334155",
                    }}
                  >
                    Meeting Title
                  </label>
                  <input
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                    placeholder="Meeting Title"
                    style={{
                      width: "100%",
                      height: "52px",
                      borderRadius: "14px",
                      border: "1px solid #cbd5e1",
                      padding: "0 16px",
                      fontSize: "15px",
                      outline: "none",
                      background: "#ffffff",
                      color: "#0f172a",
                      boxSizing: "border-box",
                    }}
                  />
                </div>

                <div>
                  <label
                    style={{
                      display: "block",
                      marginBottom: "8px",
                      fontSize: "14px",
                      fontWeight: 700,
                      color: "#334155",
                    }}
                  >
                    Language
                  </label>
                  <select
                    value={language}
                    onChange={(e) => setLanguage(e.target.value)}
                    style={{
                    width: "100%",
                    height: "52px",
                    borderRadius: "14px",
                    border: "1px solid #cbd5e1",
                    padding: "0 16px",
                    fontSize: "15px",
                    outline: "none",
                    background: "#ffffff",
                    color: "#0f172a",
                    boxSizing: "border-box",
                  }}
               >
  <option value="en">English</option>
  <option value="hi">Hindi</option>
  <option value="as">Assamese</option>
  <option value="mix">Mixed (English + Hindi + Assamese)</option>
</select>
                </div>

                <div>
                  <label
                    style={{
                      display: "block",
                      marginBottom: "8px",
                      fontSize: "14px",
                      fontWeight: 700,
                      color: "#334155",
                    }}
                  >
                    Template
                  </label>
                <select
  value={template}
  onChange={(e) => setTemplate(e.target.value)}
  style={{
    width: "100%",
    height: "52px",
    borderRadius: "14px",
    border: "1px solid #cbd5e1",
    padding: "0 16px",
    fontSize: "15px",
    outline: "none",
    background: "#ffffff",
    color: "#0f172a",
    boxSizing: "border-box",
  }}
>
  <option value="standard">Standard Meeting</option>
  <option value="board">Board Meeting</option>
  <option value="project">Project Review</option>
  <option value="standup">Daily Standup</option>
  <option value="training">Training Session</option>
  <option value="government">Government Meeting</option>
</select>
                </div>

                <div style={{ paddingTop: "6px" }}>
                  <button
                    onClick={handleStart}
                    style={{
                      border: "none",
                      borderRadius: "14px",
                      padding: "15px 20px",
                      fontWeight: 800,
                      fontSize: "15px",
                      cursor: "pointer",
                      background:
                        "linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%)",
                      color: "#fff",
                      boxShadow: "0 12px 24px rgba(29, 78, 216, 0.22)",
                      minWidth: "180px",
                    }}
                  >
                    Start Live Meeting
                  </button>
                </div>
              </div>
            </div>

            <div
              style={{
                border: "1px solid #e2e8f0",
                borderRadius: "22px",
                background: "#ffffff",
                padding: "24px",
                boxShadow: "0 10px 28px rgba(15, 23, 42, 0.05)",
                display: "flex",
                flexDirection: "column",
                justifyContent: "space-between",
              }}
            >
              <div>
                <div
                  style={{
                    fontSize: "13px",
                    fontWeight: 700,
                    letterSpacing: "0.08em",
                    textTransform: "uppercase",
                    color: "#64748b",
                    marginBottom: "10px",
                  }}
                >
                  Quick Overview
                </div>

                <h2
                  style={{
                    margin: "0 0 10px 0",
                    fontSize: "28px",
                    fontWeight: 800,
                    color: "#0f172a",
                    lineHeight: 1.15,
                  }}
                >
                  Launch a New Session
                </h2>

                <p
                  style={{
                    margin: 0,
                    fontSize: "16px",
                    lineHeight: 1.8,
                    color: "#334155",
                  }}
                >
                  Create a meeting room, begin live transcription, and move
                  directly into the AI-powered review workflow once the session
                  is complete.
                </p>
              </div>

              <div
                style={{
                  display: "grid",
                  gap: "12px",
                  marginTop: "22px",
                }}
              >
                <div
                  style={{
                    border: "1px solid #e2e8f0",
                    borderRadius: "18px",
                    background: "#f8fafc",
                    padding: "16px",
                  }}
                >
                  <div
                    style={{
                      fontSize: "13px",
                      fontWeight: 700,
                      color: "#64748b",
                      marginBottom: "6px",
                      textTransform: "uppercase",
                      letterSpacing: "0.06em",
                    }}
                  >
                    Selected Language
                  </div>
                  <div
                    style={{
                      fontSize: "18px",
                      fontWeight: 800,
                      color: "#0f172a",
                    }}
                  >
                    {
                      {
                        en: "English",
                        hi: "Hindi",
                        as: "Assamese",
                        mix: "Mixed (English + Hindi + Assamese)",
                      }[language] || language
                    }
                  </div>
                </div>

                <div
                  style={{
                    border: "1px solid #e2e8f0",
                    borderRadius: "18px",
                    background: "#f8fafc",
                    padding: "16px",
                  }}
                >
                  <div
                    style={{
                      fontSize: "13px",
                      fontWeight: 700,
                      color: "#64748b",
                      marginBottom: "6px",
                      textTransform: "uppercase",
                      letterSpacing: "0.06em",
                    }}
                  >
                    Selected Template
                  </div>
                  <div
                    style={{
                      fontSize: "18px",
                      fontWeight: 800,
                      color: "#0f172a",
                    }}
                  >
                   {
  {
    standard: "Standard Meeting",
    board: "Board Meeting",
    project: "Project Review",
    standup: "Daily Standup",
    training: "Training Session",
    government: "Government Meeting"
  }[template]
}
                  </div>
                </div>

                <div
                  style={{
                    border: "1px solid #e2e8f0",
                    borderRadius: "18px",
                    background: "#f8fafc",
                    padding: "16px",
                  }}
                >
                  <div
                    style={{
                      fontSize: "13px",
                      fontWeight: 700,
                      color: "#64748b",
                      marginBottom: "6px",
                      textTransform: "uppercase",
                      letterSpacing: "0.06em",
                    }}
                  >
                    Meeting Title Preview
                  </div>
                  <div
                    style={{
                      fontSize: "18px",
                      fontWeight: 800,
                      color: "#0f172a",
                      wordBreak: "break-word",
                    }}
                  >
                    {title?.trim() ? title : "Meeting Title"}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <style>{`
          @media (max-width: 900px) {
            .start-meeting-grid {
              grid-template-columns: 1fr !important;
            }
          }
        `}</style>
      </div>
    </div>
  );
}