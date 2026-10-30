"use strict";
const $ = (s) => document.querySelector(s);
const esc = (t) => String(t ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const TEST = { abi_pvr: "ABI / PVR", toe_pressure: "Toe pressures", xray_foot: "Foot X-ray", creatinine: "Creatinine",
  cta_runoff: "CTA runoff", vein_mapping: "Vein mapping", angiogram: "Angiogram", lipid_panel: "Lipid panel", a1c: "A1c",
  mri_foot: "Foot MRI", wound_care_center: "Wound care center referral" };
const EXAM = { wound: "Wound", periwound: "Skin around the wound", foot_temperature: "Foot temperature",
  femoral_pulses: "Femoral pulses", popliteal_pulses: "Popliteal pulses", pedal_pulses: "Pedal pulses",
  monofilament: "Monofilament", footwear: "Footwear" };
const STEPS = [["ENCOUNTER", "Interview"], ["D1", "Visit 1"], ["D2", "Results"], ["B1", "2-week return"],
  ["D3", "Workup"], ["D4", "Procedure"], ["D5", "Discharge"]];
const testName = (t) => TEST[t] || t.replace(/_/g, " ");

let sid = null, S = null, noteKey = null, godOpen = null, busyN = 0;

async function api(path, body, method = body === undefined ? "GET" : "POST") {
  busy(+1);
  try {
    const r = await fetch(path, { method, headers: { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body) });
    const data = await r.json().catch(() => ({}));
    if (!r.ok) throw new Error(data.detail || `Request failed (${r.status}).`);
    if (data.state) { S = data.state; render(); }
    return data;
  } catch (e) {
    flash(e.message);
    throw e;
  } finally { busy(-1); }
}
function busy(d) {
  busyN += d;
  const b = $("#busy");
  if (!b.dataset.err) { b.textContent = "Thinking…"; b.hidden = busyN <= 0; }
  document.querySelectorAll("button, input, textarea").forEach((el) => { if (!el.closest(".tabs")) el.toggleAttribute("data-busy", busyN > 0); });
}
function flash(msg) {
  const b = $("#busy"); b.textContent = msg; b.dataset.err = "1"; b.hidden = false;
  setTimeout(() => { delete b.dataset.err; b.hidden = busyN <= 0; b.textContent = "Thinking…"; }, 4500);
}

/* ---------- start / routing ---------- */
document.querySelectorAll("#start [data-mode]").forEach((b) => b.addEventListener("click", async () => {
  const d = await api("/api/session", { mode: b.dataset.mode });
  sid = d.id; noteKey = null;
  $("#start").hidden = true; $("#faculty").hidden = true; $("#app").hidden = false;
  render(); $("#say").focus();
}));
window.addEventListener("hashchange", route);
function route() {
  const fac = location.hash === "#faculty";
  $("#faculty").hidden = !fac;
  if (fac) { godClose(); $("#start").hidden = true; $("#app").hidden = true; loadSaved(); }
  else if (!sid) { $("#start").hidden = false; $("#app").hidden = true; }
  else { $("#app").hidden = false; }
}
route();

/* ---------- render ---------- */
function render() {
  if (!S) return;
  $("#case-title").textContent = S.case_title;
  $("#mode").textContent = S.mode === "practice" ? "Practice" : "Assessment";
  renderSteps(); renderEncounter(); renderNote(); renderAssistant(); renderChart();
  $("#finish-interview").hidden = S.phase !== "interview";
  $("#say-form").querySelector("input").disabled = S.phase === "done";
}

function renderSteps() {
  const signed = new Set(S.signed_notes.filter((n) => n.status === "signed").map((n) => n.node));
  const now = S.phase === "done" ? null : S.node === "ENCOUNTER" ? (S.note ? "D1" : "ENCOUNTER") : S.node;
  const visitedB1 = signed.has("B1") || now === "B1";
  $("#steps").innerHTML = STEPS.filter(([k]) => k !== "B1" || visitedB1).map(([k, label]) => {
    const cls = k === now ? "now" : (signed.has(k) || (k === "ENCOUNTER" && S.note)) ? "done" : "";
    return `<li class="${cls} ${k === "B1" ? "branch" : ""}" ${k === now ? 'aria-current="step"' : ""}>${label}</li>`;
  }).join("");
}

function renderEncounter() {
  const box = $("#encounter");
  if (!S.encounter.length) {
    box.innerHTML = `<p class="empty">He's on the exam table. Introduce yourself and take a history. Examine him by saying what you're doing.</p>`;
    return;
  }
  box.innerHTML = S.encounter.map((e) => {
    let h = `<div class="line you">${esc(e.physician)}</div>`;
    if (e.patient && !(e.exam.length && /^(okay|sure)\.?$/i.test(e.patient.trim()))) h += `<div class="line patient">${esc(e.patient)}</div>`;
    h += e.exam.map((x) => `<div class="line exam"><b>${esc(EXAM[x.component] || x.component)}:</b> ${esc(x.finding)}</div>`).join("");
    return h;
  }).join("");
  box.scrollTop = box.scrollHeight;
}

function renderNote() {
  const n = S.note, clip = $("#clipboard");
  if (!n) { clip.hidden = true; return; }
  clip.hidden = false;
  const key = n.node;
  if (key !== noteKey) {
    noteKey = key;
    $("#note-ap").value = "";
    clip.classList.remove("down");
    $("#clip-toggle").textContent = "Back to patient";
  }
  $("#note-title").textContent = n.title;
  $("#note-ap").placeholder = n.prompt;
  const fu = $("#note-followup");
  fu.hidden = !n.followup; fu.textContent = n.followup ? `Attending: ${n.followup} Revise your plan and sign again.` : "";
  $("#note-results").innerHTML = n.new_results.length ? `<div class="results-block"><strong>New results</strong>${
    n.new_results.map((r) => `<div><b>${esc(testName(r.test))}:</b> ${esc(r.result)}</div>`).join("")}</div>` : "";
  const hw = $("#note-history-wrap"), ht = $("#note-history");
  hw.hidden = !n.history;
  if (n.history && (ht.dataset.src !== n.history || !n.history_editable)) {
    if (ht.dataset.src !== n.history) { ht.value = n.history; ht.dataset.src = n.history; }
  }
  ht.readOnly = !n.history_editable;
  hw.querySelector("label").textContent = n.history_editable
    ? "History, drafted by the ambient AI. Review and correct it before signing."
    : "History (signed)";
  $("#sign").disabled = S.phase !== "note";
}

function renderAssistant() {
  const a = $("#assistant"), pend = S.alerts_pending;
  a.classList.toggle("alerting", pend.length > 0);
  const badge = $("#alert-badge");
  badge.hidden = !pend.length; badge.textContent = pend.length;
  badge.setAttribute("aria-label", `${pend.length} unopened alert${pend.length === 1 ? "" : "s"}`);
  $("#alert-open").hidden = !pend.length;
  $("#alert-text").textContent = pend.length === 1 ? "1 unopened alert" : `${pend.length} unopened alerts`;
  const log = $("#ai-log");
  log.innerHTML = S.assistant_chat.length ? S.assistant_chat.map((m) => {
    const q = m.question ? `<div class="ai-q">${esc(m.question)}</div>` : "";
    const meta = `<div class="ai-meta"><span class="conf ${esc(m.confidence)}">${esc(m.confidence)} confidence</span>${
      m.citation ? `<span>Source: ${esc(m.citation)}</span>` : ""}${m.alert ? "<span>Alert</span>" : ""}</div>`;
    return `${q}<div class="ai-a ${m.alert ? "alert" : ""}">${esc(m.text)}${meta}</div>`;
  }).join("") : `<p class="empty">Ambient assistant. It has the chart and hears your conversation. Ask it anything.</p>`;
  log.scrollTop = log.scrollHeight;
}

function renderChart() {
  const c = S.chart;
  $("#tab-chart").innerHTML = `<dl>
    <dt>Referral</dt><dd>${esc(c.referral)}</dd>
    <dt>Problem list</dt><dd><ul>${c.pmh.map((x) => `<li>${esc(x)}</li>`).join("")}</ul></dd>
    <dt>Medications</dt><dd><ul>${c.meds.map((x) => `<li>${esc(x)}</li>`).join("")}</ul></dd>
    <dt>Allergies</dt><dd>${esc(c.allergies)}</dd>
    <dt>Vitals</dt><dd>BP ${esc(c.vitals.bp)}. ${esc(c.vitals.other)}.</dd>
    <dt>Labs</dt><dd>${Object.entries(c.labs).map(([k, v]) => `${esc(k)} ${esc(v)}`).join("; ")}</dd></dl>`;
  $("#tab-results").innerHTML = S.results.length ? S.results.map((r) =>
    `<div class="res"><b>${esc(testName(r.test))}</b>${esc(r.result)}</div>`).join("")
    : `<p class="empty">Nothing resulted yet. Orders go in the plan of your note.</p>`;
  $("#tab-notes").innerHTML = S.signed_notes.length ? S.signed_notes.map((n) => `<div class="signed">
    <h3>${esc(n.title)} ${n.status !== "signed" ? `<span class="tag">${esc(n.status)}</span>` : ""}</h3>
    ${n.history ? `<pre>${esc(n.history)}</pre>` : ""}<pre><b>A/P:</b> ${esc(n.ap)}</pre></div>`).join("")
    : `<p class="empty">No signed notes yet.</p>`;
  $("#results-count").textContent = S.results.length ? `(${S.results.length})` : "";
  $("#notes-count").textContent = S.signed_notes.length ? `(${S.signed_notes.length})` : "";
}

/* ---------- encounter ---------- */
$("#say-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const t = $("#say").value.trim(); if (!t || busyN) return;
  $("#say").value = "";
  try { await api(`/api/${sid}/talk`, { text: t }); } catch { $("#say").value = t; }
});
$("#finish-interview").addEventListener("click", () => api(`/api/${sid}/finish_interview`, {}));
$("#clip-toggle").addEventListener("click", () => {
  const down = $("#clipboard").classList.toggle("down");
  $("#clip-toggle").textContent = down ? "Open note" : "Back to patient";
});

/* ---------- note ---------- */
$("#sign").addEventListener("click", async () => {
  const ap = $("#note-ap").value.trim();
  if (!ap) { flash("Write an assessment and plan before signing."); $("#note-ap").focus(); return; }
  const body = { ap };
  if (S.note.history_editable) body.history = $("#note-history").value;
  const d = await api(`/api/${sid}/note`, body);
  const r = d.result;
  if (r.educator) openEducator();
  else if (r.followup) openFollowup(r.followup);
  else if (S.phase === "done") openReport();
});

/* ---------- assistant ---------- */
$("#assistant-bar").addEventListener("click", () => {
  const c = $("#assistant").classList.toggle("collapsed");
  $("#assistant-bar").setAttribute("aria-expanded", String(!c));
});
$("#ai-form").addEventListener("submit", async (ev) => {
  ev.preventDefault();
  const q = $("#ai-q").value.trim(); if (!q || busyN) return;
  $("#ai-q").value = "";
  try { await api(`/api/${sid}/assistant`, { text: q }); } catch { $("#ai-q").value = q; }
});
$("#open-alert").addEventListener("click", () => api(`/api/${sid}/alert/${S.alerts_pending[0]}`, {}));

/* ---------- chart tabs ---------- */
document.querySelectorAll(".tabs button").forEach((b) => b.addEventListener("click", () => {
  document.querySelectorAll(".tabs button").forEach((x) => x.setAttribute("aria-selected", String(x === b)));
  ["chart", "results", "notes"].forEach((t) => ($(`#tab-${t}`).hidden = t !== b.dataset.tab));
}));

/* ---------- God ---------- */
function god(html) {
  $("#god-content").innerHTML = html;
  const g = $("#god"); g.classList.add("open"); g.setAttribute("aria-hidden", "false");
  setTimeout(() => { const f = $("#god-content textarea, #god-content button"); if (f) f.focus(); }, 500);
}
function godClose() {
  const g = $("#god"); g.classList.remove("open"); g.setAttribute("aria-hidden", "true"); godOpen = null;
}
function openFollowup(q) {
  godOpen = "followup";
  god(`<div class="god-who">Attending</div><p class="voice q">${esc(q)}</p>
    <div class="god-row"><button class="btn primary" id="god-ok">Revise my plan</button></div>`);
  $("#god-ok").onclick = () => { godClose(); $("#note-ap").focus(); };
}
function openEducator() {
  godOpen = "educator";
  const ex = S.exchanges, last = ex[ex.length - 1], turns = S.educator || [];
  const aiLine = turns.length ? turns[turns.length - 1].ai_use_line : "";
  let h = `<div class="god-who">Attending</div>`;
  h += ex.map((e) => e.who === "educator" ? `<p class="voice ${e.kind === "question" ? "q" : ""}">${esc(e.text)}</p>`
    : `<p class="reply">${esc(e.text)}</p>`).join("");
  if (last && last.kind === "question") {
    h += `<label for="god-reply" class="sr">Your answer</label><textarea id="god-reply" rows="3" placeholder="Answer the attending"></textarea>
      <div class="god-row"><button class="btn primary" id="god-send">Answer</button></div>`;
  } else {
    h += aiLine ? `<p class="ai-line">${esc(aiLine)}</p>` : "";
    h += `<div class="god-row"><button class="btn primary" id="god-ok">${S.phase === "done" ? "See how it went" : "Continue"}</button></div>`;
  }
  god(h);
  const send = $("#god-send");
  if (send) send.onclick = async () => {
    const t = $("#god-reply").value.trim(); if (!t) return;
    send.disabled = true;
    try { await api(`/api/${sid}/educator`, { text: t }); openEducator(); } catch { send.disabled = false; }
  };
  const ok = $("#god-ok");
  if (ok) ok.onclick = () => { if (S.phase === "done") openReport(); else godClose(); };
}

async function openReport() {
  godOpen = "report";
  god(`<div class="god-who">Attending</div><p class="voice">Let's go over the case.</p>`);
  const d = await api(`/api/${sid}/report`);
  god(reportHtml(d.result) + `<div class="god-row"><button class="btn primary" id="god-new">Start a new case</button></div>`);
  $("#god-new").onclick = () => location.reload();
}

const CELLS = { "appropriate reliance": "good", "appropriate override": "good", "overreliance": "bad", "reflexive dismissal": "bad" };
function reportHtml(rep) {
  const items = rep.calibration.items, by = (c) => items.filter((i) => i.cell === c);
  const cell = (c) => { const xs = by(c); return `<div class="cell ${CELLS[c]}"><div class="lab">${c}</div><div class="n">${xs.length}</div>
    <div class="items">${xs.map((i) => esc(i.what)).join("<br>")}</div></div>`; };
  const extra = ["not consulted", "alert not opened", "seen, no clear action", "low-value output opened"]
    .map((c) => `<span>${c}: <b>${by(c).length}</b></span>`).join("");
  const deb = rep.debrief ? Object.fromEntries(rep.debrief.decisions.map((d) => [d.node, d])) : {};
  const decs = rep.decisions.map((d) => {
    const fb = deb[d.node] || (d.educator && d.educator.length ? { feedback: d.educator[d.educator.length - 1].message,
      ai_use_line: d.educator[d.educator.length - 1].ai_use_line } : null);
    return `<div class="dec"><b>${esc(d.node)}</b> <span>${esc(d.text)}</span>${fb ? `<p>${esc(fb.feedback)}</p><p><i>${esc(fb.ai_use_line)}</i></p>` : ""}</div>`;
  }).join("");
  return `<div class="report"><h2>What happened to him</h2>
    <ul class="events">${rep.outcome.events.map((e) => `<li>${esc(e)}</li>`).join("")}</ul>
    <h3>How you used the AI</h3>
    <div class="grid2"><div></div><div class="hd">You followed it</div><div class="hd">You went against it</div>
      <div class="hd">AI was right</div>${cell("appropriate reliance")}${cell("reflexive dismissal")}
      <div class="hd">AI was wrong</div>${cell("overreliance")}${cell("appropriate override")}</div>
    <div class="extra">${extra}</div>
    ${rep.debrief ? `<h3>Overall</h3><p class="voice">${esc(rep.debrief.overall)}</p>` : ""}
    <h3>Decision by decision</h3>${decs}</div>`;
}

/* ---------- faculty ---------- */
async function loadSaved() {
  const list = await api("/api/saved");
  $("#saved-list").innerHTML = list.length ? list.map((s) => `<li><button data-name="${esc(s.name)}" ${s.finished ? "" : "disabled"}>
    ${esc(s.mode)} case, ${new Date(s.started * 1000).toLocaleString()}
    <small>${s.finished ? esc((s.events || []).join(" ")) : "Not finished"}</small></button></li>`).join("")
    : `<li class="empty">No saved sessions yet.</li>`;
  document.querySelectorAll("#saved-list button[data-name]").forEach((b) => b.addEventListener("click", async () => {
    const rep = await api(`/api/saved/${b.dataset.name}`);
    $("#saved-report").innerHTML = reportHtml(rep);
  }));
}
$("#faculty-home").addEventListener("click", (e) => { e.preventDefault(); location.hash = ""; location.reload(); });
