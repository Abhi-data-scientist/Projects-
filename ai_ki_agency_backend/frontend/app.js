const API_URL = "http://127.0.0.1:8000/api/pipeline";
const agents = [
  ["requirement", "Requirement", "Clarify the request"],
  ["architecture", "Architecture", "Plan the solution"],
  ["tools", "Tools", "Choose dependencies"],
  ["cost", "Cost", "Estimate services"],
  ["preview", "Preview", "Create proposal PDF"],
  ["coding", "Coding", "Generate source code"],
  ["bug_report", "Bug Report", "Check generated code"],
  ["bug_fix", "Bug Fix", "Fix reported issues"],
  ["package", "Package", "Create code ZIP"],
];

let session = null;
let runningAgent = null;

const messages = document.querySelector("#messages");
const agentList = document.querySelector("#agent-list");
const form = document.querySelector("#query-form");
const queryInput = document.querySelector("#query");
const techHintInput = document.querySelector("#tech-hint");
const sendButton = document.querySelector("#send-query");

function makeElement(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}

function labelFor(key) {
  return key.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function addSection(parent, title) {
  const section = makeElement("section", "output-section");
  section.append(makeElement("h3", "output-label", labelFor(title)));
  parent.append(section);
  return section;
}

function addTextList(parent, items) {
  const list = makeElement("ul", "pretty-list");
  items.forEach((item) => list.append(makeElement("li", "", String(item))));
  parent.append(list);
}

function addObjectTable(parent, rows) {
  const columns = [...new Set(rows.flatMap((row) => Object.keys(row)))];
  const wrapper = makeElement("div", "table-wrap");
  const table = makeElement("table", "output-table");
  const header = document.createElement("tr");
  columns.forEach((column) => header.append(makeElement("th", "", labelFor(column))));
  table.append(header);
  rows.forEach((row) => {
    const tableRow = document.createElement("tr");
    columns.forEach((column) => {
      const value = row[column];
      tableRow.append(makeElement("td", "", typeof value === "object" ? JSON.stringify(value) : String(value ?? "—")));
    });
    table.append(tableRow);
  });
  wrapper.append(table); parent.append(wrapper);
}

function addCodeFiles(parent, files) {
  const grid = makeElement("div", "code-files");
  files.forEach((file) => {
    const card = makeElement("article", "code-card");
    const header = makeElement("div", "code-header");
    header.append(makeElement("strong", "", file.path || "untitled file"));
    const actions = makeElement("div", "code-actions");
    actions.append(makeElement("span", "language-pill", file.language || "code"));
    const copyButton = makeElement("button", "copy-button", "Copy");
    copyButton.type = "button";
    copyButton.addEventListener("click", async () => {
      await navigator.clipboard.writeText(file.content || "");
      copyButton.textContent = "Copied";
      setTimeout(() => { copyButton.textContent = "Copy"; }, 1200);
    });
    actions.append(copyButton); header.append(actions);
    card.append(header, makeElement("pre", "code-content", file.content || "")); grid.append(card);
  });
  parent.append(grid);
}

async function downloadArtifact(artifact) {
  if (!session) throw new Error("Start a session before downloading an artifact.");
  const response = await fetch(API_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action: "download", session_id: session.session_id, artifact: artifact.id }),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || "Download failed.");
  }

  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement("a");
  link.href = url;
  link.download = artifact.filename || "download";
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function addDownloads(parent, artifacts) {
  const downloads = makeElement("div", "downloads");
  artifacts.forEach((artifact) => {
    if (!artifact?.id) return;
    const button = makeElement("button", "download-button", artifact.label || "Download file");
    button.type = "button";
    button.addEventListener("click", async () => {
      const label = button.textContent;
      button.disabled = true;
      button.textContent = "Preparing download…";
      try {
        await downloadArtifact(artifact);
      } catch (error) {
        addMessage("assistant", error.message, "Download failed");
      } finally {
        button.disabled = false;
        button.textContent = label;
      }
    });
    downloads.append(button);
  });
  parent.append(downloads);
}

function formatOutput(data) {
  const root = makeElement("div", "structured-output");
  if (!data || typeof data !== "object") return makeElement("p", "", String(data ?? "No output returned."));

  const summaryKey = ["feature_summary", "approach_summary", "estimated_monthly_total", "pdf_filename", "archive_name"]
    .find((key) => data[key]);
  if (summaryKey) root.append(makeElement("p", "output-summary", String(data[summaryKey])));

  Object.entries(data).forEach(([key, value]) => {
    if (key === summaryKey || value === null || value === undefined || value === "") return;
    const section = addSection(root, key);

    if (key === "downloads" && Array.isArray(value)) {
      addDownloads(section, value);
    } else if (key === "files" && Array.isArray(value)) {
      addCodeFiles(section, value);
    } else if (Array.isArray(value) && value.every((item) => typeof item !== "object")) {
      addTextList(section, value);
    } else if (Array.isArray(value) && value.every((item) => item && typeof item === "object")) {
      addObjectTable(section, value);
    } else if (typeof value === "object") {
      const details = makeElement("dl", "detail-grid");
      Object.entries(value).forEach(([nestedKey, nestedValue]) => {
        details.append(makeElement("dt", "", labelFor(nestedKey)));
        details.append(makeElement("dd", "", typeof nestedValue === "object" ? JSON.stringify(nestedValue) : String(nestedValue)));
      });
      section.append(details);
    } else if (typeof value === "boolean") {
      section.append(makeElement("span", `boolean-pill ${value ? "yes" : "no"}`, value ? "Yes" : "No"));
    } else {
      section.append(makeElement("p", "output-value", String(value)));
    }
  });
  return root;
}

function addMessage(type, content, title = "") {
  const message = makeElement("article", `message ${type}`);
  const avatar = makeElement("div", "avatar", type === "user" ? "YOU" : "AI");
  const bubble = makeElement("div", "bubble");
  if (title) bubble.append(makeElement("p", "result-title", title));
  bubble.append(typeof content === "string" ? makeElement("div", "message-text", content) : formatOutput(content));
  message.append(avatar, bubble); messages.append(message); messages.scrollTop = messages.scrollHeight;
  return message;
}

function renderAgents() {
  agentList.replaceChildren();
  const results = session?.results || {};
  agents.forEach(([id, label, helper], index) => {
    const result = results[id];
    const previous = agents[index - 1]?.[0];
    const isAllowed = index === 0 || results[previous]?.status === "success";
    const button = makeElement("button", `agent-button ${result?.status || ""}`);
    button.type = "button";
    button.disabled = !session || Boolean(runningAgent) || !isAllowed || result?.status === "success";
    button.innerHTML = `<span class="agent-number">${index + 1}</span><span class="agent-copy"><strong>${label}</strong><small>${result?.status === "success" ? "Complete" : result?.status === "error" ? "Try again" : helper}</small></span>`;
    button.addEventListener("click", () => runAgent(id, label)); agentList.append(button);
  });
}

async function request(payload) {
  const response = await fetch(API_URL, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(body.detail || "Request failed.");
  return body;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const query = queryInput.value.trim(); if (query.length < 3) return;
  sendButton.disabled = true; addMessage("user", query);
  try {
    const data = await request({ action: "start", query, tech_hint: techHintInput.value.trim() || null });
    session = data.session; addMessage("assistant", `${data.message} Session: ${session.session_id}`);
    queryInput.value = ""; techHintInput.value = "";
  } catch (error) { addMessage("assistant", error.message, "Could not start session"); }
  finally { sendButton.disabled = false; renderAgents(); }
});

function removeWorkingMessage(label) {
  [...messages.querySelectorAll(".message.assistant")].find((message) => {
    const title = message.querySelector(".result-title")?.textContent;
    const text = message.querySelector(".message-text")?.textContent;
    return title === `${label} Agent` && text?.startsWith("Working");
  })?.remove();
}

async function runAgent(id, label) {
  runningAgent = id; renderAgents(); addMessage("assistant", "Working…", `${label} Agent`);
  try {
    const data = await request({ action: "run_agent", session_id: session.session_id, agent: id });
    session = data.session;
    if (data.agent_result.status === "success") addMessage("assistant", data.agent_result.output, `${label} Agent · complete`);
    else addMessage("assistant", data.agent_result.error || "Unknown error", `${label} Agent · failed`);
  } catch (error) { addMessage("assistant", error.message, `${label} Agent · failed`); }
  finally { removeWorkingMessage(label); runningAgent = null; renderAgents(); }
}

document.querySelector("#new-chat").addEventListener("click", () => {
  session = null; runningAgent = null; messages.replaceChildren();
  addMessage("assistant", "Tell me what you want to build. Then run each agent one by one from the left."); renderAgents(); queryInput.focus();
});

addMessage("assistant", "Tell me what you want to build. Then run each agent one by one from the left.");
renderAgents();
