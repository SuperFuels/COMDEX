(function installAionProjectManagementWorkspace(global) {
  "use strict";

  let portfolio = null;
  let activeTab = "portfolio";
  let selectedProjectId = "";
  let loading = false;
  let pilotMessages = [{ role: "pilot", text: "Give me an outcome, deadline and budget. I will turn it into a controlled project, keep delivery evidence together and show where attention is needed." }];

  const esc = (value) => String(value == null ? "" : value)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#039;");
  const label = (value) => String(value || "Not set").replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
  const notify = (message, kind = "info") => global.safeAionDesktopMessage?.(message, kind);

  async function request(path, payload = {}) {
    const target = `/api/aion/business/project-management${path}`;
    const body = JSON.stringify(payload);
    if (!global.aionDesktop?.signAionFlowRequest) throw new Error("The protected desktop Project session is unavailable.");
    const headers = await global.aionDesktop.signAionFlowRequest({ method: "POST", target, body, person_id: "desktop_user", workspace_id: "home-fixed" });
    const response = await fetch(`http://127.0.0.1:8080${target}`, { method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json", ...headers }, body });
    const result = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(result.detail || `Project request failed (${response.status})`);
    return result;
  }

  async function refresh(showError = false) {
    if (loading) return;
    loading = true;
    try {
      portfolio = (await request("/status")).state;
      if (!selectedProjectId || !portfolio.projects.some((project) => project.id === selectedProjectId)) selectedProjectId = portfolio.projects[0]?.id || "";
    } catch (error) { if (showError) notify(error.message, "error"); }
    finally { loading = false; rerender(); }
  }

  const selected = () => portfolio?.projects?.find((project) => project.id === selectedProjectId) || portfolio?.projects?.[0] || null;
  const money = (value, currency = "GBP") => {
    const numeric = Number(value || 0);
    try { return new Intl.NumberFormat(undefined, { style: "currency", currency, maximumFractionDigits: 0 }).format(numeric); }
    catch { return `${currency} ${numeric.toFixed(0)}`; }
  };
  const badge = (value, tone = "") => `<span class="pmw-badge ${tone || `is-${esc(value)}`}">${esc(label(value))}</span>`;

  function metric(value, title, detail = "") {
    return `<article class="pmw-metric"><strong>${esc(value)}</strong><span>${esc(title)}</span>${detail ? `<small>${esc(detail)}</small>` : ""}</article>`;
  }

  function renderPortfolio() {
    const summary = portfolio?.summary || {};
    const projects = portfolio?.projects || [];
    return `<section class="pmw-panel">
      <header class="pmw-panel-head"><div><div class="pmw-eyebrow">DELIVERY PORTFOLIO</div><h3>Everything the business has committed to deliver</h3><p>Client work, internal programmes and small practical jobs use the same accountable record without forcing every project into enterprise software.</p></div><button class="pmw-button pmw-primary" data-pmw-new-project>＋ New project</button></header>
      <div class="pmw-metrics">${metric(summary.active_projects || 0,"Live projects")}${metric(summary.at_risk_projects || 0,"At risk / blocked")}${metric(summary.open_tasks || 0,"Open tasks")}${metric(money(summary.budget_total,summary.currency),"Portfolio budget")}${metric(money(Number(summary.spent_total||0)+Number(summary.committed_total||0),summary.currency),"Spent + committed",`${money(summary.remaining_total,summary.currency)} remaining`)}</div>
      ${projects.length ? `<div class="pmw-project-grid">${projects.map((project) => `<button class="pmw-project-card" data-pmw-project="${esc(project.id)}"><div class="pmw-card-top"><span>${esc(label(project.project_type))}</span>${badge(project.status)}</div><h4>${esc(project.title)}</h4><p>${esc(project.outcome)}</p><div class="pmw-progress"><i style="width:${Math.max(2, Number(project.progress_percent || 0))}%"></i></div><footer><span>${esc(project.progress_percent || 0)}% · ${esc(project.open_task_count)} open task(s)</span><strong>${esc(money(project.financials?.remaining, project.currency))} remaining</strong></footer></button>`).join("")}</div>` : `<div class="pmw-empty"><strong>No project records yet</strong><span>Create a client job, refurbishment, internal initiative, R&amp;D programme or department target. Start small: an outcome, an owner, a date and a budget are enough.</span><button class="pmw-button" data-pmw-new-project>Create the first project</button></div>`}
    </section>`;
  }

  function renderProject() {
    const project = selected();
    if (!project) return `<section class="pmw-panel"><div class="pmw-empty">Create or select a project to open its delivery record.</div></section>`;
    return `<section class="pmw-panel">
      <header class="pmw-panel-head"><div><div class="pmw-eyebrow">${esc(label(project.project_type))}</div><h3>${esc(project.title)}</h3><p>${esc(project.outcome)}</p></div><div class="pmw-head-actions">${badge(project.status)}<button class="pmw-button" data-pmw-project-status>Update status</button></div></header>
      <div class="pmw-project-summary"><div><span>Owner</span><strong>${esc(project.owner || "Unassigned")}</strong></div><div><span>Customer / sponsor</span><strong>${esc(project.customer || project.sponsor || "Internal")}</strong></div><div><span>Target</span><strong>${esc(project.target_date || "Not set")}</strong></div><div><span>Budget</span><strong>${esc(money(project.budget_total, project.currency))}</strong></div></div>
      <div class="pmw-actionbar"><button class="pmw-button" data-pmw-add-task>＋ Task</button><button class="pmw-button" data-pmw-add-milestone>＋ Milestone</button><button class="pmw-button" data-pmw-record-cost>＋ Cost</button><button class="pmw-button" data-pmw-add-resource>＋ Person / material</button><button class="pmw-button" data-pmw-add-risk>＋ Risk</button><button class="pmw-button" data-pmw-add-decision>＋ Decision</button></div>
      <div class="pmw-two-col"><div><h4>Work</h4>${project.tasks.length ? project.tasks.map((task) => `<article class="pmw-line"><button class="pmw-task-state" data-pmw-task="${esc(task.id)}" title="Change task status">${task.status === "done" ? "✓" : task.status === "blocked" ? "!" : "○"}</button><div><strong>${esc(task.title)}</strong><small>${esc(task.assignee || "Unassigned")}${task.due_date ? ` · due ${esc(task.due_date)}` : ""}</small></div>${badge(task.status)}</article>`).join("") : `<div class="pmw-quiet">No work items recorded.</div>`}</div><div><h4>Milestones</h4>${project.milestones.length ? project.milestones.map((item) => `<article class="pmw-line"><span class="pmw-marker">◆</span><div><strong>${esc(item.title)}</strong><small>${esc(item.owner || "Unassigned")}${item.due_date ? ` · ${esc(item.due_date)}` : ""}</small></div>${badge(item.status)}</article>`).join("") : `<div class="pmw-quiet">No milestones recorded.</div>`}</div></div>
      <div class="pmw-two-col"><div><h4>Latest updates</h4>${(project.activity || []).slice(-6).reverse().map((item) => `<article class="pmw-activity"><span>${esc(item.message)}</span><small>${esc(item.at || "")}</small></article>`).join("") || `<div class="pmw-quiet">No updates recorded.</div>`}</div><div><h4>Delivery health</h4><div class="pmw-health"><div><span>Progress</span><strong>${esc(project.progress_percent)}%</strong></div><div><span>Open risks</span><strong>${esc(project.open_risk_count)}</strong></div><div><span>Spent</span><strong>${esc(money(project.financials?.spent, project.currency))}</strong></div><div><span>Committed</span><strong>${esc(money(project.financials?.committed, project.currency))}</strong></div></div></div></div>
    </section>`;
  }

  function renderTimeline() {
    const projects = portfolio?.projects || [];
    const items = projects.flatMap((project) => [
      ...(project.milestones || []).map((row) => ({ ...row, project: project.title, kind: "Milestone" })),
      ...(project.tasks || []).filter((row) => row.due_date).map((row) => ({ ...row, project: project.title, kind: "Task" })),
    ]).sort((a,b) => String(a.due_date || "9999").localeCompare(String(b.due_date || "9999")));
    return `<section class="pmw-panel"><header class="pmw-panel-head"><div><div class="pmw-eyebrow">DATES &amp; DEPENDENCIES</div><h3>Timeline</h3><p>A plain-language delivery calendar across every project.</p></div></header>${items.length ? `<div class="pmw-table"><div class="pmw-table-row pmw-table-head"><span>Date</span><span>Project</span><span>Delivery item</span><span>Status</span></div>${items.map((item) => `<div class="pmw-table-row"><span>${esc(item.due_date || "Not set")}</span><span>${esc(item.project)}</span><span><strong>${esc(item.title)}</strong><small>${esc(item.kind)}</small></span><span>${badge(item.status)}</span></div>`).join("")}</div>` : `<div class="pmw-empty">Add task and milestone dates to build the timeline.</div>`}</section>`;
  }

  function renderBudget() {
    const projects = portfolio?.projects || [];
    return `<section class="pmw-panel"><header class="pmw-panel-head"><div><div class="pmw-eyebrow">BUDGET CONTROL</div><h3>Budget, commitments and actual cost</h3><p>Committed costs stay separate from money already spent, so the apparent balance does not hide future obligations.</p></div></header>${projects.length ? projects.map((project) => `<article class="pmw-budget"><div class="pmw-budget-title"><button data-pmw-project="${esc(project.id)}">${esc(project.title)}</button>${badge(project.status)}</div><div class="pmw-health"><div><span>Budget</span><strong>${esc(money(project.budget_total,project.currency))}</strong></div><div><span>Spent</span><strong>${esc(money(project.financials?.spent,project.currency))}</strong></div><div><span>Committed</span><strong>${esc(money(project.financials?.committed,project.currency))}</strong></div><div><span>Remaining</span><strong>${esc(money(project.financials?.remaining,project.currency))}</strong></div></div>${project.costs?.length ? `<details><summary>${esc(project.costs.length)} cost record(s)</summary>${project.costs.map((cost) => `<div class="pmw-cost"><span>${esc(cost.description)} · ${esc(label(cost.category))}${cost.committed ? " · committed" : ""}</span><strong>${esc(money(cost.amount,project.currency))}</strong></div>`).join("")}</details>` : ""}</article>`).join("") : `<div class="pmw-empty">No project budget has been created.</div>`}</section>`;
  }

  function renderResources() {
    const projects = portfolio?.projects || [];
    const rows = projects.flatMap((project) => (project.resources || []).map((item) => ({ ...item, project: project.title })));
    return `<section class="pmw-panel"><header class="pmw-panel-head"><div><div class="pmw-eyebrow">PEOPLE · MATERIALS · SUPPLIERS</div><h3>Resources</h3><p>See what each project needs, who owns it and whether it has been secured.</p></div></header>${rows.length ? `<div class="pmw-table"><div class="pmw-table-row pmw-table-head"><span>Project</span><span>Resource</span><span>Type / quantity</span><span>Status</span></div>${rows.map((item) => `<div class="pmw-table-row"><span>${esc(item.project)}</span><span><strong>${esc(item.name)}</strong><small>${esc(item.owner || "No owner")}</small></span><span>${esc(label(item.kind))} · ${esc(item.quantity)}</span><span>${badge(item.status)}</span></div>`).join("")}</div>` : `<div class="pmw-empty">No people, materials, suppliers or equipment requirements are recorded yet.</div>`}</section>`;
  }

  function renderRisks() {
    const projects = portfolio?.projects || [];
    const risks = projects.flatMap((project) => (project.risks || []).map((item) => ({ ...item, project: project.title })));
    const decisions = projects.flatMap((project) => (project.decisions || []).map((item) => ({ ...item, project: project.title })));
    return `<section class="pmw-panel"><header class="pmw-panel-head"><div><div class="pmw-eyebrow">CONTROL RECORD</div><h3>Risks and decisions</h3><p>Keep the reason behind a decision beside the delivery evidence it affected.</p></div></header><div class="pmw-two-col"><div><h4>Open risks</h4>${risks.length ? risks.map((item) => `<article class="pmw-record"><strong>${esc(item.title)}</strong><span>${esc(item.project)} · ${esc(label(item.likelihood))} likelihood · ${esc(label(item.impact))} impact</span><small>${esc(item.mitigation || "No mitigation recorded")}</small></article>`).join("") : `<div class="pmw-quiet">No risks recorded.</div>`}</div><div><h4>Decisions</h4>${decisions.length ? decisions.map((item) => `<article class="pmw-record"><strong>${esc(item.decision)}</strong><span>${esc(item.project)}</span><small>${esc(item.reason || "No reason recorded")}</small></article>`).join("") : `<div class="pmw-quiet">No decisions recorded.</div>`}</div></div></section>`;
  }

  function renderRight() {
    if (!portfolio) return `<section class="pmw-panel"><div class="pmw-empty">${loading ? "Loading the project portfolio…" : "Project Management is ready to load."}</div></section>`;
    if (activeTab === "project") return renderProject();
    if (activeTab === "timeline") return renderTimeline();
    if (activeTab === "budget") return renderBudget();
    if (activeTab === "resources") return renderResources();
    if (activeTab === "risks") return renderRisks();
    return renderPortfolio();
  }

  function styles() { return `<style>
    .pmw-shell{--pm:#216b61;height:100%;background:#f8fafb;border-top:4px solid var(--pm);color:#172536}.pmw-head{height:96px;box-sizing:border-box;display:flex;justify-content:space-between;align-items:center;padding:18px 28px;border-bottom:1px solid #d8e1e5;background:#f7fafb}.pmw-head h2{margin:7px 0 0;font-size:27px}.pmw-eyebrow{color:var(--pm);font-size:10px;letter-spacing:.2em;font-weight:950}.pmw-status{border:1px solid #98bab5;background:#fff;padding:8px 11px;color:#305e58;font-size:9px;font-weight:900;letter-spacing:.12em;text-transform:uppercase}.pmw-split{display:grid;grid-template-columns:minmax(320px,var(--pmw-left,34%)) 22px minmax(600px,1fr);height:calc(100% - 96px);overflow:hidden}.pmw-pilot{min-width:0;display:flex;flex-direction:column;padding:20px 24px;background:#f4faf8}.pmw-pilot-title{display:flex;justify-content:space-between;gap:12px;padding-bottom:15px;border-bottom:1px solid #bdd5d0}.pmw-pilot-title small{display:block;margin-top:3px;color:#64748b}.pmw-help{margin:14px 0 0;border:1px solid #a9cfca;background:#fff;border-radius:10px}.pmw-help summary{padding:12px 14px;font-weight:850;cursor:pointer}.pmw-help div{padding:0 14px 13px;color:#637783;font-size:12px;line-height:1.5}.pmw-thread{flex:1;min-height:180px;overflow:auto;padding:18px 0;display:flex;flex-direction:column;gap:12px}.pmw-message{max-width:88%;padding:14px 16px;border:1px solid #a9d3cd;background:#eaf7f4;color:#23564f;line-height:1.5;border-radius:4px 16px 16px}.pmw-message.user{align-self:flex-end;background:#152b38;border-color:#152b38;color:#fff;border-radius:16px 4px 16px 16px}.pmw-message b{display:block;margin-bottom:5px;font-size:9px;letter-spacing:.12em}.pmw-chat{display:flex;gap:8px;padding-top:13px;border-top:1px solid #bdd5d0}.pmw-chat textarea{flex:1;min-width:0;padding:11px;border:1px solid #8fbab4;resize:vertical}.pmw-chat button,.pmw-primary{background:#152b38!important;border-color:#152b38!important;color:#fff!important}.pmw-resizer{display:grid;place-items:center;border-left:1px solid #d7e0e3;border-right:1px solid #d7e0e3;background:#f5f7f8;cursor:col-resize}.pmw-resizer span{color:var(--pm);font-weight:900}.pmw-work{min-width:0;overflow:auto;background:#f6f8f9}.pmw-tabs{position:sticky;top:0;z-index:3;display:flex;gap:5px;padding:11px 14px;border-bottom:1px solid #d5dfe3;background:#edf2f3}.pmw-tabs button{border:1px solid #b9c8cd;background:#fff;padding:8px 11px;font-weight:800;cursor:pointer}.pmw-tabs button.active{border-color:#152b38;background:#152b38;color:#fff}.pmw-content{padding:14px}.pmw-panel{min-height:360px;padding:20px;border:1px solid #cfdbdf;border-top:4px solid var(--pm);background:#fff}.pmw-panel-head{display:flex;justify-content:space-between;align-items:flex-start;gap:20px;padding-bottom:16px;border-bottom:1px solid #dce4e7}.pmw-panel-head h3{margin:5px 0;font-size:24px}.pmw-panel-head p{max-width:760px;margin:0;color:#64748b;line-height:1.48}.pmw-button{border:1px solid #91afa9;background:#fff;color:#264e49;padding:9px 12px;font-weight:850;cursor:pointer}.pmw-metrics{display:grid;grid-template-columns:repeat(5,minmax(110px,1fr));gap:9px;margin:16px 0}.pmw-metric{padding:14px;border:1px solid #d5e0e2}.pmw-metric strong{display:block;font-size:23px}.pmw-metric span,.pmw-metric small{display:block;margin-top:3px;color:#657786;font-size:11px}.pmw-project-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(270px,1fr));gap:11px}.pmw-project-card{min-height:190px;padding:16px;border:1px solid #d0dcdf;border-top:3px solid #4b8c83;background:#fff;text-align:left;cursor:pointer}.pmw-card-top,.pmw-project-card footer,.pmw-budget-title{display:flex;justify-content:space-between;gap:10px;align-items:center}.pmw-card-top>span:first-child{color:#61737f;font-size:9px;font-weight:900;letter-spacing:.12em;text-transform:uppercase}.pmw-project-card h4{margin:17px 0 7px;font-size:17px}.pmw-project-card p{height:40px;margin:0;color:#64748b;font-size:12px;line-height:1.45;overflow:hidden}.pmw-progress{height:5px;margin:17px 0 9px;background:#e6ecee}.pmw-progress i{display:block;height:100%;background:var(--pm)}.pmw-project-card footer{font-size:10px;color:#637581}.pmw-project-card footer strong{color:#223d49}.pmw-badge{display:inline-block;padding:4px 6px;border:1px solid #adc5c1;background:#f3faf8;color:#30675f;font-size:8px;font-weight:900;letter-spacing:.08em;text-transform:uppercase}.pmw-badge.is-at_risk,.pmw-badge.is-blocked{border-color:#e0b29c;background:#fff7f2;color:#984b27}.pmw-badge.is-completed,.pmw-badge.is-done{border-color:#a8ceb9;background:#f1faf5;color:#26734d}.pmw-empty{display:grid;place-items:center;gap:10px;min-height:260px;color:#64748b;text-align:center}.pmw-project-summary,.pmw-health{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:9px;margin:15px 0}.pmw-project-summary div,.pmw-health div{padding:12px;background:#f3f6f7}.pmw-project-summary span,.pmw-health span{display:block;color:#71818d;font-size:9px;letter-spacing:.08em;text-transform:uppercase}.pmw-project-summary strong,.pmw-health strong{display:block;margin-top:4px}.pmw-actionbar{display:flex;flex-wrap:wrap;gap:7px;margin:14px 0}.pmw-two-col{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px;margin-top:15px}.pmw-two-col>div{border:1px solid #d6e0e3;padding:14px}.pmw-two-col h4{margin:0 0 12px}.pmw-line{display:grid;grid-template-columns:28px 1fr auto;gap:8px;align-items:center;padding:10px 0;border-bottom:1px solid #e2e8ea}.pmw-line small{display:block;margin-top:3px;color:#71818d}.pmw-task-state{width:25px;height:25px;border:1px solid #91afa9;background:#fff;color:#216b61;cursor:pointer}.pmw-marker{color:#216b61}.pmw-activity,.pmw-cost{display:flex;justify-content:space-between;gap:12px;padding:9px 0;border-bottom:1px solid #e1e7e9}.pmw-activity small{color:#71818d}.pmw-quiet{padding:18px;background:#f5f7f8;color:#71818d}.pmw-head-actions{display:flex;align-items:center;gap:8px}.pmw-table{margin-top:15px;border:1px solid #d6e0e3}.pmw-table-row{display:grid;grid-template-columns:.75fr 1.15fr 2fr .8fr;gap:12px;align-items:center;padding:12px;border-bottom:1px solid #dce4e7}.pmw-table-row:last-child{border-bottom:0}.pmw-table-row small{display:block;margin-top:3px;color:#71818d}.pmw-table-head{background:#eff3f4;color:#5c707d;font-size:9px;font-weight:900;letter-spacing:.1em;text-transform:uppercase}.pmw-budget{margin-top:13px;padding:15px;border:1px solid #d3dfe2}.pmw-budget-title button{border:0;background:none;padding:0;color:#172536;font-size:16px;font-weight:900;cursor:pointer}.pmw-budget summary{cursor:pointer;color:#4c6571}.pmw-record{display:grid;gap:5px;padding:12px 0;border-bottom:1px solid #dfe6e8}.pmw-record span,.pmw-record small{color:#657986}.pmw-cost strong{white-space:nowrap}
    @media(max-width:1200px){.pmw-split{display:block;height:auto;overflow:auto}.pmw-resizer{display:none}.pmw-pilot,.pmw-work{min-height:650px}.pmw-metrics{grid-template-columns:repeat(2,1fr)}}
  </style>`; }

  function render() {
    if (!portfolio && !loading) setTimeout(() => refresh(false), 0);
    const tabs = [["portfolio","Portfolio"],["project","Project"],["timeline","Timeline"],["budget","Budget"],["resources","Team & resources"],["risks","Risks & decisions"]];
    return `${styles()}<section class="pmw-shell" data-aion-project-management-root><header class="pmw-head"><div><div class="pmw-eyebrow">PILOT · PROJECT DELIVERY COMMAND CENTRE</div><h2>Project coordination</h2></div><span class="pmw-status">Evidence-led · approval gated</span></header><div class="pmw-split" data-pmw-split><section class="pmw-pilot"><div class="pmw-pilot-title"><div><strong>Project Pilot</strong><small>Goals, teams, budgets and delivery adviser</small></div><span class="pmw-status">Controlled records</span></div><details class="pmw-help"><summary>What can I ask Project Pilot to do? ＋</summary><div>Create a project from a business outcome; break work into milestones; review budget, blockers and delivery risk; or prepare a status update. Project Pilot changes records only through explicit project actions.</div></details><div class="pmw-thread" data-pmw-thread>${pilotMessages.map((item) => `<div class="pmw-message ${item.role === "user" ? "user" : ""}"><b>${item.role === "user" ? "YOU" : "PROJECT PILOT"}</b>${esc(item.text).replace(/\n/g,"<br>")}</div>`).join("")}</div><form class="pmw-chat" data-pmw-chat><textarea rows="2" data-pmw-input placeholder="Ask about a project, budget or delivery risk…"></textarea><button type="submit">Send</button></form></section><div class="pmw-resizer" data-pmw-resizer><span>⋮<br>⋮</span></div><section class="pmw-work"><nav class="pmw-tabs">${tabs.map(([key,name]) => `<button class="${activeTab===key?"active":""}" data-pmw-tab="${key}">${name}</button>`).join("")}</nav><div class="pmw-content">${renderRight()}</div></section></div></section>`;
  }

  function rerender() {
    const root = document.querySelector("[data-aion-project-management-root]");
    if (!root) return;
    const holder = document.createElement("div"); holder.innerHTML = render(); root.replaceWith(holder.firstElementChild);
  }

  async function mutate(operation, fields) {
    const project = selected(); if (!project) return notify("Select a project first.", "error");
    try { portfolio = (await request(`/projects/${encodeURIComponent(project.id)}/actions`, { operation, fields })).state; notify("Project record updated.", "success"); rerender(); }
    catch (error) { notify(error.message, "error"); }
  }

  document.addEventListener("click", async (event) => {
    const tab = event.target.closest?.("[data-pmw-tab]");
    if (tab) { activeTab = tab.dataset.pmwTab; rerender(); return; }
    const projectButton = event.target.closest?.("[data-pmw-project]");
    if (projectButton) { selectedProjectId = projectButton.dataset.pmwProject; activeTab = "project"; rerender(); return; }
    if (event.target.closest?.("[data-pmw-new-project]")) {
      const title = prompt("Project or job name"); if (!title) return;
      const outcome = prompt("What must be delivered or achieved?"); if (!outcome) return;
      const project_type = prompt("Type: client_job, internal_initiative, refurbishment, research_development, department_target or implementation", "client_job") || "other";
      const owner = prompt("Owner or project lead") || ""; const customer = prompt("Client, sponsor or department") || "";
      const target_date = prompt("Target date (YYYY-MM-DD)") || ""; const budget_total = prompt("Approved budget", "0") || "0";
      try { portfolio = (await request("/projects", { title, outcome, project_type, owner, customer, target_date, currency: "GBP", budget_total })).state; selectedProjectId = portfolio.projects.at(-1)?.id || ""; activeTab = "project"; notify("Project created.", "success"); rerender(); }
      catch (error) { notify(error.message, "error"); }
      return;
    }
    if (event.target.closest?.("[data-pmw-project-status]")) { const status = prompt("Status: draft, planned, active, at_risk, blocked, completed or cancelled", selected()?.status || "active"); if (status) await mutate("update", { status }); return; }
    if (event.target.closest?.("[data-pmw-add-task]")) { const title = prompt("Task or work item"); if (!title) return; await mutate("add_task", { title, assignee: prompt("Assignee") || "", due_date: prompt("Due date (YYYY-MM-DD)") || "", priority: "normal" }); return; }
    if (event.target.closest?.("[data-pmw-add-milestone]")) { const title = prompt("Milestone"); if (!title) return; await mutate("add_milestone", { title, owner: prompt("Milestone owner") || "", due_date: prompt("Due date (YYYY-MM-DD)") || "" }); return; }
    if (event.target.closest?.("[data-pmw-record-cost]")) { const description = prompt("Cost description"); if (!description) return; const amount = prompt("Amount"); if (!amount) return; await mutate("record_cost", { description, amount, category: prompt("Category (labour, materials, supplier, travel or other)", "other") || "other", committed: confirm("Is this committed but not yet spent?") }); return; }
    if (event.target.closest?.("[data-pmw-add-resource]")) { const name = prompt("Person, material, supplier or equipment required"); if (!name) return; await mutate("add_resource", { name, kind: prompt("Type: person, material, supplier or equipment", "person") || "person", quantity: prompt("Quantity or allocation", "1") || "1", owner: prompt("Owner") || "" }); return; }
    if (event.target.closest?.("[data-pmw-add-risk]")) { const title = prompt("Risk"); if (!title) return; await mutate("add_risk", { title, likelihood: prompt("Likelihood: low, medium or high", "medium") || "medium", impact: prompt("Impact: low, medium or high", "medium") || "medium", mitigation: prompt("How will this be reduced or controlled?") || "", owner: prompt("Risk owner") || "" }); return; }
    if (event.target.closest?.("[data-pmw-add-decision]")) { const decision = prompt("Decision made"); if (!decision) return; await mutate("add_decision", { decision, reason: prompt("Why was this decision made?") || "" }); return; }
    const taskButton = event.target.closest?.("[data-pmw-task]");
    if (taskButton) { const status = prompt("Task status: not_started, in_progress, blocked or done", "done"); if (status) await mutate("task_status", { task_id: taskButton.dataset.pmwTask, status }); }
  });

  document.addEventListener("submit", async (event) => {
    const form = event.target.closest?.("[data-pmw-chat]"); if (!form) return;
    event.preventDefault(); const input = form.querySelector("[data-pmw-input]"); const question = String(input?.value || "").trim(); if (!question) return;
    pilotMessages.push({ role: "user", text: question }); input.value = ""; rerender();
    try {
      const evidence = (await request("/investigate", { question })).investigation;
      let answer = evidence.answer;
      if (typeof global.aionOperationsConversationRequest === "function") {
        try {
          const result = await global.aionOperationsConversationRequest("turn", { department_id: "projects", user_text: `${question}\n\nVerified project evidence: ${evidence.answer}\nProject IDs: ${(evidence.project_ids || []).join(", ") || "none"}. Explain only what the records support; identify missing owners, dates, budgets or dependencies and do not imply that an action was completed.`, attachments: [] });
          answer = result?.conversation?.turn?.content || result?.history?.turns?.slice(-1)?.[0]?.content || answer;
          answer = `${answer}\n\nEvidence boundary: ${evidence.answer}`;
        } catch { /* Keep the deterministic portfolio answer. */ }
      }
      pilotMessages.push({ role: "pilot", text: answer }); rerender();
    } catch (error) { notify(error.message, "error"); }
  });

  let resizing = false;
  document.addEventListener("pointerdown", (event) => { if (event.target.closest?.("[data-pmw-resizer]")) { resizing = true; event.preventDefault(); } });
  document.addEventListener("pointermove", (event) => { if (!resizing) return; const split = document.querySelector("[data-pmw-split]"); if (!split) return; const rect = split.getBoundingClientRect(); const width = Math.max(300, Math.min(rect.width * .52, event.clientX - rect.left)); split.style.setProperty("--pmw-left", `${width}px`); });
  document.addEventListener("pointerup", () => { resizing = false; });

  global.AionProjectManagementWorkspace = { render, refresh };
})(window);
