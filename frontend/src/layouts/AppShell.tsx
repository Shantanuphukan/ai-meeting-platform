import { Link, Outlet, useLocation } from "react-router-dom";

function navItemStyle(active: boolean): React.CSSProperties {
  return {
    display: "flex",
    alignItems: "center",
    gap: "10px",
    padding: "12px 14px",
    borderRadius: "14px",
    textDecoration: "none",
    fontWeight: 700,
    fontSize: "15px",
    color: active ? "#1d4ed8" : "#334155",
    background: active ? "#eff6ff" : "transparent",
    border: active ? "1px solid #bfdbfe" : "1px solid transparent",
    transition: "all 0.2s ease",
  };
}

export default function AppShell() {
  const location = useLocation();

  const isActive = (path: string) => {
    if (path === "/") return location.pathname === "/";
    return location.pathname.startsWith(path);
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "grid",
        gridTemplateColumns: "280px minmax(0, 1fr)",
        background: "linear-gradient(180deg, #f8fbff 0%, #f5f7fb 45%, #eef3f8 100%)",
      }}
    >
      <aside
        style={{
          borderRight: "1px solid #e2e8f0",
          background: "rgba(255,255,255,0.92)",
          backdropFilter: "blur(12px)",
          padding: "22px 18px",
          display: "flex",
          flexDirection: "column",
          gap: "18px",
          position: "sticky",
          top: 0,
          height: "100vh",
          boxSizing: "border-box",
        }}
      >
        <div
          style={{
            padding: "10px 8px 18px 8px",
            borderBottom: "1px solid #e2e8f0",
          }}
        >
          <div
            style={{
              fontSize: "12px",
              fontWeight: 800,
              letterSpacing: "0.16em",
              textTransform: "uppercase",
              color: "#64748b",
              marginBottom: "8px",
            }}
          >
            Workspace
          </div>
          <div
            style={{
              fontSize: "26px",
              lineHeight: 1.1,
              fontWeight: 900,
              color: "#0f172a",
            }}
          >
            Meeting Minute
            <br />
            System
          </div>
        </div>

        <nav
          style={{
            display: "grid",
            gap: "8px",
          }}
        >
          <Link to="/" style={navItemStyle(isActive("/"))}>
            Dashboard
          </Link>

          <Link to="/start" style={navItemStyle(isActive("/start"))}>
            Start Meeting
          </Link>

          <Link to="/archive" style={navItemStyle(isActive("/archive"))}>
            Archive
          </Link>
        </nav>

        <div
          style={{
            marginTop: "auto",
            border: "1px solid #e2e8f0",
            borderRadius: "18px",
            background: "#ffffff",
            padding: "16px",
            boxShadow: "0 10px 28px rgba(15, 23, 42, 0.05)",
          }}
        >
          <div
            style={{
              fontSize: "13px",
              fontWeight: 800,
              textTransform: "uppercase",
              letterSpacing: "0.08em",
              color: "#64748b",
              marginBottom: "8px",
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
            Ready
          </div>
        </div>
      </aside>

      <div
        style={{
          minWidth: 0,
          display: "flex",
          flexDirection: "column",
          minHeight: "100vh",
        }}
      >
        <header
          style={{
            position: "sticky",
            top: 0,
            zIndex: 20,
            background: "rgba(255,255,255,0.85)",
            backdropFilter: "blur(12px)",
            borderBottom: "1px solid #e2e8f0",
            padding: "18px 24px",
          }}
        >
          <div
            style={{
              textAlign: "center",
              fontSize: "clamp(18px, 2vw, 26px)",
              fontWeight: 900,
              letterSpacing: "0.08em",
              textTransform: "uppercase",
              color: "#0f172a",
            }}
          >
            Meeting Minute System
          </div>
        </header>

        <main
          style={{
            flex: 1,
            minWidth: 0,
          }}
        >
          <Outlet />
        </main>

        <footer
          style={{
            borderTop: "1px solid #e2e8f0",
            background: "rgba(255,255,255,0.75)",
            backdropFilter: "blur(10px)",
            padding: "16px 24px",
            textAlign: "center",
            fontWeight: 700,
            color: "#475569",
          }}
        >
          @meeting minutes system
        </footer>
      </div>
    </div>
  );
}