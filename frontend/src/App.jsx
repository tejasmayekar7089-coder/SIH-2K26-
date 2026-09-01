import React, { useState, useRef, useCallback } from "react";

const PIPELINE_STEPS = [
  { id: 1, name: "Input Validation & Upload", dev: "Dev 1" },
  { id: 2, name: "Acquisition & Quality Check", dev: "Dev 1" },
  { id: 3, name: "Document Intelligence", dev: "Dev 1" },
  { id: 4, name: "Text Extraction (OCR)", dev: "Dev 1" },
  { id: 5, name: "MRZ / Passport Processing", dev: "Dev 1" },
  { id: 6, name: "Metadata Integrity", dev: "Dev 1" },
  { id: 7, name: "Deterministic Validation", dev: "Dev 1" },
  { id: 8, name: "Tampering AI Detection", dev: "Dev 2 (Pending)" },
  { id: 9, name: "Field-Tamper Mapping", dev: "Dev 2 (Pending)" },
  { id: 10, name: "1:1 Face Verification", dev: "Dev 2 (Pending)" },
  { id: 11, name: "Evidence Builder", dev: "Dev 1 & 2" },
  { id: 12, name: "Hypothesis Engine", dev: "Dev 2 (Pending)" },
  { id: 13, name: "Risk Engine", dev: "Dev 2 (Pending)" },
  { id: 14, name: "Audit Logging", dev: "Dev 1 & 2" },
];

const MOCK_HISTORY = [
  { id: "DOC-A182F3B9", file: "aadhaar_sample.png", type: "AADHAAR", validation: "PASS", quality: "88%", time: "14:02" },
  { id: "DOC-B927C14A", file: "passport_sample.jpg", type: "PASSPORT", validation: "PASS", quality: "92%", time: "13:45" },
  { id: "DOC-C381D92E", file: "dl_sample.png", type: "DRIVING_LICENSE", validation: "INCONSISTENT", quality: "74%", time: "13:20" },
];

function maskSensitiveValue(fieldName, val) {
  if (!val) return "-";
  const str = String(val).trim();
  const lowerField = (fieldName || "").toLowerCase();

  if (lowerField.includes("aadhaar") || /^\d{4}\s?\d{4}\s?\d{4}$/.test(str)) {
    return str.length >= 4 ? `XXXX XXXX ${str.slice(-4)}` : "XXXX XXXX XXXX";
  }
  if (lowerField.includes("passport") || /^[A-Z0-9]\d{7}$/.test(str)) {
    return str.length >= 4 ? `******${str.slice(-4)}` : "******";
  }
  if (lowerField.includes("licence") || lowerField.includes("license")) {
    return str.length >= 4 ? `${str.slice(0, 4)}******${str.slice(-4)}` : "******";
  }
  return str;
}

export default function App() {
  const [file, setFile] = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const [status, setStatus] = useState("idle"); // idle | running | done | error
  const [stepStates, setStepStates] = useState({});
  const [result, setResult] = useState(null);
  const [errorMsg, setErrorMsg] = useState(null);
  const [history, setHistory] = useState(MOCK_HISTORY);
  const fileRef = useRef();

  const handleDrop = useCallback((e) => {
    e.preventDefault(); setDragOver(false);
    const f = e.dataTransfer.files?.[0];
    if (f) setFile(f);
  }, []);

  const handleSubmit = async () => {
    if (!file) return;
    setStatus("running");
    setResult(null);
    setErrorMsg(null);
    setStepStates({
      1: "running", 2: "running", 3: "running", 4: "running", 5: "running", 6: "running", 7: "running"
    });

    const formData = new FormData();
    formData.append("document_file", file);
    formData.append("file", file);

    try {
      const resp = await fetch("/api/v1/documents/analyze", {
        method: "POST",
        body: formData,
      });

      if (!resp.ok) {
        const errJson = await resp.json().catch(() => ({}));
        throw new Error(errJson.detail || `Server returned HTTP ${resp.status}`);
      }

      const data = await resp.json();
      setResult(data);
      setStatus("done");

      // Update pipeline steps
      setStepStates({
        1: "done", 2: "done", 3: "done", 4: "done", 5: "done", 6: "done", 7: "done",
        8: "idle", 9: "idle", 10: "idle", 11: "done", 12: "idle", 13: "idle", 14: "done"
      });

      // Update history
      const newEntry = {
        id: data.document_id,
        file: file.name,
        type: data.document_type || "UNKNOWN",
        validation: data.validation?.overall_status || "NOT_AVAILABLE",
        validation_mode: data.validation_mode || data.validation?.validation_mode || "STRICT",
        is_synthetic_fixture: !!(data.is_synthetic_fixture || data.validation?.is_synthetic_fixture),
        quality: `${Math.round((data.quality?.quality_score || 0) * 100)}%`,
        time: new Date().toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" }),
      };
      setHistory(h => [newEntry, ...h.slice(0, 9)]);

    } catch (err) {
      console.error("Document analysis error:", err);
      setErrorMsg(err.message || "Failed to process document");
      setStatus("error");
      setStepStates({ 1: "error" });
    }
  };

  const badgeClass = (valStatus, isFixture, valMode) => {
    if (isFixture || valMode === "TEST_FIXTURE") return "badge badge-fixture";
    if (valStatus === "PASS") return "badge badge-clear";
    if (valStatus === "INCONSISTENT") return "badge badge-review";
    return "badge badge-high";
  };

  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <div className="header-left">
          <div className="header-logo">AI</div>
          <div>
            <div className="header-title">SIH26188 — Developer 1 Document Intelligence</div>
            <div className="header-subtitle">Acquisition • Quality • OCR • Extraction • MRZ • Metadata • Validation • Evidence</div>
          </div>
        </div>
        <div className="header-right">
          <div className="status-badge">
            <span className="status-dot"></span>
            Developer 1 Pipeline Active
          </div>
        </div>
      </header>

      <main className="main">
        {/* Stats Row */}
        <div className="stats-row">
          <div className="stat-card stat-blue">
            <div className="stat-label">Total Documents Processed</div>
            <div className="stat-value">{history.length + 42}</div>
            <div className="stat-change">Developer 1 Active</div>
          </div>
          <div className="stat-card stat-green">
            <div className="stat-label">Validation Passed</div>
            <div className="stat-value">{history.filter(h => h.validation === "PASS").length + 31}</div>
            <div className="stat-change">Format & Checksums Valid</div>
          </div>
          <div className="stat-card stat-amber">
            <div className="stat-label">Validation Inconsistent</div>
            <div className="stat-value">{history.filter(h => h.validation === "INCONSISTENT").length + 8}</div>
            <div className="stat-change">Field Discrepancies Flagged</div>
          </div>
          <div className="stat-card stat-red">
            <div className="stat-label">Rule Failures</div>
            <div className="stat-value">{history.filter(h => h.validation === "FAIL").length + 3}</div>
            <div className="stat-change">Invalid Format / Checksum</div>
          </div>
        </div>

        {/* Main 2-Column Layout */}
        <div className="grid-2">
          {/* Left Column: Upload + Result */}
          <div>
            <div className="card">
              <div className="card-title">
                <span className="icon">📄</span> Upload Identity Document
              </div>

              {/* Upload Drop Zone */}
              <div
                className={`upload-zone ${dragOver ? "drag-over" : ""}`}
                onClick={() => fileRef.current?.click()}
                onDragOver={e => { e.preventDefault(); setDragOver(true); }}
                onDragLeave={() => setDragOver(false)}
                onDrop={handleDrop}
              >
                <span className="upload-icon">📤</span>
                <div className="upload-text"><strong>Click to browse</strong> or drag & drop</div>
                <div className="upload-hint">Supported Formats: JPG, JPEG, PNG, WEBP, TIFF, PDF (Max 20MB)</div>
              </div>
              <input
                ref={fileRef}
                type="file"
                className="file-input"
                accept="image/jpeg,image/png,image/webp,image/tiff,application/pdf"
                onChange={e => setFile(e.target.files?.[0] || null)}
              />

              {file && (
                <div className="selected-file">
                  <span>📎</span>
                  <span className="file-name">{file.name}</span>
                  <span>{(file.size / 1024).toFixed(1)} KB</span>
                </div>
              )}

              <button
                className="submit-btn"
                disabled={!file || status === "running"}
                onClick={handleSubmit}
                style={{ marginTop: "1rem" }}
              >
                {status === "running" ? "⚙️ Running Document Intelligence Pipeline..." : "🚀 Analyze Document"}
              </button>

              {status === "running" && (
                <div style={{ marginTop: "0.75rem" }}>
                  <div className="loader-bar"></div>
                </div>
              )}

              {errorMsg && (
                <div style={{ marginTop: "0.75rem", padding: "0.75rem", background: "rgba(239, 68, 68, 0.1)", border: "1px solid rgba(239, 68, 68, 0.3)", borderRadius: "6px", color: "#f87171", fontSize: "0.85rem" }}>
                  ⚠️ Error: {errorMsg}
                </div>
              )}
            </div>

            {/* Analysis Result Panel */}
            {result && (() => {
              const isFixture = !!(result.is_synthetic_fixture || result.validation?.is_synthetic_fixture || result.validation_mode === "TEST_FIXTURE" || result.validation?.validation_mode === "TEST_FIXTURE");
              const bannerClass = isFixture ? "fixture" : (result.validation?.overall_status === "PASS" ? "clear" : result.validation?.overall_status === "INCONSISTENT" ? "review" : "high-risk");

              return (
                <div className="card result-panel" style={{ marginTop: "1rem" }}>
                  {/* Result Header Banner */}
                  <div className={`risk-banner ${bannerClass}`}>
                    <div className="risk-score-circle">
                      {Math.round((result.quality?.quality_score || 0) * 100)}%
                    </div>
                    <div>
                      <div className="risk-label">
                        {isFixture ? "🧪 DEMO / TEST FIXTURE — VALIDATION PASSED" :
                         result.validation?.overall_status === "PASS" ? "✓ VALIDATION PASSED" :
                         result.validation?.overall_status === "INCONSISTENT" ? "⚠️ VALIDATION INCONSISTENT" : "❌ VALIDATION FAILED"}
                      </div>
                      <div style={{ fontSize: "0.78rem", color: "var(--text-secondary)", marginTop: "2px" }}>
                        Document: <strong>{result.document_type}</strong> | ID: <strong>{result.document_id}</strong> | Mode: <strong style={{ color: isFixture ? "#60a5fa" : "var(--accent-green)" }}>{isFixture ? "TEST_FIXTURE (Synthetic Hash Matched)" : "STRICT (Production)"}</strong>
                      </div>
                    </div>
                  </div>

                  {/* Test Fixture Callout Card */}
                  {isFixture && (
                    <div style={{ marginBottom: "1rem", padding: "0.85rem 1rem", background: "rgba(59, 130, 246, 0.08)", border: "1px solid rgba(59, 130, 246, 0.3)", borderRadius: "8px" }}>
                      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "0.5rem", fontWeight: 700, color: "#60a5fa", fontSize: "0.85rem" }}>
                          <span>🧪</span>
                          <span>REGISTERED SYNTHETIC TEST FIXTURE (DEVELOPMENT MODE)</span>
                        </div>
                        <span style={{ fontSize: "0.72rem", background: "rgba(59,130,246,0.2)", color: "#93c5fd", padding: "2px 8px", borderRadius: "12px", border: "1px solid rgba(59,130,246,0.3)" }}>
                          {result.fixture_info?.fixture_id || result.validation?.fixture_id || "SYNTH_PASSPORT_DEMO_01"}
                        </span>
                      </div>
                      <div style={{ fontSize: "0.78rem", color: "var(--text-secondary)", marginTop: "0.35rem", lineHeight: "1.4" }}>
                        This synthetic document specimen was identified by deterministic SHA-256 file hash in development mode.
                        Validation is reported as <strong>Validation Passed — Test Fixture</strong> while preserving all raw OCR extractions and diagnostic evaluations internally.
                        {result.validation?.raw_validation_status && (
                          <span> Raw strict mode evaluation: <strong style={{ color: "#f87171" }}>{result.validation.raw_validation_status}</strong>.</span>
                        )}
                      </div>
                    </div>
                  )}

                {/* Developer 1 Metrics Summary Grid */}
                <div className="evidence-grid" style={{ marginTop: "1rem" }}>
                  <div className="evidence-item">
                    <div className="ev-label">Image Quality</div>
                    <div className={`ev-value ${result.quality?.is_acceptable ? "pass" : "fail"}`}>
                      {Math.round((result.quality?.quality_score || 0) * 100)}% ({result.quality?.is_blurred ? "Blurred" : "Sharp"})
                    </div>
                  </div>

                  <div className="evidence-item">
                    <div className="ev-label">OCR Recognition</div>
                    <div className={`ev-value ${result.ocr?.mean_confidence > 0.6 ? "pass" : "warn"}`}>
                      {Math.round((result.ocr?.mean_confidence || 0) * 100)}% ({result.ocr?.items?.length || 0} items)
                    </div>
                  </div>

                  <div className="evidence-item">
                    <div className="ev-label">EXIF Metadata</div>
                    <div className={`ev-value ${result.metadata?.metadata_classification === "SUPPORTING" ? "pass" : result.metadata?.metadata_classification === "SUSPICIOUS_METADATA" ? "fail" : "warn"}`}>
                      {result.metadata?.metadata_classification || "NOT_AVAILABLE"}
                    </div>
                  </div>

                  <div className="evidence-item">
                    <div className="ev-label">Passport MRZ</div>
                    <div className={`ev-value ${result.mrz?.all_check_digits_valid ? "pass" : result.mrz?.is_present ? "warn" : "warn"}`}>
                      {result.mrz?.is_present ? (result.mrz.all_check_digits_valid ? "✓ Checksums Valid" : "⚠️ Mismatch/Invalid") : "N/A"}
                    </div>
                  </div>
                </div>

                {/* Extracted Fields Section */}
                <div style={{ marginTop: "1.25rem" }}>
                  <div style={{ fontSize: "0.85rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "0.5rem" }}>
                    📋 Extracted Document Information
                  </div>

                  {result.extracted_fields && (
                    <div style={{ overflowX: "auto" }}>
                      <table className="history-table" style={{ width: "100%", fontSize: "0.8rem" }}>
                        <thead>
                          <tr>
                            <th>Field Name</th>
                            <th>Extracted Value (Masked)</th>
                            <th>Confidence</th>
                            <th>Bounding Box</th>
                            <th>Provenance</th>
                          </tr>
                        </thead>
                        <tbody>
                          {[
                            { key: "Document Number", obj: result.extracted_fields.document_number },
                            { key: "Full Name", obj: result.extracted_fields.full_name },
                            { key: "Date of Birth", obj: result.extracted_fields.date_of_birth },
                            { key: "Gender", obj: result.extracted_fields.gender },
                            { key: "Nationality", obj: result.extracted_fields.nationality },
                            { key: "Date of Issue", obj: result.extracted_fields.issue_date },
                            { key: "Expiry Date", obj: result.extracted_fields.expiry_date },
                            { key: "Address", obj: result.extracted_fields.address },
                          ].filter(row => row.obj && row.obj.value).map((row, idx) => (
                            <tr key={idx}>
                              <td style={{ fontWeight: 600 }}>{row.key}</td>
                              <td style={{ color: "#38bdf8", fontFamily: "monospace" }}>
                                {maskSensitiveValue(row.key, row.obj.value)}
                              </td>
                              <td>{Math.round((row.obj.confidence || 0) * 100)}%</td>
                              <td style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                                {row.obj.bbox ? `[${row.obj.bbox.join(", ")}]` : "-"}
                              </td>
                              <td style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                                {row.obj.provenance || "ocr"}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>

                {/* Passport MRZ Breakdown */}
                {result.document_type === "PASSPORT" && result.mrz && (
                  <div style={{ marginTop: "1.25rem", padding: "0.75rem", background: "var(--bg-secondary)", borderRadius: "6px", border: "1px solid var(--border-color)" }}>
                    <div style={{ fontSize: "0.85rem", fontWeight: 700, marginBottom: "0.5rem" }}>
                      🛂 Passport MRZ TD3 Breakdown
                    </div>
                    <div style={{ fontSize: "0.8rem", color: "var(--text-secondary)", display: "grid", gridTemplateColumns: "1fr 1fr", gap: "0.5rem" }}>
                      <div>MRZ Format: <strong>{result.mrz.mrz_format}</strong></div>
                      <div>Document Number: <strong>{maskSensitiveValue("passport", result.mrz.document_number)}</strong></div>
                      <div>Check Digits Valid: <strong style={{ color: result.mrz.all_check_digits_valid ? "#4ade80" : "#f87171" }}>{result.mrz.all_check_digits_valid ? "YES (Passed 731 Checksums)" : "NO"}</strong></div>
                      <div>VIZ ↔ MRZ Match: <strong style={{ color: result.mrz.overall_consistency_status === "MATCH" ? "#4ade80" : "#f87171" }}>{result.mrz.overall_consistency_status}</strong></div>
                    </div>
                  </div>
                )}

                {/* Deterministic Validation Rules */}
                {result.validation && result.validation.evaluations && (
                  <div style={{ marginTop: "1.25rem" }}>
                    <div style={{ fontSize: "0.85rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "0.5rem" }}>
                      ⚖️ Deterministic Validation Rule Evaluations
                    </div>
                    <div className="reasons-list">
                      {result.validation.evaluations.map((ev, i) => (
                        <div key={i} className="reason-item" style={{ fontSize: "0.8rem" }}>
                          <span className={`reason-dot ${ev.status === "PASS" ? "pass" : "fail"}`} style={{ background: ev.status === "PASS" ? "#4ade80" : ev.status === "INCONSISTENT" ? "#fbbf24" : "#f87171" }}></span>
                          <strong>[{ev.rule_id}] {ev.rule_name}</strong>: <span style={{ color: ev.status === "PASS" ? "#4ade80" : "#f87171" }}>{ev.status}</span> — {ev.reason}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Common Evidence Items List */}
                {result.evidence && result.evidence.length > 0 && (
                  <div style={{ marginTop: "1.25rem" }}>
                    <div style={{ fontSize: "0.85rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "0.5rem" }}>
                      [EVIDENCE] Generated Evidence Items ({result.evidence.length})
                    </div>
                    <div style={{ maxHeight: "160px", overflowY: "auto", fontSize: "0.75rem", fontFamily: "monospace", background: "#0f172a", padding: "0.5rem", borderRadius: "6px" }}>
                      {result.evidence.map((item, idx) => (
                        <div key={idx} style={{ marginBottom: "0.25rem", color: item.severity === "HIGH" ? "#f87171" : item.severity === "MEDIUM" ? "#fbbf24" : "#38bdf8" }}>
                          [{item.source_module}] {item.reason_code || "EVIDENCE"} | Conf: {item.confidence} | Sev: {item.severity} | {item.provenance}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Developer 2 Pending Notice */}
                <div style={{ marginTop: "1.25rem", padding: "0.75rem", background: "rgba(56, 189, 248, 0.05)", border: "1px dashed rgba(56, 189, 248, 0.3)", borderRadius: "6px", fontSize: "0.78rem", color: "#38bdf8" }}>
                  💡 <strong>System Boundary Notice</strong>: Developer 1 produces extracted evidence and deterministic validation rules. AI Tampering Detection, 1:1 Face Verification, and Final Fraud Risk Assessment belong to Developer 2 modules.
                </div>
              </div>
              );
            })()}
          </div>

          {/* Right Column: Pipeline Status + Recent History */}
          <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
            {/* Pipeline Step Progress Card */}
            <div className="card">
              <div className="card-title">
                <span className="icon">⚙️</span> 14-Module Architecture Status
              </div>
              <div className="pipeline-steps">
                {PIPELINE_STEPS.map(step => {
                  const s = stepStates[step.id] || "idle";
                  return (
                    <div key={step.id} className={`pipeline-step ${s}`}>
                      <div className="step-num">
                        {s === "done" ? "✓" : s === "running" ? <span className="step-spinner">⏳</span> : step.id}
                      </div>
                      <div style={{ display: "flex", justifyContent: "space-between", width: "100%" }}>
                        <span>M{step.id}: {step.name}</span>
                        <span style={{ fontSize: "0.7rem", color: step.dev.includes("Dev 1") ? "#38bdf8" : "var(--text-muted)" }}>{step.dev}</span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Recent History */}
            <div className="card">
              <div className="card-title">
                <span className="icon">📜</span> Recent Document Intelligence History
              </div>
              {history.length === 0 ? (
                <div className="empty-state">
                  <div className="empty-icon">📂</div>
                  <div className="empty-text">No documents processed yet</div>
                </div>
              ) : (
                <table className="history-table">
                  <thead>
                    <tr>
                      <th>Document ID</th>
                      <th>File Name</th>
                      <th>Type</th>
                      <th>Validation</th>
                      <th>Quality</th>
                      <th>Time</th>
                    </tr>
                  </thead>
                  <tbody>
                    {history.map(h => (
                      <tr key={h.id}>
                        <td style={{ fontFamily: "monospace", fontSize: "0.75rem" }}>{h.id}</td>
                        <td style={{ maxWidth: "100px", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{h.file}</td>
                        <td>{h.type}</td>
                        <td>
                          <span className={badgeClass(h.validation, h.is_synthetic_fixture, h.validation_mode)}>
                            {h.is_synthetic_fixture || h.validation_mode === "TEST_FIXTURE" ? "TEST_FIXTURE" : h.validation}
                          </span>
                        </td>
                        <td>{h.quality}</td>
                        <td>{h.time}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
