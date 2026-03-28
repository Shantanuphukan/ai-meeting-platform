export default function Dashboard() {
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
                Overview
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
                Dashboard
              </h1>

              <p
                style={{
                  margin: "10px 0 0 0",
                  color: "#64748b",
                  fontSize: "15px",
                  maxWidth: "720px",
                }}
              >
                AI Meeting Platform Dashboard
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
              Workspace Ready
            </div>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
              gap: "16px",
              marginBottom: "22px",
            }}
          >
            <div
              style={{
                border: "1px solid #e2e8f0",
                borderRadius: "20px",
                background: "#ffffff",
                padding: "20px",
                boxShadow: "0 10px 28px rgba(15, 23, 42, 0.05)",
              }}
            >
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
                Section
              </div>
              <div
                style={{
                  fontSize: "28px",
                  fontWeight: 800,
                  color: "#0f172a",
                  lineHeight: 1.1,
                }}
              >
                Dashboard
              </div>
            </div>

            <div
              style={{
                border: "1px solid #e2e8f0",
                borderRadius: "20px",
                background: "#ffffff",
                padding: "20px",
                boxShadow: "0 10px 28px rgba(15, 23, 42, 0.05)",
              }}
            >
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
                Platform
              </div>
              <div
                style={{
                  fontSize: "20px",
                  fontWeight: 800,
                  color: "#0f172a",
                  lineHeight: 1.3,
                }}
              >
                AI Meeting Platform Dashboard
              </div>
            </div>

            <div
              style={{
                border: "1px solid #e2e8f0",
                borderRadius: "20px",
                background: "#ffffff",
                padding: "20px",
                boxShadow: "0 10px 28px rgba(15, 23, 42, 0.05)",
              }}
            >
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
                Status
              </div>
              <div
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "8px",
                  padding: "8px 12px",
                  borderRadius: "999px",
                  background: "#ecfdf5",
                  color: "#166534",
                  border: "1px solid #bbf7d0",
                  fontWeight: 800,
                  fontSize: "14px",
                }}
              >
                <span
                  style={{
                    width: "8px",
                    height: "8px",
                    borderRadius: "50%",
                    background: "#16a34a",
                    display: "inline-block",
                  }}
                />
                Active
              </div>
            </div>
          </div>

          <div
            style={{
              border: "1px solid #e2e8f0",
              borderRadius: "24px",
              background: "#ffffff",
              padding: "24px",
              boxShadow: "0 10px 28px rgba(15, 23, 42, 0.05)",
            }}
          >
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
              Main Workspace
            </div>

            <h2
              style={{
                margin: "0 0 10px 0",
                fontSize: "32px",
                fontWeight: 800,
                color: "#0f172a",
                lineHeight: 1.15,
              }}
            >
              Dashboard
            </h2>

            <p
              style={{
                margin: 0,
                fontSize: "18px",
                lineHeight: 1.85,
                color: "#334155",
                maxWidth: "860px",
              }}
            >
              AI Meeting Platform Dashboard
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}