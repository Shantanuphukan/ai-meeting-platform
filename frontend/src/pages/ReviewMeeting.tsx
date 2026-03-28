import { useEffect, useMemo, useState } from "react";
import { useParams } from "react-router-dom";
import api from "../services/api";

type TranscriptSegment = {
  id?: string;
  speaker_label?: string;
  text?: string;
  _partial?: boolean;
};

type GroupedTranscriptSegment = {
  speaker_label: string;
  text: string;
};

type ActionItem = {
  owner_name?: string;
  task?: string;
  deadline_text?: string;
};

type MinutesState = {
  summary?: string;
  discussion_points?: string[];
  decisions?: string[];
  action_items?: ActionItem[];
  next_steps?: string[];
  output_language?: string;
  language?: string;
  title?: string;
  [key: string]: any;
};

type ReviewLabels = {
  workspace: string;
  reviewReady: string;
  meetingId: string;
  singleSpeaker: string;
  multiSpeaker: string;
  editMinutes: string;
  saveChanges: string;
  saving: string;
  cancel: string;
  exportDocx: string;
  exporting: string;
  transcriptTitle: string;
  transcriptSubtitle: string;
  loadingTranscript: string;
  noTranscriptTitle: string;
  noTranscriptSubtitle: string;
  minutesTitle: string;
  minutesSubtitle: string;
  loadingMinutes: string;
  summary: string;
  discussionPoints: string;
  decisions: string;
  actionItems: string;
  nextSteps: string;
  noDiscussion: string;
  noDecisions: string;
  noActions: string;
  noNextSteps: string;
  actionFormatHelp: string;
  minutesUnavailableTitle: string;
  minutesUnavailableSubtitle: string;
  liveSpeaker: string;
};

const LABELS: Record<string, ReviewLabels> = {
  en: {
    workspace: "Meeting Review Workspace",
    reviewReady: "Review Ready",
    meetingId: "Meeting ID",
    singleSpeaker: "Single Speaker",
    multiSpeaker: "Multi Speaker",
    editMinutes: "Edit Minutes",
    saveChanges: "Save Changes",
    saving: "Saving...",
    cancel: "Cancel",
    exportDocx: "Export DOCX",
    exporting: "Exporting...",
    transcriptTitle: "Transcript",
    transcriptSubtitle: "Final captured transcript for this meeting.",
    loadingTranscript: "Loading transcript...",
    noTranscriptTitle: "No transcript available",
    noTranscriptSubtitle: "No transcript was found for this meeting.",
    minutesTitle: "Minutes",
    minutesSubtitle: "Structured notes, decisions, actions, and next steps.",
    loadingMinutes: "Loading minutes...",
    summary: "Summary",
    discussionPoints: "Discussion Points",
    decisions: "Decisions",
    actionItems: "Action Items",
    nextSteps: "Next Steps",
    noDiscussion: "No discussion points extracted yet.",
    noDecisions: "No decisions extracted yet.",
    noActions: "No action items extracted yet.",
    noNextSteps: "No next steps extracted yet.",
    actionFormatHelp: "One line per item. Format: Owner | Task | Deadline",
    minutesUnavailableTitle: "Minutes not available yet",
    minutesUnavailableSubtitle: "The meeting summary could not be loaded.",
    liveSpeaker: "Live Speaker",
  },
  hi: {
    workspace: "मीटिंग समीक्षा कार्यक्षेत्र",
    reviewReady: "समीक्षा तैयार",
    meetingId: "मीटिंग आईडी",
    singleSpeaker: "एक वक्ता",
    multiSpeaker: "एकाधिक वक्ता",
    editMinutes: "मिनट्स संपादित करें",
    saveChanges: "परिवर्तन सहेजें",
    saving: "सहेजा जा रहा है...",
    cancel: "रद्द करें",
    exportDocx: "DOCX निर्यात करें",
    exporting: "निर्यात हो रहा है...",
    transcriptTitle: "प्रतिलेख",
    transcriptSubtitle: "इस मीटिंग का अंतिम कैप्चर किया गया प्रतिलेख।",
    loadingTranscript: "प्रतिलेख लोड हो रहा है...",
    noTranscriptTitle: "प्रतिलेख उपलब्ध नहीं है",
    noTranscriptSubtitle: "इस मीटिंग के लिए कोई प्रतिलेख नहीं मिला।",
    minutesTitle: "कार्यवृत्त",
    minutesSubtitle: "संरचित सारांश, निर्णय, कार्य बिंदु और अगले कदम।",
    loadingMinutes: "कार्यवृत्त लोड हो रहा है...",
    summary: "सारांश",
    discussionPoints: "चर्चा बिंदु",
    decisions: "निर्णय",
    actionItems: "कार्य बिंदु",
    nextSteps: "अगले कदम",
    noDiscussion: "अभी तक कोई चर्चा बिंदु उपलब्ध नहीं है।",
    noDecisions: "अभी तक कोई निर्णय उपलब्ध नहीं है।",
    noActions: "अभी तक कोई कार्य बिंदु उपलब्ध नहीं है।",
    noNextSteps: "अभी तक कोई अगले कदम उपलब्ध नहीं हैं।",
    actionFormatHelp: "प्रति पंक्ति एक प्रविष्टि। प्रारूप: मालिक | कार्य | समयसीमा",
    minutesUnavailableTitle: "कार्यवृत्त अभी उपलब्ध नहीं है",
    minutesUnavailableSubtitle: "मीटिंग सारांश लोड नहीं हो सका।",
    liveSpeaker: "वक्ता",
  },
  as: {
    workspace: "মিটিং পৰ্যালোচনা কৰ্মক্ষেত্ৰ",
    reviewReady: "পৰ্যালোচনা প্ৰস্তুত",
    meetingId: "মিটিং আইডি",
    singleSpeaker: "এজন বক্তা",
    multiSpeaker: "একাধিক বক্তা",
    editMinutes: "মিনিটছ সম্পাদনা কৰক",
    saveChanges: "সলনি সংৰক্ষণ কৰক",
    saving: "সংৰক্ষণ কৰা হৈছে...",
    cancel: "বাতিল কৰক",
    exportDocx: "DOCX ৰপ্তানি কৰক",
    exporting: "ৰপ্তানি কৰা হৈছে...",
    transcriptTitle: "প্ৰতিলিপি",
    transcriptSubtitle: "এই মিটিঙৰ চূড়ান্ত ধৰা পৰাৰ প্ৰতিলিপি।",
    loadingTranscript: "প্ৰতিলিপি লোড হৈ আছে...",
    noTranscriptTitle: "প্ৰতিলিপি উপলব্ধ নহয়",
    noTranscriptSubtitle: "এই মিটিঙৰ বাবে কোনো প্ৰতিলিপি পোৱা নগ'ল।",
    minutesTitle: "মিনিটছ",
    minutesSubtitle: "গাঁথনি অনুসৰি সাৰাংশ, সিদ্ধান্ত, কৰণীয় কাম আৰু পৰৱৰ্তী পদক্ষেপ।",
    loadingMinutes: "মিনিটছ লোড হৈ আছে...",
    summary: "সাৰাংশ",
    discussionPoints: "আলোচনাৰ মূল বিষয়সমূহ",
    decisions: "সিদ্ধান্তসমূহ",
    actionItems: "কৰণীয় কামসমূহ",
    nextSteps: "পৰৱৰ্তী পদক্ষেপসমূহ",
    noDiscussion: "এতিয়ালৈকে কোনো আলোচনাৰ বিষয় উদ্ধাৰ হোৱা নাই।",
    noDecisions: "এতিয়ালৈকে কোনো সিদ্ধান্ত উদ্ধাৰ হোৱা নাই।",
    noActions: "এতিয়ালৈকে কোনো কৰণীয় কাম উদ্ধাৰ হোৱা নাই।",
    noNextSteps: "এতিয়ালৈকে কোনো পৰৱৰ্তী পদক্ষেপ উদ্ধাৰ হোৱা নাই।",
    actionFormatHelp: "প্ৰতি শাৰী এটাকৈ। বিন্যাস: দায়িত্বশীল | কাম | সময়সীমা",
    minutesUnavailableTitle: "মিনিটছ এতিয়াও উপলব্ধ নহয়",
    minutesUnavailableSubtitle: "মিটিং সাৰাংশ লোড কৰিব পৰা নগ'ল।",
    liveSpeaker: "বক্তা",
  },
    mix: {
    workspace: "Meeting Review Workspace",
    reviewReady: "Review Ready",
    meetingId: "Meeting ID",
    singleSpeaker: "Single Speaker",
    multiSpeaker: "Multi Speaker",
    editMinutes: "Edit Minutes",
    saveChanges: "Save Changes",
    saving: "Saving...",
    cancel: "Cancel",
    exportDocx: "Export DOCX",
    exporting: "Exporting...",
    transcriptTitle: "Transcript",
    transcriptSubtitle: "Final captured transcript for this meeting.",
    loadingTranscript: "Loading transcript...",
    noTranscriptTitle: "No transcript available",
    noTranscriptSubtitle: "No transcript was found for this meeting.",
    minutesTitle: "Minutes",
    minutesSubtitle: "Structured notes, decisions, actions, and next steps.",
    loadingMinutes: "Loading minutes...",
    summary: "Summary",
    discussionPoints: "Discussion Points",
    decisions: "Decisions",
    actionItems: "Action Items",
    nextSteps: "Next Steps",
    noDiscussion: "No discussion points extracted yet.",
    noDecisions: "No decisions extracted yet.",
    noActions: "No action items extracted yet.",
    noNextSteps: "No next steps extracted yet.",
    actionFormatHelp: "One line per item. Format: Owner | Task | Deadline",
    minutesUnavailableTitle: "Minutes not available yet",
    minutesUnavailableSubtitle: "The meeting summary could not be loaded.",
    liveSpeaker: "Live Speaker",
  },
};

function groupTranscriptSegments(
  segments: TranscriptSegment[]
): GroupedTranscriptSegment[] {
  const grouped: GroupedTranscriptSegment[] = [];

  for (const seg of segments) {
    const speaker = (seg.speaker_label || "Live Speaker").trim();
    const text = (seg.text || "").trim();

    if (!text) continue;

    const last = grouped[grouped.length - 1];

    if (last && last.speaker_label === speaker) {
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
      });
    }
  }

  return grouped;
}

function normalizeLinesToArray(value: string) {
  return value
    .split("\n")
    .map((item) => item.trim())
    .filter(Boolean);
}

function actionItemsToText(items: ActionItem[] = []) {
  return items
    .map((item) => {
      const owner = (item.owner_name || "Unassigned").trim();
      const task = (item.task || "").trim();
      const deadline = (item.deadline_text || "").trim();

      if (!task) return "";
      return `${owner} | ${task} | ${deadline}`;
    })
    .filter(Boolean)
    .join("\n");
}

function textToActionItems(value: string): ActionItem[] {
  return value
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const parts = line.split("|").map((p) => p.trim());
      return {
        owner_name: parts[0] || "Unassigned",
        task: parts[1] || "",
        deadline_text: parts[2] || "",
      };
    })
    .filter((item) => item.task);
}

function normalizeLanguage(value?: string) {
  const raw = (value || "").trim().toLowerCase();

  if (raw === "assamese" || raw === "as") return "as";
  if (raw === "hindi" || raw === "hi") return "hi";
  if (raw === "mix" || raw === "mixed" || raw === "mixed-language" || raw === "multilingual") return "mix";
  return "en";
}

export default function ReviewMeeting() {
  const { meetingId = "" } = useParams();
  const [transcript, setTranscript] = useState<TranscriptSegment[]>([]);
  const [minutes, setMinutes] = useState<MinutesState | null>(null);
  const [draftMinutes, setDraftMinutes] = useState<MinutesState | null>(null);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);

  const [discussionText, setDiscussionText] = useState("");
  const [decisionsText, setDecisionsText] = useState("");
  const [actionItemsText, setActionItemsText] = useState("");
  const [nextStepsText, setNextStepsText] = useState("");

  useEffect(() => {
    const load = async () => {
      try {
        const t = await api.get(`/api/review/meetings/${meetingId}/transcript`);

        let m = null;
        try {
          const minutesRes = await api.get(`/api/review/meetings/${meetingId}/minutes`);
          m = minutesRes.data;
        } catch {
          m = null;
        }

        setTranscript(t.data || []);
        setMinutes(m);
        setDraftMinutes(m);

        setDiscussionText((m?.discussion_points || []).join("\n"));
        setDecisionsText((m?.decisions || []).join("\n"));
        setActionItemsText(actionItemsToText(m?.action_items || []));
        setNextStepsText((m?.next_steps || []).join("\n"));
      } catch (error) {
        console.error("Failed to load review data:", error);
      } finally {
        setLoading(false);
      }
    };

    load();
  }, [meetingId]);

  const groupedTranscript = useMemo(
    () => groupTranscriptSegments(transcript),
    [transcript]
  );

  const uniqueSpeakers = useMemo(() => {
    return Array.from(
      new Set(groupedTranscript.map((seg) => seg.speaker_label).filter(Boolean))
    );
  }, [groupedTranscript]);

  const isSingleSpeaker = uniqueSpeakers.length <= 1;

  const reviewLanguage = useMemo(() => {
    return normalizeLanguage(
      draftMinutes?.output_language ||
        draftMinutes?.language ||
        minutes?.output_language ||
        minutes?.language
    );
  }, [draftMinutes, minutes]);

  const labels = useMemo(() => {
    return LABELS[reviewLanguage] || LABELS.en;
  }, [reviewLanguage]);

  const handleExport = async () => {
    try {
      setExporting(true);

      const response = await fetch(
        `http://localhost:8000/api/export/meetings/${meetingId}/docx`,
        {
          method: "POST",
        }
      );

      if (!response.ok) {
        throw new Error("Failed to export DOCX");
      }

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);

      const a = document.createElement("a");
      a.href = url;
      a.download = `meeting_${meetingId}.docx`;
      document.body.appendChild(a);
      a.click();
      a.remove();

      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error(error);
      alert("DOCX export failed");
    } finally {
      setExporting(false);
    }
  };

  const handleEdit = () => {
    if (!minutes) return;

    setDraftMinutes(minutes);
    setDiscussionText((minutes.discussion_points || []).join("\n"));
    setDecisionsText((minutes.decisions || []).join("\n"));
    setActionItemsText(actionItemsToText(minutes.action_items || []));
    setNextStepsText((minutes.next_steps || []).join("\n"));
    setEditing(true);
  };

  const handleCancelEdit = () => {
    setDraftMinutes(minutes);
    setDiscussionText((minutes?.discussion_points || []).join("\n"));
    setDecisionsText((minutes?.decisions || []).join("\n"));
    setActionItemsText(actionItemsToText(minutes?.action_items || []));
    setNextStepsText((minutes?.next_steps || []).join("\n"));
    setEditing(false);
  };

  const handleSave = async () => {
    if (!draftMinutes) return;

    try {
      setSaving(true);

      const payload: MinutesState = {
        ...draftMinutes,
        summary: draftMinutes.summary || "",
        discussion_points: normalizeLinesToArray(discussionText),
        decisions: normalizeLinesToArray(decisionsText),
        action_items: textToActionItems(actionItemsText),
        next_steps: normalizeLinesToArray(nextStepsText),
      };

      await api.patch(`/api/review/meetings/${meetingId}/minutes`, payload);

      setMinutes(payload);
      setDraftMinutes(payload);
      setEditing(false);
    } catch (error) {
      console.error("Failed to save minutes:", error);
      alert("Failed to save minutes");
    } finally {
      setSaving(false);
    }
  };

  const updateDraftSummary = (value: string) => {
    setDraftMinutes((prev) => ({
      ...(prev || {}),
      summary: value,
    }));
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
                {labels.workspace}
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
                {minutes?.title || "Meeting Review"}
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
                    padding: "8px 12px",
                    borderRadius: "999px",
                    background: "#eff6ff",
                    color: "#1d4ed8",
                    fontWeight: 700,
                    border: "1px solid #bfdbfe",
                    fontSize: "14px",
                  }}
                >
                  {labels.reviewReady}
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
                  {labels.meetingId}: {meetingId}
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
                  {isSingleSpeaker ? labels.singleSpeaker : labels.multiSpeaker}
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
              {!editing ? (
                <button
                  onClick={handleEdit}
                  disabled={!minutes}
                  style={{
                    border: "1px solid #cbd5e1",
                    borderRadius: "14px",
                    padding: "14px 18px",
                    fontWeight: 800,
                    fontSize: "15px",
                    cursor: !minutes ? "not-allowed" : "pointer",
                    background: "#ffffff",
                    color: "#0f172a",
                    minWidth: "140px",
                  }}
                >
                  {labels.editMinutes}
                </button>
              ) : (
                <>
                  <button
                    onClick={handleSave}
                    disabled={saving}
                    style={{
                      border: "none",
                      borderRadius: "14px",
                      padding: "14px 18px",
                      fontWeight: 800,
                      fontSize: "15px",
                      cursor: saving ? "not-allowed" : "pointer",
                      background: saving
                        ? "#cbd5e1"
                        : "linear-gradient(135deg, #16a34a 0%, #15803d 100%)",
                      color: "#fff",
                      minWidth: "140px",
                    }}
                  >
                    {saving ? labels.saving : labels.saveChanges}
                  </button>

                  <button
                    onClick={handleCancelEdit}
                    disabled={saving}
                    style={{
                      border: "1px solid #cbd5e1",
                      borderRadius: "14px",
                      padding: "14px 18px",
                      fontWeight: 800,
                      fontSize: "15px",
                      cursor: saving ? "not-allowed" : "pointer",
                      background: "#ffffff",
                      color: "#0f172a",
                      minWidth: "120px",
                    }}
                  >
                    {labels.cancel}
                  </button>
                </>
              )}

              <button
                onClick={handleExport}
                disabled={exporting}
                style={{
                  border: "none",
                  borderRadius: "14px",
                  padding: "14px 18px",
                  fontWeight: 800,
                  fontSize: "15px",
                  cursor: exporting ? "not-allowed" : "pointer",
                  background: exporting
                    ? "#cbd5e1"
                    : "linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%)",
                  color: "#fff",
                  boxShadow: exporting
                    ? "none"
                    : "0 12px 24px rgba(29, 78, 216, 0.22)",
                  minWidth: "160px",
                }}
              >
                {exporting ? labels.exporting : labels.exportDocx}
              </button>
            </div>
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "minmax(0, 1.2fr) minmax(340px, 1fr)",
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
                minHeight: "560px",
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
                  {labels.transcriptTitle}
                </h2>
                <p
                  style={{
                    margin: "6px 0 0 0",
                    color: "#64748b",
                    fontSize: "14px",
                  }}
                >
                  {labels.transcriptSubtitle}
                </p>
              </div>

              {loading ? (
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
                  <div style={{ fontSize: "18px", fontWeight: 700, color: "#334155" }}>
                    {labels.loadingTranscript}
                  </div>
                </div>
              ) : groupedTranscript.length === 0 ? (
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
                      {labels.noTranscriptTitle}
                    </div>
                    <div style={{ color: "#64748b" }}>
                      {labels.noTranscriptSubtitle}
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
                    gap: "12px",
                  }}
                >
                  {groupedTranscript.map((seg, idx) => (
                    <div
                      key={`${seg.speaker_label}-${idx}-${seg.text.slice(0, 24)}`}
                      style={{
                        borderBottom:
                          idx !== groupedTranscript.length - 1
                            ? "1px solid #eef2f7"
                            : "none",
                        paddingBottom:
                          idx !== groupedTranscript.length - 1 ? "12px" : "0",
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
                        {seg.text}
                      </p>
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{ display: "grid", gap: "14px" }}>
                  {groupedTranscript.map((seg, idx) => (
                    <div
                      key={`${seg.speaker_label}-${idx}-${seg.text.slice(0, 24)}`}
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
                        {seg.speaker_label || labels.liveSpeaker}
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
                minHeight: "560px",
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
                  {labels.minutesTitle}
                </h2>
                <p
                  style={{
                    margin: "6px 0 0 0",
                    color: "#64748b",
                    fontSize: "14px",
                  }}
                >
                  {labels.minutesSubtitle}
                </p>
              </div>

              {loading ? (
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
                  <div style={{ fontSize: "18px", fontWeight: 700, color: "#334155" }}>
                    {labels.loadingMinutes}
                  </div>
                </div>
              ) : draftMinutes ? (
                <div style={{ display: "grid", gap: "18px" }}>
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
                      {labels.summary}
                    </h3>
                    <textarea
                      value={draftMinutes.summary || ""}
                      onChange={(e) => updateDraftSummary(e.target.value)}
                      readOnly={!editing}
                      rows={8}
                      style={{
                        width: "100%",
                        resize: "vertical",
                        lineHeight: 1.6,
                        fontSize: "15px",
                        borderRadius: "12px",
                        border: "1px solid #cbd5e1",
                        padding: "12px",
                        outline: "none",
                        background: editing ? "#ffffff" : "#f8fafc",
                        color: "#0f172a",
                        boxSizing: "border-box",
                      }}
                    />
                  </div>

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
                      {labels.discussionPoints}
                    </h3>

                    {editing ? (
                      <textarea
                        value={discussionText}
                        onChange={(e) => setDiscussionText(e.target.value)}
                        rows={7}
                        style={{
                          width: "100%",
                          resize: "vertical",
                          lineHeight: 1.8,
                          fontSize: "15px",
                          borderRadius: "12px",
                          border: "1px solid #cbd5e1",
                          padding: "12px",
                          outline: "none",
                          background: "#ffffff",
                          color: "#0f172a",
                          boxSizing: "border-box",
                        }}
                      />
                    ) : Array.isArray(draftMinutes.discussion_points) &&
                      draftMinutes.discussion_points.length > 0 ? (
                      <ul
                        style={{
                          margin: 0,
                          paddingLeft: "20px",
                          lineHeight: 1.8,
                          color: "#334155",
                        }}
                      >
                        {draftMinutes.discussion_points.map((item: string, idx: number) => (
                          <li key={idx}>{item}</li>
                        ))}
                      </ul>
                    ) : (
                      <div style={{ color: "#64748b" }}>{labels.noDiscussion}</div>
                    )}
                  </div>

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
                      {labels.decisions}
                    </h3>

                    {editing ? (
                      <textarea
                        value={decisionsText}
                        onChange={(e) => setDecisionsText(e.target.value)}
                        rows={6}
                        style={{
                          width: "100%",
                          resize: "vertical",
                          lineHeight: 1.8,
                          fontSize: "15px",
                          borderRadius: "12px",
                          border: "1px solid #cbd5e1",
                          padding: "12px",
                          outline: "none",
                          background: "#ffffff",
                          color: "#0f172a",
                          boxSizing: "border-box",
                        }}
                      />
                    ) : Array.isArray(draftMinutes.decisions) &&
                      draftMinutes.decisions.length > 0 ? (
                      <ul
                        style={{
                          margin: 0,
                          paddingLeft: "20px",
                          lineHeight: 1.8,
                          color: "#334155",
                        }}
                      >
                        {draftMinutes.decisions.map((item: string, idx: number) => (
                          <li key={idx}>{item}</li>
                        ))}
                      </ul>
                    ) : (
                      <div style={{ color: "#64748b" }}>{labels.noDecisions}</div>
                    )}
                  </div>

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
                      {labels.actionItems}
                    </h3>

                    {editing ? (
                      <>
                        <div
                          style={{
                            fontSize: "13px",
                            color: "#64748b",
                            marginBottom: "8px",
                            lineHeight: 1.6,
                          }}
                        >
                          {labels.actionFormatHelp}
                        </div>
                        <textarea
                          value={actionItemsText}
                          onChange={(e) => setActionItemsText(e.target.value)}
                          rows={7}
                          style={{
                            width: "100%",
                            resize: "vertical",
                            lineHeight: 1.8,
                            fontSize: "15px",
                            borderRadius: "12px",
                            border: "1px solid #cbd5e1",
                            padding: "12px",
                            outline: "none",
                            background: "#ffffff",
                            color: "#0f172a",
                            boxSizing: "border-box",
                          }}
                        />
                      </>
                    ) : Array.isArray(draftMinutes.action_items) &&
                      draftMinutes.action_items.length > 0 ? (
                      <ul
                        style={{
                          margin: 0,
                          paddingLeft: "20px",
                          lineHeight: 1.8,
                          color: "#334155",
                        }}
                      >
                        {draftMinutes.action_items.map((item: any, idx: number) => (
                          <li key={idx}>
                            <strong>{item.owner_name || "Unassigned"}:</strong>{" "}
                            {item.task || ""}
                            {item.deadline_text
                              ? ` (Deadline: ${item.deadline_text})`
                              : ""}
                          </li>
                        ))}
                      </ul>
                    ) : (
                      <div style={{ color: "#64748b" }}>{labels.noActions}</div>
                    )}
                  </div>

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
                      {labels.nextSteps}
                    </h3>

                    {editing ? (
                      <textarea
                        value={nextStepsText}
                        onChange={(e) => setNextStepsText(e.target.value)}
                        rows={6}
                        style={{
                          width: "100%",
                          resize: "vertical",
                          lineHeight: 1.8,
                          fontSize: "15px",
                          borderRadius: "12px",
                          border: "1px solid #cbd5e1",
                          padding: "12px",
                          outline: "none",
                          background: "#ffffff",
                          color: "#0f172a",
                          boxSizing: "border-box",
                        }}
                      />
                    ) : Array.isArray(draftMinutes.next_steps) &&
                      draftMinutes.next_steps.length > 0 ? (
                      <ul
                        style={{
                          margin: 0,
                          paddingLeft: "20px",
                          lineHeight: 1.8,
                          color: "#334155",
                        }}
                      >
                        {draftMinutes.next_steps.map((item: string, idx: number) => (
                          <li key={idx}>{item}</li>
                        ))}
                      </ul>
                    ) : (
                      <div style={{ color: "#64748b" }}>{labels.noNextSteps}</div>
                    )}
                  </div>
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
                      {labels.minutesUnavailableTitle}
                    </div>
                    <div style={{ color: "#64748b" }}>
                      {labels.minutesUnavailableSubtitle}
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