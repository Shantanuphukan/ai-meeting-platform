import { Routes, Route } from "react-router-dom";

import AppShell from "./layouts/AppShell";

import Dashboard from "./pages/Dashboard";
import StartMeeting from "./pages/StartMeeting";
import LiveMeeting from "./pages/LiveMeeting";
import ReviewMeeting from "./pages/ReviewMeeting";
import Archive from "./pages/Archive";

export default function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/start" element={<StartMeeting />} />
        <Route path="/live/:meetingId" element={<LiveMeeting />} />
        <Route path="/review/:meetingId" element={<ReviewMeeting />} />
        <Route path="/archive" element={<Archive />} />
      </Route>
    </Routes>
  );
}