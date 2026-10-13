"use strict";

const $ = (id) => document.getElementById(id);
let lastAnalysis = null;

function notify(message, error = false) {
  $("message").textContent = message;
  $("message").classList.toggle("error", error);
}

function parseCSV(source) {
  const text = source.replace(/^\uFEFF/, "");
  const rows = [];
  let field = "", record = [], quoted = false, endedQuote = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (quoted) {
      if (ch === '"' && text[i + 1] === '"') { field += '"'; i++; }
      else if (ch === '"') { quoted = false; endedQuote = true; }
      else { field += ch; }
    } else if (ch === ',' || ch === '\n' || ch === '\r') {
      record.push(field);
      field = "";
      endedQuote = false;
      if (ch !== ',') {
        if (record.some((cell) => cell.trim() !== "")) rows.push(record);
        record = [];
        if (ch === '\r' && text[i + 1] === '\n') i++;
      }
    } else if (ch === '"' && field === "" && !endedQuote) {
      quoted = true;
    } else if (endedQuote) {
      if (ch !== ' ' && ch !== '\t') throw new Error("Invalid content after a quoted CSV field.");
    } else if (ch === '"') {
      throw new Error("Unexpected quote in CSV field.");
    } else {
      field += ch;
    }
  }
  if (quoted) throw new Error("Unterminated quoted CSV field.");
  record.push(field);
  if (record.some((cell) => cell.trim() !== "")) rows.push(record);
  if (!rows.length) throw new Error("CSV is empty.");
  const header = rows.shift().map((cell) => cell.trim().toLowerCase());
  const columns = ["psm_id", "score", "is_decoy"].map((name) => {
    const count = header.filter((h) => h === name).length;
    if (count !== 1) throw new Error("CSV requires exactly one " + name + " column.");
    return header.indexOf(name);
  });
  if (!rows.length) throw new Error("CSV contains no PSMs.");
  if (rows.length > 50000) throw new Error("Maximum 50,000 PSMs per calculation.");
  return rows.map((record, index) => {
    if (record.length !== header.length) throw new Error("CSV row " + (index + 2) + " has an incorrect number of columns.");
    return {
      psm_id: record[columns[0]],
      score: record[columns[1]],
      is_decoy: record[columns[2]]
    };
  });
}

function parseDecoy(value) {
  const label = String(value).trim().toLowerCase();
  if (["true", "1", "yes", "decoy"].includes(label)) return true;
  if (["false", "0", "no", "target"].includes(label)) return false;
  throw new Error("Invalid is_decoy value: use true/false, 1/0, yes/no, or target/decoy.");
}

function analyzePSMs(input, alpha) {
  if (!Number.isFinite(alpha) || alpha <= 0 || alpha > 1) throw new Error("α must be greater than 0 and at most 1.");
  const seen = new Set();
  const rows = input.map((raw, index) => {
    const id = raw.psm_id;
    if (typeof id !== "string" || id.length > 256 || !/^[A-Za-z0-9][A-Za-z0-9._:-]*$/.test(id)) {
      throw new Error("Row " + (index + 2) + ": invalid psm_id (letters, numbers, dot, colon, dash, underscore only).");
    }
    if (seen.has(id)) throw new Error("Duplicate psm_id " + id + ": input must contain one winning match per spectrum.");
    seen.add(id);
    if (typeof raw.score !== "string" || !raw.score.trim()) throw new Error("Row " + (index + 2) + ": missing score.");
    const score = Number(raw.score);
    if (!Number.isFinite(score)) throw new Error("Row " + (index + 2) + ": nonfinite score.");
    return { psm_id: id, score, is_decoy: parseDecoy(raw.is_decoy) };
  });
  rows.sort((a, b) => b.score - a.score);
  const groups = [];
  let targets = 0, decoys = 0;
  for (const entry of rows) {
    if (!groups.length || groups[groups.length - 1].score !== entry.score) {
      groups.push({ score: entry.score, members: [], fdr: 1 });
    }
    const group = groups[groups.length - 1];
    group.members.push(entry);
    if (entry.is_decoy) decoys++; else targets++;
    group.fdr = targets ? Math.min(1, (decoys + 1) / targets) : 1;
  }
  let best = 1;
  for (let i = groups.length - 1; i >= 0; i--) {
    best = Math.min(best, groups[i].fdr);
    for (const entry of groups[i].members) {
      entry.q_value = best;
      entry.accepted = !entry.is_decoy && best <= alpha;
    }
  }
  const accepted = rows.filter((entry) => entry.accepted);
  return {
    rows, targets, decoys, accepted: accepted.length,
    threshold: accepted.length ? Math.min(...accepted.map((entry) => entry.score)) : null
  };
}

function showResults(result, alpha) {
  $("targets").textContent = String(result.targets);
  $("decoys").textContent = String(result.decoys);
  $("accepted").textContent = String(result.accepted);
  $("cutoff").textContent = result.threshold === null ? "No target wins pass the selected FDR threshold." :
    "Lowest accepted score: " + result.threshold + " (α = " + alpha + ")";
  const tbody = $("resultRows");
  tbody.replaceChildren();
  for (const item of result.rows.slice(0, 300)) {
    const tr = document.createElement("tr");
    for (const value of [item.psm_id, String(item.score), item.is_decoy ? "Decoy" : "Target", item.q_value.toFixed(6), item.accepted ? "Yes" : "No"]) {
      const td = document.createElement("td");
      td.textContent = value;
      if (item.accepted) td.classList.add("accepted");
      tr.appendChild(td);
    }
    tbody.appendChild(tr);
  }
  $("download").disabled = false;
  notify("Analyzed " + result.rows.length + " PSMs. Accepted " + result.accepted + " target matches at α = " + alpha + ".");
}

function exportResults() {
  if (!lastAnalysis) return;
  const output = ["psm_id,score,is_decoy,q_value,accepted"];
  for (const item of lastAnalysis.rows) {
    output.push([item.psm_id, item.score, item.is_decoy, item.q_value, item.accepted].join(","));
  }
  const blob = new Blob([output.join("\r\n") + "\r\n"], { type: "text/csv;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "psm_fdr_results.csv";
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

if (typeof document !== "undefined") {
$("csvFile").addEventListener("change", async (event) => {
  const file = event.target.files?.[0];
  if (!file) return;
  if (file.size > 5 * 1024 * 1024) {
    notify("File exceeds the 5 MB browser limit.", true);
    event.target.value = "";
    return;
  }
  try {
    $("csvText").value = await file.text();
    notify("Imported " + file.name + ". Select Calculate q-values.");
  } catch (_) {
    notify("Could not read file.", true);
  }
});
$("example").addEventListener("click", () => {
  $("csvFile").value = "";
  const example = ["psm_id,score,is_decoy"];
  for (let i = 0; i < 15; i++) example.push("target_" + (i + 1) + "," + (100 - i) + ",false");
  example.push("decoy_1,70,true", "target_16,68,false", "decoy_2,60,true");
  $("csvText").value = example.join("\n");
  notify("Synthetic example loaded. It is not experimental data.");
});
$("analyze").addEventListener("click", () => {
  try {
    const alpha = Number($("alpha").value);
    if (!$("alpha").value.trim()) throw new Error("Enter an FDR threshold α.");
    if (new Blob([$("csvText").value]).size > 5 * 1024 * 1024) throw new Error("Input exceeds 5 MB.");
    const input = parseCSV($("csvText").value);
    lastAnalysis = analyzePSMs(input, alpha);
    showResults(lastAnalysis, alpha);
  } catch (error) {
    lastAnalysis = null;
    $("download").disabled = true;
    notify(error.message || "Analysis failed.", true);
  }
});
$("download").addEventListener("click", exportResults);
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { parseCSV, parseDecoy, analyzePSMs };
}

