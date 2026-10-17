import { useEffect } from "react";
import { getRecords, createManualRecord } from "./api";
import { useMemo, useRef, useState } from "react";

type Page =
  | "Overview"
  | "Medical Records"
  | "Report Analysis"
  | "Integrity Checks"
  | "Laboratory Verification"
  | "Medicine Verification"
  | "Care Gaps"
  | "Consultation Summary"
  | "Audit Trail"
  | "Settings";

type RecordItem = {
  id: string;
  name: string;
  date: string;
  lab: string;
  value: string;
  unit: string;
  range: string;
  status: string;
  source: string;
};

const nav: { name: Page; icon: string }[] = [
  { name: "Overview", icon: "grid" },
  { name: "Medical Records", icon: "file" },
  { name: "Report Analysis", icon: "chart" },
  { name: "Integrity Checks", icon: "shield" },
  { name: "Laboratory Verification", icon: "flask" },
  { name: "Medicine Verification", icon: "pill" },
  { name: "Care Gaps", icon: "calendar" },
  { name: "Consultation Summary", icon: "clipboard" },
  { name: "Audit Trail", icon: "link" },
  { name: "Settings", icon: "settings" },
];

const initialRecords: RecordItem[] = [
  { id: "SR-1048", name: "Fasting Plasma Glucose", date: "18 Oct 2025", lab: "Aster Diagnostics, Pune", value: "102", unit: "mg/dL", range: "70–99 mg/dL", status: "Needs review", source: "PDF Extracted" },
  { id: "SR-1043", name: "Complete Blood Count", date: "08 Sep 2025", lab: "Metropolis Healthcare, Pune", value: "13.6", unit: "g/dL Hb", range: "12.0–15.5 g/dL", status: "Reviewed", source: "PDF Extracted" },
  { id: "SR-1031", name: "Fasting Plasma Glucose", date: "12 Jul 2025", lab: "Aster Diagnostics, Pune", value: "96", unit: "mg/dL", range: "70–99 mg/dL", status: "Verified", source: "Online Source" },
  { id: "SR-1022", name: "Lipid Profile", date: "14 Apr 2025", lab: "CarePlus Labs, Mumbai", value: "174", unit: "mg/dL total", range: "<200 mg/dL", status: "Reviewed", source: "Scanned Image" },
  { id: "SR-1015", name: "Complete Blood Count", date: "04 Feb 2025", lab: "Metropolis Healthcare, Pune", value: "13.2", unit: "g/dL Hb", range: "12.0–15.5 g/dL", status: "Reviewed", source: "Manual" },
];

const findings = [
  { id: "DUP-002", title: "Conflicting report identifiers", severity: "High-Priority Review", report: "SR-1048", when: "Today, 09:42", evidence: "Report ID LAB-8821 appears on two files with different glucose values.", action: "Compare both originals with the issuing laboratory." },
  { id: "OCR-014", title: "Low-confidence OCR extraction", severity: "Review", report: "SR-1022", when: "Today, 09:41", evidence: "Collection date extracted at 67% confidence from page 1, upper-right region.", action: "Review the source image and confirm the date." },
  { id: "META-008", title: "Missing collection time", severity: "Info", report: "SR-1043", when: "08 Sep, 14:08", evidence: "Report date is present; collection time was not found in the available file.", action: "Add metadata if it is available on another page." },
  { id: "UNIT-003", title: "Unit compatibility needs review", severity: "Review", report: "SR-1031", when: "12 Jul, 11:24", evidence: "One historical glucose value uses mmol/L. A supported contextual conversion is available.", action: "Confirm analyte context before comparing converted values." },
];

const Icon = ({ name, size = 18 }: { name: string; size?: number }) => {
  const paths: Record<string, React.ReactNode> = {
    grid: <><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></>,
    file: <><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><path d="M14 2v6h6M8 13h8M8 17h5"/></>,
    chart: <><path d="M3 3v18h18"/><path d="m7 16 4-5 4 3 5-7"/></>,
    shield: <><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10"/><path d="m9 12 2 2 4-4"/></>,
    flask: <><path d="M9 3h6M10 3v6l-5 9a2 2 0 0 0 2 3h10a2 2 0 0 0 2-3l-5-9V3"/><path d="M8 15h8"/></>,
    pill: <><path d="m10.5 20.5-7-7a4.95 4.95 0 0 1 7-7l7 7a4.95 4.95 0 0 1-7 7Z"/><path d="m8.5 11.5 7-7"/></>,
    calendar: <><rect x="3" y="5" width="18" height="16" rx="2"/><path d="M16 3v4M8 3v4M3 11h18"/></>,
    clipboard: <><rect x="5" y="4" width="14" height="18" rx="2"/><path d="M9 4V2h6v2M9 10h6M9 14h6M9 18h4"/></>,
    link: <><path d="M10 13a5 5 0 0 0 7.5.5l2-2a5 5 0 0 0-7-7l-1.2 1.2"/><path d="M14 11a5 5 0 0 0-7.5-.5l-2 2a5 5 0 0 0 7 7l1.2-1.2"/></>,
    settings: <><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.7 1.7 0 0 0 .3 1.9l.1.1-2.8 2.8-.1-.1a1.7 1.7 0 0 0-1.9-.3 1.7 1.7 0 0 0-1 1.6v.2h-4V21a1.7 1.7 0 0 0-1-1.6 1.7 1.7 0 0 0-1.9.3l-.1.1L4.2 17l.1-.1a1.7 1.7 0 0 0 .3-1.9A1.7 1.7 0 0 0 3 14H2.8v-4H3a1.7 1.7 0 0 0 1.6-1 1.7 1.7 0 0 0-.3-1.9L4.2 7 7 4.2l.1.1a1.7 1.7 0 0 0 1.9.3A1.7 1.7 0 0 0 10 3V2.8h4V3a1.7 1.7 0 0 0 1 1.6 1.7 1.7 0 0 0 1.9-.3l.1-.1L19.8 7l-.1.1a1.7 1.7 0 0 0-.3 1.9 1.7 1.7 0 0 0 1.6 1h.2v4H21a1.7 1.7 0 0 0-1.6 1Z"/></>,
    search: <><circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/></>,
    bell: <><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4"/></>,
    plus: <path d="M12 5v14M5 12h14"/>,
    upload: <><path d="M12 16V4M7 9l5-5 5 5"/><path d="M4 15v5h16v-5"/></>,
    check: <path d="m5 12 4 4L19 6"/>,
    alert: <><path d="M10.3 3.7 2.2 18a2 2 0 0 0 1.8 3h16a2 2 0 0 0 1.8-3L13.7 3.7a2 2 0 0 0-3.4 0Z"/><path d="M12 9v4M12 17h.01"/></>,
    eye: <><path d="M2 12s3.5-6 10-6 10 6 10 6-3.5 6-10 6S2 12 2 12"/><circle cx="12" cy="12" r="2.5"/></>,
    menu: <path d="M4 7h16M4 12h16M4 17h16"/>,
    x: <path d="m6 6 12 12M18 6 6 18"/>,
    arrow: <path d="m9 18 6-6-6-6"/>,
    download: <><path d="M12 3v12M7 10l5 5 5-5"/><path d="M4 19h16"/></>,
  };
  return <svg className="icon" width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name] || paths.file}</svg>;
};

const Badge = ({ children, tone }: { children: React.ReactNode; tone?: string }) => (
  <span className={`badge ${tone || ""}`}><span className="badge-dot"/>{children}</span>
);

const Button = ({ children, variant = "primary", icon, onClick, type = "button", disabled = false }: { children: React.ReactNode; variant?: string; icon?: string; onClick?: () => void; type?: "button" | "submit"; disabled?: boolean }) => (
  <button type={type} className={`btn ${variant}`} onClick={onClick} disabled={disabled}>{icon && <Icon name={icon} size={16}/>} {children}</button>
);

const Card = ({ children, className = "" }: { children: React.ReactNode; className?: string }) => <section className={`card ${className}`}>{children}</section>;

const SectionTitle = ({ title, subtitle, action }: { title: string; subtitle?: string; action?: React.ReactNode }) => (
  <div className="section-title"><div><h2>{title}</h2>{subtitle && <p>{subtitle}</p>}</div>{action}</div>
);

const TrendChart = ({ kind = "glucose" }: { kind?: "glucose" | "haemoglobin" }) => {
  const glucose = [{ x: 30, y: 116, v: "89" }, { x: 125, y: 101, v: "93" }, { x: 218, y: 93, v: "96" }, { x: 315, y: 72, v: "102" }, { x: 410, y: 80, v: "100" }];
  const hb = [{ x: 30, y: 103, v: "13.2" }, { x: 125, y: 90, v: "13.4" }, { x: 218, y: 95, v: "13.3" }, { x: 315, y: 82, v: "13.6" }, { x: 410, y: 88, v: "13.5" }];
  const data = kind === "glucose" ? glucose : hb;
  const points = data.map((p) => `${p.x},${p.y}`).join(" ");
  return <div className="chart-wrap">
    <div className="chart-legend"><span><i className="legend-line"/>Recorded value</span><span><i className="legend-range"/>Lab reference range</span></div>
    <svg className="chart" viewBox="0 0 440 160" role="img" aria-label={`${kind} values over time`}>
      <rect x="30" y={kind === "glucose" ? 75 : 45} width="380" height={kind === "glucose" ? 46 : 82} rx="6" className="range"/>
      {[40, 80, 120].map(y => <line key={y} x1="30" y1={y} x2="410" y2={y} className="gridline"/>)}
      <polyline points={points} className="trend"/>
      {data.map((p, i) => <g key={i} className="point"><circle cx={p.x} cy={p.y} r="5"/><title>{`${p.v} ${kind === "glucose" ? "mg/dL" : "g/dL"} · ${["Feb", "Apr", "Jul", "Sep", "Oct"][i]} 2025`}</title></g>)}
      {["Feb", "Apr", "Jul", "Sep", "Oct"].map((m, i) => <text key={m} x={data[i].x} y="151" textAnchor="middle">{m}</text>)}
    </svg>
  </div>;
};

function Header({ page, onMenu, onAdd }: { page: Page; onMenu: () => void; onAdd: () => void }) {
  const [search, setSearch] = useState("");
  const [notify, setNotify] = useState(false);
  return <header className="topbar">
    <button className="icon-btn mobile-menu" onClick={onMenu} aria-label="Toggle menu"><Icon name="menu"/></button>
    <div className="page-heading"><div className="breadcrumb">Workspace <span>/</span> {page}</div><h1>{page}</h1></div>
    <div className="top-actions">
      <label className="global-search"><Icon name="search" size={17}/><input value={search} onChange={e => setSearch(e.target.value)} placeholder="Search records, reports, IDs…"/>{search && <span className="search-hint">Searching “{search}”</span>}</label>
      <div className="notify-wrap"><button className="icon-btn" onClick={() => setNotify(!notify)} aria-label="Notifications"><Icon name="bell"/><i/></button>{notify && <div className="popover"><b>2 items need review</b><p>Conflicting report identifier detected.</p><p>Care-plan task due in 8 days.</p></div>}</div>
      <button className="icon-btn help" onClick={() => alert("Help centre: Demo guidance is available for every verification workflow.")}>?</button>
      <div className="profile"><span>AN</span><div><b>Aarav N.</b><small>Patient workspace</small></div></div>
      <Button icon="plus" onClick={onAdd}>Add Record</Button>
    </div>
  </header>;
}

function Sidebar({ page, setPage, open, collapse, setCollapse }: { page: Page; setPage: (p: Page) => void; open: boolean; collapse: boolean; setCollapse: (v: boolean) => void }) {
  return <aside className={`sidebar ${open ? "open" : ""} ${collapse ? "collapsed" : ""}`}>
    <div className="brand"><div className="brand-mark"><Icon name="shield"/></div><div><strong>SehatSnap</strong><small>INTEGRITY</small></div></div>
    <nav>{nav.map(n => <button key={n.name} className={page === n.name ? "active" : ""} onClick={() => setPage(n.name)} title={n.name}><Icon name={n.icon}/><span>{n.name}</span>{page === n.name && <i/>}</button>)}</nav>
    <div className="sidebar-bottom">
      <div className="privacy-mini"><Icon name="shield" size={16}/><span><b>Private workspace</b><small>Synthetic demo data</small></span></div>
      <button className="collapse-btn" onClick={() => setCollapse(!collapse)}><Icon name="arrow"/><span>Collapse sidebar</span></button>
    </div>
  </aside>;
}

function Overview({ setPage, openUpload }: { setPage: (p: Page) => void; openUpload: () => void }) {
  const [measure, setMeasure] = useState<"glucose" | "haemoglobin">("glucose");
  return <div className="page">
    <div className="hero">
      <div><Badge tone="verified">Health data workspace</Badge><h2>Your Health Records, <em>Clearly Verified</em></h2><p>Organise reports, understand their provenance, and focus attention on information that needs review.</p></div>
      <div className="hero-score"><div className="score-ring"><strong>86</strong><small>/100</small></div><div><b>Record integrity score</b><span>Good coverage</span><small>Based on 12 deterministic checks</small></div></div>
    </div>
    <div className="metrics">
      {[
        ["28", "Total medical reports", "+3 this month", "file"],
        ["24", "Reports reviewed", "86% of all records", "check"],
        ["4", "Items requiring review", "1 high priority", "alert"],
        ["7", "Verified lab checks", "Official sources", "flask"],
        ["2", "Pending care-plan tasks", "Next due 02 Nov", "calendar"],
      ].map((m, i) => <Card key={m[1]}><div className={`metric-icon m${i}`}><Icon name={m[3]}/></div><div className="metric-value">{m[0]}</div><b>{m[1]}</b><small>{m[2]}</small></Card>)}
    </div>
    <div className="quick-panel"><div><span className="eyebrow">QUICK ACTIONS</span><h3>What would you like to do?</h3></div>
      <div className="quick-actions">
        <button onClick={openUpload}><Icon name="upload"/><span>Upload report<small>PDF or image</small></span></button>
        <button onClick={() => setPage("Medical Records")}><Icon name="plus"/><span>Enter test<small>Add manually</small></span></button>
        <button onClick={() => setPage("Laboratory Verification")}><Icon name="flask"/><span>Verify laboratory<small>Check official source</small></span></button>
        <button onClick={() => setPage("Medicine Verification")}><Icon name="pill"/><span>Verify medicine<small>Compare label data</small></span></button>
        <button onClick={() => setPage("Consultation Summary")}><Icon name="download"/><span>Consultation PDF<small>Build summary</small></span></button>
      </div>
    </div>
    <div className="dashboard-grid">
      <Card className="span-2"><SectionTitle title="Measurement trends" subtitle="Only comparable values with compatible units are plotted." action={<div className="segmented"><button className={measure === "glucose" ? "active" : ""} onClick={() => setMeasure("glucose")}>Glucose</button><button className={measure === "haemoglobin" ? "active" : ""} onClick={() => setMeasure("haemoglobin")}>Haemoglobin</button></div>}/><TrendChart kind={measure}/><div className="chart-footer"><span>5 comparable measurements</span><span>Original units preserved · Hover points for source values</span></div></Card>
      <Card><SectionTitle title="Integrity alerts" subtitle="Evidence that needs attention" action={<button className="text-btn" onClick={() => setPage("Integrity Checks")}>View all <Icon name="arrow" size={14}/></button>}/><div className="alert-list">{findings.slice(0,3).map(f => <button key={f.id} onClick={() => setPage("Integrity Checks")}><span className={`alert-icon ${f.severity.startsWith("High") ? "danger" : f.severity === "Info" ? "info" : "warn"}`}><Icon name="alert" size={16}/></span><span><b>{f.title}</b><small>{f.report} · {f.when}</small></span><Icon name="arrow" size={15}/></button>)}</div></Card>
      <Card className="span-2"><SectionTitle title="Health record timeline" subtitle="Recent reports across your available history" action={<button className="text-btn" onClick={() => setPage("Medical Records")}>All records <Icon name="arrow" size={14}/></button>}/><div className="timeline">{initialRecords.slice(0,4).map((r, i) => <div key={r.id} className="timeline-row"><div className="date"><b>{r.date.split(" ")[0]}</b><span>{r.date.split(" ").slice(1).join(" ")}</span></div><i className={i === 0 ? "current" : ""}/><div className="record-main"><b>{r.name}</b><span>{r.lab} · {r.source}</span></div><div className="record-value"><b>{r.value}</b><span>{r.unit}</span></div><Badge tone={r.status === "Needs review" ? "review" : "verified"}>{r.status}</Badge></div>)}</div></Card>
      <Card><SectionTitle title="Care plan" subtitle="From documented plans only" action={<button className="text-btn" onClick={() => setPage("Care Gaps")}>Manage <Icon name="arrow" size={14}/></button>}/><div className="care-mini"><div><span className="due">DUE 02 NOV</span><b>Repeat fasting glucose</b><p>No matching test record found in the available history.</p><Badge tone="review">Needs Review</Badge></div><div><span className="due neutral">18 NOV</span><b>Review lipid profile</b><p>Appointment recorded in care plan.</p><Badge tone="info">Scheduled</Badge></div></div></Card>
    </div>
  </div>;
}

function MedicalRecords({ records, setRecords, recordsError, openUpload }: {
  records: RecordItem[];
  setRecords: React.Dispatch<React.SetStateAction<RecordItem[]>>;
  recordsError: string;
  openUpload: () => void;
}) {
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("All statuses");
  const [manual, setManual] = useState(false);
  const visible = records.filter(r => `${r.name} ${r.lab} ${r.id}`.toLowerCase().includes(query.toLowerCase()) && (status === "All statuses" || r.status === status));
  
const [saving, setSaving] = useState(false);
const [manualError, setManualError] = useState("");

const addManual = async (e: React.FormEvent<HTMLFormElement>) => {
  e.preventDefault();

  const form = e.currentTarget;
  const fd = new FormData(form);

  setSaving(true);
  setManualError("");

  try {
    const created = await createManualRecord({
      test: String(fd.get("test") ?? ""),
      value: String(fd.get("value") ?? ""),
      unit: String(fd.get("unit") ?? ""),
      lab: String(fd.get("lab") ?? ""),
    });

    setRecords((previous) => [created, ...previous]);
    setManual(false);
  } catch (error) {
    setManualError(
      error instanceof Error
        ? error.message
        : "Record save nahi ho paya."
    );
  } finally {
    setSaving(false);
  }
};

  return <div className="page"><PageIntro title="Medical records" text="Search, review, and add reports while preserving their original source and correction history." actions={<><Button variant="secondary" onClick={() => setManual(true)} icon="plus">Enter manually</Button><Button onClick={openUpload} icon="upload">Upload report</Button></>}/>
    
<Card>
  {recordsError && (
    <p style={{ color: "#dc2626", padding: "12px 16px" }}>
      Failed to load records: {recordsError}
    </p>
  )}
  <div className="table-tools">
<label className="search-field"><Icon name="search"/><input value={query} onChange={e => setQuery(e.target.value)} placeholder="Search records, laboratories, report IDs…"/></label><select value={status} onChange={e => setStatus(e.target.value)}><option>All statuses</option><option>Reviewed</option><option>Needs review</option><option>Verified</option></select><select><option>Newest first</option><option>Oldest first</option></select><span className="result-count">{visible.length} records</span></div><RecordTable records={visible}/></Card>
    {manual && <Modal title="Enter test information manually" onClose={() => setManual(false)}><form onSubmit={addManual} className="form-grid">
      {manualError && (
  <p style={{ color: "#dc2626" }}>{manualError}</p>
)}<Field label="Test name" name="test" placeholder="e.g. Thyroid Stimulating Hormone" required/><Field label="Result value" name="value" placeholder="Enter value" required/><Field label="Unit" name="unit" placeholder="e.g. mIU/L" required/><Field label="Laboratory name" name="lab" placeholder="Issuing laboratory" required/><div className="modal-actions full"><Button variant="ghost" onClick={() => setManual(false)}>Cancel</Button><Button type="submit" disabled={saving}>
  {saving ? "Saving..." : "Add confirmed record"}
</Button></div></form></Modal>}
  </div>;
}

function RecordTable({ records }: { records: RecordItem[] }) {
  return <div className="table-scroll"><table><thead><tr><th>Record</th><th>Collection date</th><th>Laboratory</th><th>Result</th><th>Source</th><th>Status</th><th/></tr></thead><tbody>{records.map(r => <tr key={r.id}><td><div className="table-title"><span className="file-icon"><Icon name="file" size={16}/></span><span><b>{r.name}</b><small>{r.id}</small></span></div></td><td>{r.date}</td><td>{r.lab}</td><td><b>{r.value}</b> <span className="muted">{r.unit}</span><small className="block">{r.range}</small></td><td><Badge tone="neutral">{r.source}</Badge></td><td><Badge tone={r.status === "Needs review" ? "review" : "verified"}>{r.status}</Badge></td><td><button className="kebab">•••</button></td></tr>)}</tbody></table>{records.length === 0 && <div className="empty"><Icon name="search" size={28}/><b>No matching records</b><p>Try a different search term or status filter.</p></div>}</div>;
}

const PageIntro = ({ title, text, actions }: { title: string; text: string; actions?: React.ReactNode }) => <div className="page-intro"><div><h2>{title}</h2><p>{text}</p></div>{actions && <div className="intro-actions">{actions}</div>}</div>;
const Field = ({ label, name, placeholder, required = false, defaultValue, badge }: { label: string; name: string; placeholder?: string; required?: boolean; defaultValue?: string; badge?: string }) => <label className="field"><span>{label}{badge && <Badge tone={badge.includes("67") ? "review" : "neutral"}>{badge}</Badge>}</span><input name={name} placeholder={placeholder} required={required} defaultValue={defaultValue}/></label>;

function ReportAnalysis() {
  const [test, setTest] = useState<"glucose" | "haemoglobin">("glucose");
  return <div className="page"><PageIntro title="Report analysis" text="Compare original measurements over time without changing source values or inferring diagnoses." actions={<Button variant="secondary" icon="download" onClick={() => window.print()}>Export view</Button>}/>
    <div className="filter-bar"><span>TEST</span><select value={test} onChange={e => setTest(e.target.value as typeof test)}><option value="glucose">Fasting Plasma Glucose</option><option value="haemoglobin">Haemoglobin</option></select><span>DATE RANGE</span><select><option>Last 12 months</option><option>All available history</option></select><Badge tone="verified">Units compatible</Badge></div>
    <div className="analysis-grid"><Card className="span-2"><SectionTitle title="Values over time" subtitle={test === "glucose" ? "5 measurements · mg/dL · Source values preserved" : "5 measurements · g/dL · Source values preserved"}/><TrendChart kind={test}/></Card><Card><SectionTitle title="Comparison readiness" subtitle="Deterministic unit checks"/><div className="readiness"><div><Icon name="check"/><span><b>5 comparable values</b><small>Same analyte and compatible units</small></span></div><div><Icon name="chart"/><span><b>1 supported conversion</b><small>100 mg/dL ≈ 5.55 mmol/L</small></span></div><div className="warn"><Icon name="alert"/><span><b>1 value excluded</b><small>Analyte context unavailable</small></span></div></div></Card></div>
    <Card><SectionTitle title="Side-by-side report comparison" subtitle="Original report values and reference ranges"/><div className="comparison"><div className="compare-labels"><span>Source report</span><span>Result</span><span>Reference range</span><span>Report identifier</span><span>Data quality</span></div><div><b>18 Oct 2025</b><small>Aster Diagnostics</small><strong>102 mg/dL</strong><span>70–99 mg/dL</span><code>LAB-8821</code><Badge tone="review">Identifier conflict</Badge></div><div><b>12 Jul 2025</b><small>Aster Diagnostics</small><strong>96 mg/dL</strong><span>70–99 mg/dL</span><code>LAB-8614</code><Badge tone="verified">Reviewed</Badge></div><div><b>04 Apr 2025</b><small>CarePlus Labs</small><strong>5.55 mmol/L</strong><span>3.9–5.5 mmol/L</span><code>CP-2410</code><Badge tone="info">Convertible</Badge></div></div></Card>
  </div>;
}

function IntegrityChecks() {
  const [selected, setSelected] = useState<typeof findings[0] | null>(null);
  const [statuses, setStatuses] = useState<Record<string,string>>({});
  const update = (value: string) => { if (selected) { setStatuses({...statuses, [selected.id]: value}); setSelected({...selected}); } };
  return <div className="page"><PageIntro title="Diagnostic integrity engine" text="Deterministic checks identify evidence requiring review; they do not determine authenticity or fraud."/>
    <div className="metrics compact">{[["4","Open findings"],["1","High-priority review"],["9","Resolved this month"],["12","Rules active"]].map((m,i)=><Card key={m[1]}><span className={`metric-line l${i}`}/><div className="metric-value">{m[0]}</div><b>{m[1]}</b></Card>)}</div>
    <Card><div className="table-tools"><select><option>All severities</option><option>High-Priority Review</option><option>Review</option><option>Info</option></select><select><option>Open findings</option><option>Resolved</option></select><span className="result-count">Last scan: Today, 09:42</span></div><div className="table-scroll"><table><thead><tr><th>Rule / finding</th><th>Severity</th><th>Source report</th><th>Detected</th><th>Status</th><th>Recommended action</th></tr></thead><tbody>{findings.map(f=><tr key={f.id} className="clickable" onClick={()=>setSelected(f)}><td><div className="table-title"><span className={`alert-icon ${f.severity.startsWith("High") ? "danger" : f.severity === "Info" ? "info" : "warn"}`}><Icon name="alert" size={15}/></span><span><b>{f.title}</b><small>{f.id}</small></span></div></td><td><Badge tone={f.severity.startsWith("High") ? "danger" : f.severity === "Info" ? "info" : "review"}>{f.severity}</Badge></td><td><code>{f.report}</code></td><td>{f.when}</td><td><Badge tone={statuses[f.id] === "Resolved" ? "verified" : "neutral"}>{statuses[f.id] || "Inconclusive"}</Badge></td><td>{f.action}</td></tr>)}</tbody></table></div></Card>
    {selected && <Drawer title="Finding evidence" onClose={()=>setSelected(null)}><div className="drawer-head"><Badge tone={selected.severity.startsWith("High") ? "danger" : "review"}>{selected.severity}</Badge><h3>{selected.title}</h3><p>{selected.id} · Detected {selected.when}</p></div><div className="evidence-box"><span>EVIDENCE</span><p>{selected.evidence}</p></div><h4>Why this rule was triggered</h4><p className="body-copy">The deterministic rule compared report metadata and observed a condition outside the configured consistency criteria. This finding indicates that the evidence needs review; it does not establish that a report is false.</p><h4>Next verification step</h4><p className="body-copy">{selected.action}</p><div className="drawer-actions"><Button variant="secondary" onClick={()=>update("Reviewed")}>Mark reviewed</Button><Button variant="secondary" onClick={()=>update("Clinician review")}>Needs clinician review</Button><Button onClick={()=>{update("Resolved"); setSelected(null)}}>Resolve</Button></div></Drawer>}
  </div>;
}

function VerificationPage({ medicine = false }: { medicine?: boolean }) {
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(false);
  const submit = (e: React.FormEvent) => { e.preventDefault(); setLoading(true); setResult(false); window.setTimeout(()=>{setLoading(false);setResult(true)},900); };
  return <div className="page"><PageIntro title={medicine ? "Medicine verification" : "Laboratory verification"} text={medicine ? "Compare product label details with checked regulatory information. No prescribing or substitution advice is provided." : "Check laboratory identity and accreditation details against an official-source demonstration dataset."}/>
    <div className="verification-grid"><Card><SectionTitle title={medicine ? "Product details" : "Search accreditation records"} subtitle="Enter the information visible on your source record"/><form className="verify-form" onSubmit={submit}>
      {medicine ? <><Field label="Brand or product name" name="brand" defaultValue="Glycomet 500"/><Field label="Active ingredient" name="ingredient" defaultValue="Metformin Hydrochloride"/><div className="form-grid"><Field label="Strength" name="strength" defaultValue="500 mg"/><Field label="Dosage form" name="form" defaultValue="Tablet"/></div><Field label="Manufacturer" name="manufacturer" defaultValue="USV Private Limited"/><Field label="Route (if shown)" name="route" defaultValue="Oral"/></> : <><Field label="Laboratory name" name="lab" defaultValue="Metropolis Healthcare Ltd."/><Field label="City or location" name="city" defaultValue="Pune, Maharashtra"/><Field label="Accreditation / certificate number" name="certificate" defaultValue="MC-2104"/><Field label="Test name or discipline" name="discipline" defaultValue="Clinical Biochemistry"/></>}
      <Button type="submit" disabled={loading} icon={loading ? undefined : "search"}>{loading ? "Checking demo source…" : medicine ? "Check product information" : "Check official-source demo"}</Button>
    </form><div className="demo-note"><Icon name="alert" size={16}/><p><b>Demonstration dataset</b><br/>This prototype does not perform a live official-source lookup. Results below are synthetic and clearly identified.</p></div></Card>
    <div>{loading && <Card className="loading-card"><span className="spinner"/><b>Comparing checked fields</b><p>Reviewing identity, scope, validity, and source metadata…</p></Card>}{!loading && !result && <Card className="empty-result"><Icon name={medicine ? "pill" : "flask"} size={34}/><b>No verification run yet</b><p>Complete the search form to view a transparent, synthetic demonstration result.</p></Card>}{result && (medicine ? <MedicineResult/> : <LabResult/>)}</div></div>
  </div>;
}

function LabResult() {
  const [evidence, setEvidence] = useState(false);
  return <Card className="result-card"><div className="result-top"><span className="result-check"><Icon name="check"/></span><div><Badge tone="verified">Verified Against Official Source</Badge><h3>Metropolis Healthcare Ltd.</h3><p>Pune, Maharashtra · Certificate MC-2104</p></div><strong>96%<small>Match confidence</small></strong></div><div className="match-list">{[["Laboratory identity","Exact name match","verified"],["Location","Pune location matched","verified"],["Accreditation status","Active in demo dataset","verified"],["Certificate validity","Valid through 31 Mar 2026","verified"],["Requested scope","Clinical Biochemistry listed","verified"],["Outstanding questions","Collection centre relationship not checked","review"]].map(x=><div key={x[0]}><span>{x[0]}</span><b>{x[1]}</b><Badge tone={x[2]}>{x[2] === "verified" ? "Matched" : "Review"}</Badge></div>)}</div><div className="source-row"><span>Official source reference</span><b>NABL directory demonstration snapshot</b><small>Checked 20 Oct 2025, 10:14 IST</small></div><Button variant="secondary" icon="eye" onClick={()=>setEvidence(!evidence)}>{evidence ? "Hide evidence" : "View evidence"}</Button>{evidence && <div className="evidence-panel"><b>Evidence and limitations</b><p>Matched on laboratory name, city, certificate number, validity date, and discipline. This synthetic snapshot demonstrates a workflow model and is not a live NABL response. Scope can vary by site and version.</p></div>}</Card>;
}

function MedicineResult() {
  return <Card className="result-card"><div className="result-top"><span className="result-check warn"><Icon name="alert"/></span><div><Badge tone="review">Possible Match — Human Review</Badge><h3>Glycomet 500</h3><p>Metformin Hydrochloride Tablets IP</p></div><strong>88%<small>Match confidence</small></strong></div><div className="review-banner"><Icon name="alert"/><p><b>Formulation detail requires review</b><br/>The checked source lists an immediate-release tablet; the uploaded label image does not clearly show release type. Verify with a registered pharmacist or clinician.</p></div><div className="match-list">{[["Active ingredient","Metformin Hydrochloride · match","verified"],["Strength","500 mg · match","verified"],["Dosage form","Tablet · partial detail","review"],["Manufacturer","USV Private Limited · match","verified"],["Regulatory information","Label record available in demo","info"]].map(x=><div key={x[0]}><span>{x[0]}</span><b>{x[1]}</b><Badge tone={x[2]}>{x[2] === "verified" ? "Matched" : "Review"}</Badge></div>)}</div><div className="source-row"><span>Checked source</span><b>CDSCO/SUGAM demonstration dataset</b><small>Source date 06 Aug 2025 · Retrieved 20 Oct 2025</small></div></Card>;
}

type Task = { title:string; expected:string; due:string; source:string; status:string; reason:string };
function CareGaps() {
  const [tasks,setTasks]=useState<Task[]>([
    {title:"Repeat fasting glucose", expected:"Fasting Plasma Glucose report", due:"02 Nov 2025", source:"Dr. Mehta visit note · 18 Oct", status:"Needs Review", reason:"No matching test record found in the available history."},
    {title:"Review lipid profile", expected:"Consultation note", due:"18 Nov 2025", source:"Discharge plan · 20 Sep", status:"Scheduled", reason:"Appointment is recorded; no completion document is available yet."},
    {title:"Share CBC with consultant", expected:"Shared consultation summary", due:"22 Oct 2025", source:"User-confirmed plan · 08 Sep", status:"Completed", reason:"Completion was confirmed by the user."}
  ]);
  const [adding,setAdding]=useState(false);
  const update=(i:number,status:string)=>setTasks(tasks.map((t,n)=>n===i?{...t,status}:t));
  const add=(e:React.FormEvent<HTMLFormElement>)=>{e.preventDefault();const f=new FormData(e.currentTarget);setTasks([{title:String(f.get("title")),expected:String(f.get("expected")),due:String(f.get("due")),source:"User-confirmed care plan",status:"Needs Review",reason:"No matching test record found in the available history."},...tasks]);setAdding(false)};
  return <div className="page"><PageIntro title="Care-gap early warning" text="Track unresolved tasks grounded only in user-confirmed or clinician-provided care plans." actions={<Button icon="plus" onClick={()=>setAdding(true)}>Add care-plan task</Button>}/><div className="safety-strip"><Icon name="shield"/><span>A missing record means only that no matching test record was found in the available history. It does not mean the test was not performed.</span></div><div className="task-list">{tasks.map((t,i)=><Card key={`${t.title}-${i}`}><div className="task-date"><span>DUE</span><b>{t.due.split(" ")[0]}</b><small>{t.due.split(" ").slice(1).join(" ")}</small></div><div className="task-content"><div><Badge tone={t.status==="Completed"?"verified":t.status==="Scheduled"?"info":"review"}>{t.status}</Badge><h3>{t.title}</h3><p>{t.reason}</p></div><dl><div><dt>Expected record</dt><dd>{t.expected}</dd></div><div><dt>Care-plan source</dt><dd>{t.source}</dd></div><div><dt>Records checked</dt><dd>28 available records · checked today</dd></div></dl><div className="task-actions"><Button variant="ghost" onClick={()=>update(i,"Completed")}>Completed elsewhere</Button><Button variant="ghost" onClick={()=>update(i,"Scheduled")}>Mark scheduled</Button><Button variant="ghost" onClick={()=>update(i,"Not Applicable")}>Not applicable</Button><Button variant="secondary" onClick={()=>update(i,"Clinician Review")}>Request clinician review</Button></div></div></Card>)}</div>
    {adding&&<Modal title="Add documented care-plan task" onClose={()=>setAdding(false)}><form className="form-grid" onSubmit={add}><Field label="Task description" name="title" placeholder="e.g. Repeat test X" required/><Field label="Expected test or report" name="expected" placeholder="Record to look for" required/><Field label="Due date" name="due" placeholder="15 Nov 2025" required/><div className="full consent"><input type="checkbox" id="confirmed" required/><label htmlFor="confirmed">I confirm this task comes from a documented or user-confirmed care plan.</label></div><div className="modal-actions full"><Button variant="ghost" onClick={()=>setAdding(false)}>Cancel</Button><Button type="submit">Add task</Button></div></form></Modal>}
  </div>;
}

function ConsultationSummary() {
  const [preview,setPreview]=useState(true);
  const [exclude,setExclude]=useState(false);
  const print=()=>{if(confirm("This export may contain sensitive health information. Continue to the browser print / PDF dialog?")) window.print()};
  return <div className="page summary-page"><PageIntro title="Consultation summary" text="Create a concise, source-linked packet for a clinician review." actions={<><Button variant="secondary" icon="eye" onClick={()=>setPreview(!preview)}>{preview?"Edit selection":"Preview PDF"}</Button><Button icon="download" onClick={print}>Download PDF</Button></>}/><div className="summary-layout"><Card className="summary-controls"><SectionTitle title="Report contents" subtitle="Choose what to include before export"/>{["Selected medical records","Measurement charts","Integrity flags","Laboratory verification","Medicine verification","Care-gap tasks","Source references","Uncertainty notes"].map((x,i)=><label className="toggle-row" key={x}><span>{x}</span><input type="checkbox" defaultChecked={i!==4||!exclude} onChange={i===4?e=>setExclude(!e.target.checked):undefined}/><i/></label>)}<hr/><Field label="Date range" name="range" defaultValue="01 Feb 2025 – 20 Oct 2025"/><div className="export-note"><Icon name="shield"/><p>Sensitive sections can be excluded. Export uses the browser’s print-to-PDF support in this prototype.</p></div></Card>{preview?<ReportPreview exclude={exclude}/>:<Card className="selection-state"><Icon name="clipboard" size={34}/><h3>Selection mode</h3><p>Update the content controls, then preview the consultation-ready report.</p><Button onClick={()=>setPreview(true)}>Preview report</Button></Card>}</div></div>;
}

function ReportPreview({exclude}:{exclude:boolean}) {
  return <article className="pdf-preview"><div className="pdf-head"><div className="brand dark"><div className="brand-mark"><Icon name="shield"/></div><div><strong>SehatSnap</strong><small>INTEGRITY</small></div></div><span>CONSULTATION SUMMARY</span><h2>Health Record Integrity Summary</h2><p>Prepared for professional consultation · Generated 20 Oct 2025, 10:42 IST</p></div><div className="pdf-meta"><div><span>DATE RANGE</span><b>01 Feb – 20 Oct 2025</b></div><div><span>RECORDS REVIEWED</span><b>5 selected reports</b></div><div><span>WORKSPACE</span><b>Synthetic demo profile</b></div></div><div className="pdf-section"><h3>1. Available record summary</h3><p>This packet includes selected records from three reporting laboratories. Original values and units are preserved. Four records were reviewed; one requires follow-up.</p><RecordTable records={initialRecords.slice(0,3)}/></div><div className="pdf-section"><h3>2. Measurement trend</h3><p>Fasting Plasma Glucose · mg/dL · Original laboratory ranges shown where available.</p><TrendChart/></div><div className="pdf-columns"><div className="pdf-section"><h3>3. Data-quality findings</h3><div className="pdf-finding"><Badge tone="danger">High-Priority Review</Badge><b>Conflicting report identifier</b><p>Identifier LAB-8821 appears on two files with different values. Compare originals.</p></div></div><div className="pdf-section"><h3>4. Verification summary</h3><div className="pdf-finding"><Badge tone="verified">Official-source demo</Badge><b>Laboratory identity matched</b><p>NABL directory demo snapshot · retrieved 20 Oct 2025.</p></div></div></div>{!exclude&&<div className="pdf-section"><h3>5. Medicine verification</h3><p>Possible match — human review. Release-type detail was not legible in the available label image.</p></div>}<div className="pdf-disclaimer"><b>Professional review disclaimer</b><p>SehatSnap Integrity supports record quality and verification. It does not diagnose, prescribe, or replace professional medical judgment. Demo lookups are synthetic and not live official-source responses.</p></div></article>;
}

function AuditTrail() {
  const [mode,setMode]=useState<"match"|"mismatch">("match");
  const [checked,setChecked]=useState(false);
  const events=[["EVT-8F21","Report confirmed","a91f…7cd2","20 Oct 2025 · 09:42","User AN","rules-v1.4"],["EVT-8F18","OCR extraction reviewed","c083…91aa","20 Oct 2025 · 09:39","User AN","ocr-demo-v2"],["EVT-8F11","File added","a91f…7cd2","20 Oct 2025 · 09:36","Local upload","ingest-v1.2"]];
  return <div className="page"><PageIntro title="Audit trail" text="A local hash-linked audit log records evidence history without placing patient information on a public blockchain." actions={<Badge tone="info">Local Hash-Linked Audit Log</Badge>}/><div className="audit-grid"><Card><SectionTitle title="Report integrity verification" subtitle="Sample report · SR-1048"/><div className="hash-file"><span><Icon name="file"/></span><div><b>fasting-glucose-oct-2025.pdf</b><small>PDF · 1.8 MB · Added 20 Oct 2025</small></div></div><label className="scenario"><span>DEMO SCENARIO</span><select value={mode} onChange={e=>{setMode(e.target.value as typeof mode);setChecked(false)}}><option value="match">Original sample report</option><option value="mismatch">Altered copy (demonstration)</option></select></label><div className="hashes"><div><span>Recorded SHA-256</span><code>a91f4e80b92c…119a7cd2</code></div><div><span>Current file hash</span><code>{mode==="match"?"a91f4e80b92c…119a7cd2":"7b2d8f11c429…88ef013a"}</code></div></div><Button icon="shield" onClick={()=>setChecked(true)}>Verify integrity</Button>{checked&&<div className={`integrity-result ${mode}`}><Icon name={mode==="match"?"check":"alert"}/><p><b>{mode==="match"?"Integrity of this file matches the recorded hash.":"Integrity mismatch detected — review the recorded evidence."}</b><br/>{mode==="match"?"A matching hash confirms the file is unchanged; it does not prove medical correctness or authenticity.":"The current bytes differ from the recorded artifact. Compare the file history before using it."}</p></div>}</Card><Card><SectionTitle title="Event history" subtitle="Hash-linked sequence for SR-1048"/><div className="event-timeline">{events.map((e,i)=><div key={e[0]}><i className={i===0?"active":""}/><div><span>{e[3]}</span><b>{e[1]}</b><p>Event {e[0]} · Actor: {e[4]}</p><code>Hash {e[2]} · {e[5]}</code></div></div>)}</div></Card></div><Card><SectionTitle title="Recent audit events" subtitle="Tamper-evident record activity"/><div className="table-scroll"><table><thead><tr><th>Event ID</th><th>Event type</th><th>Artifact hash</th><th>Timestamp</th><th>Actor reference</th><th>Rule / model</th><th>Verification</th></tr></thead><tbody>{events.map(e=><tr key={e[0]}><td><code>{e[0]}</code></td><td><b>{e[1]}</b></td><td><code>{e[2]}</code></td><td>{e[3]}</td><td>{e[4]}</td><td>{e[5]}</td><td><Badge tone="verified">Hash-linked</Badge></td></tr>)}</tbody></table></div></Card></div>;
}

function Settings() {
  const [saved,setSaved]=useState(false);
  return <div className="page"><PageIntro title="Settings" text="Manage workspace preferences, privacy, and review behaviour."/><div className="settings-grid"><Card><SectionTitle title="Workspace preferences"/><label className="settings-field"><span>Date format</span><select><option>DD MMM YYYY</option><option>DD/MM/YYYY</option></select></label><label className="settings-field"><span>Default units</span><select><option>Preserve source units</option><option>Metric where compatible</option></select></label><label className="toggle-row"><span><b>Show simulated-data labels</b><small>Keep demonstration status visible across results</small></span><input type="checkbox" defaultChecked/><i/></label><label className="toggle-row"><span><b>Review reminders</b><small>Notify when integrity findings remain unresolved</small></span><input type="checkbox" defaultChecked/><i/></label><Button onClick={()=>{setSaved(true);setTimeout(()=>setSaved(false),2000)}}>{saved?"Preferences saved":"Save preferences"}</Button></Card><Card><SectionTitle title="Privacy & export"/><div className="privacy-block"><Icon name="shield"/><div><b>Local prototype storage</b><p>Session changes are held in this browser view. No backend or public blockchain integration is configured.</p></div></div><button className="settings-link" onClick={()=>alert("No connected integrations in this demonstration workspace.")}>Connected data sources <Icon name="arrow"/></button><button className="settings-link" onClick={()=>alert("Demo records can be cleared by refreshing this prototype.")}>Data retention controls <Icon name="arrow"/></button><button className="settings-link danger-text" onClick={()=>confirm("This is a prototype. Refreshing the page resets session changes.")}>Reset demonstration workspace <Icon name="arrow"/></button></Card></div></div>;
}

function Modal({title,onClose,children}:{title:string;onClose:()=>void;children:React.ReactNode}) {
  return <div className="overlay" onMouseDown={e=>e.target===e.currentTarget&&onClose()}><div className="modal"><div className="modal-head"><div><span>SEHATSNAP INTEGRITY</span><h2>{title}</h2></div><button className="icon-btn" onClick={onClose}><Icon name="x"/></button></div>{children}</div></div>;
}
function Drawer({title,onClose,children}:{title:string;onClose:()=>void;children:React.ReactNode}) {
  return <div className="overlay drawer-overlay" onMouseDown={e=>e.target===e.currentTarget&&onClose()}><aside className="drawer"><div className="modal-head"><div><span>INTEGRITY REVIEW</span><h2>{title}</h2></div><button className="icon-btn" onClick={onClose}><Icon name="x"/></button></div>{children}</aside></div>;
}

function UploadModal({onClose,onConfirm}:{onClose:()=>void;onConfirm:(r:RecordItem)=>void}) {
  const [stage,setStage]=useState<"choose"|"extract"|"review">("choose");
  const [file,setFile]=useState<File|null>(null);
  const input=useRef<HTMLInputElement>(null);
  const select=(f?:File)=>{if(!f)return; if(!/\.(pdf|png|jpe?g)$/i.test(f.name)){alert("Please choose a PDF, PNG, JPG, or JPEG file.");return}setFile(f)};
  const process=()=>{setStage("extract");window.setTimeout(()=>setStage("review"),1200)};
  const confirm=(e:React.FormEvent<HTMLFormElement>)=>{e.preventDefault();const f=new FormData(e.currentTarget);onConfirm({id:"SR-1054",name:String(f.get("test")),date:String(f.get("date")),lab:String(f.get("lab")),value:String(f.get("value")),unit:String(f.get("unit")),range:String(f.get("range")),status:"Reviewed",source:"PDF Extracted"});onClose()};
  return <Modal title={stage==="review"?"Review extracted fields":"Add a medical record"} onClose={onClose}>
    {stage==="choose"&&<div><div className="source-tabs"><button className="active">Upload file</button><button onClick={()=>alert("Online URL import is simulated in this prototype. Use manual entry for confirmed values.")}>Report URL</button></div><div className={`dropzone ${file?"has-file":""}`} onClick={()=>input.current?.click()} onDragOver={e=>e.preventDefault()} onDrop={e=>{e.preventDefault();select(e.dataTransfer.files[0])}}><input ref={input} type="file" accept=".pdf,.png,.jpg,.jpeg" hidden onChange={e=>select(e.target.files?.[0])}/>{file?<><span className="drop-icon"><Icon name="file"/></span><b>{file.name}</b><p>{(file.size/1024/1024).toFixed(2)} MB · Ready to extract</p></>:<><span className="drop-icon"><Icon name="upload"/></span><b>Drop a medical report here</b><p>or click to choose a file</p><small>PDF, PNG, JPG or JPEG · Maximum 20 MB</small></>}</div><div className="demo-note"><Icon name="alert" size={16}/><p>OCR and PDF extraction are simulated in this client-side prototype. You must review every extracted field before confirmation.</p></div><div className="modal-actions"><Button variant="ghost" onClick={onClose}>Cancel</Button><Button disabled={!file} onClick={process}>Extract fields</Button></div></div>}
    {stage==="extract"&&<div className="extracting"><div className="scan-doc"><Icon name="file" size={36}/><i/></div><h3>Extracting report fields</h3><p>Simulating document parsing and provenance mapping…</p><div className="progress"><i/></div><div className="extract-steps"><span><Icon name="check"/> File validated</span><span><span className="spinner small"/> Reading page 1 of 1</span></div></div>}
    {stage==="review"&&<form onSubmit={confirm}><div className="review-warning"><Icon name="alert"/><p><b>Review before confirming</b><br/>Extracted information is not treated as confirmed medical data until you approve it.</p></div><div className="form-grid review-form"><Field label="Test name" name="test" defaultValue="Fasting Plasma Glucose" badge="PDF Extracted · 98%"/><Field label="Result value" name="value" defaultValue="102" badge="PDF Extracted · 96%"/><Field label="Unit" name="unit" defaultValue="mg/dL" badge="PDF Extracted · 94%"/><Field label="Reference range" name="range" defaultValue="70–99 mg/dL" badge="PDF Extracted · 91%"/><Field label="Collection date" name="date" defaultValue="18 Oct 2025" badge="OCR Extracted · 67%"/><Field label="Report date" name="reportDate" defaultValue="19 Oct 2025" badge="PDF Extracted · 95%"/><Field label="Laboratory name" name="lab" defaultValue="Aster Diagnostics, Pune" badge="PDF Extracted · 92%"/><Field label="Report ID" name="reportId" defaultValue="LAB-8821" badge="OCR Extracted · 72%"/></div><div className="provenance-note"><span>Source location</span><b>Page 1 · Results table, row 3</b><small>Original file remains unchanged and linked to this correction history.</small></div><div className="modal-actions"><Button variant="ghost" onClick={onClose}>Cancel</Button><Button variant="secondary" onClick={()=>alert("All fields are already editable. Select any field to update it.")}>Edit fields</Button><Button type="submit">Confirm records</Button></div></form>}
  </Modal>;
}

export default function App() {
  const [page,setPage]=useState<Page>("Overview");
  const [sidebarOpen,setSidebarOpen]=useState(false);
  const [collapsed,setCollapsed]=useState(false);
  const [upload,setUpload]=useState(false);
  const [records, setRecords] = useState<RecordItem[]>([]);
  const [recordsError, setRecordsError] = useState("");
  useEffect(() => {
  let active = true;

  getRecords()
    .then((data) => {
      if (active) {
        setRecords(data.records);
        setRecordsError("");
      }
    })
    .catch((error: unknown) => {
      if (active) {
        setRecordsError(
          error instanceof Error
            ? error.message
            : "Failed to load medical records."
        );
      }
    });

  return () => {
    active = false;
  };
}, []);
  const go=(p:Page)=>{setPage(p);setSidebarOpen(false);window.scrollTo({top:0,behavior:"smooth"})};
  const content=useMemo(()=>{
    if(page==="Overview")return <Overview setPage={go} openUpload={()=>setUpload(true)}/>;
    if(page==="Medical Records")return <MedicalRecords records={records} setRecords={setRecords} recordsError={recordsError} openUpload={()=>setUpload(true)}/>;
    if(page==="Report Analysis")return <ReportAnalysis/>;
    if(page==="Integrity Checks")return <IntegrityChecks/>;
    if(page==="Laboratory Verification")return <VerificationPage/>;
    if(page==="Medicine Verification")return <VerificationPage medicine/>;
    if(page==="Care Gaps")return <CareGaps/>;
    if(page==="Consultation Summary")return <ConsultationSummary/>;
    if(page==="Audit Trail")return <AuditTrail/>;
    return <Settings/>;
  }, [page, records, recordsError]);
  return <div className="app-shell"><Sidebar page={page} setPage={go} open={sidebarOpen} collapse={collapsed} setCollapse={setCollapsed}/><div className={`main-shell ${collapsed?"wide":""}`}><Header page={page} onMenu={()=>setSidebarOpen(!sidebarOpen)} onAdd={()=>setUpload(true)}/><main>{content}</main><footer className="trust-notice"><Icon name="shield" size={15}/><span>SehatSnap Integrity supports medical record quality and verification. It does not diagnose conditions, prescribe treatments, or replace professional medical judgment.</span></footer></div>{upload&&<UploadModal onClose={()=>setUpload(false)} onConfirm={r=>{setRecords([r,...records]);setPage("Medical Records")}}/>}</div>;
}
