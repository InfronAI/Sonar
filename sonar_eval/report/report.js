"use strict";
for (const view of document.querySelectorAll("[data-list]")) {
  const rows = [...view.querySelectorAll("tbody tr")];
  const tools = view.querySelector(".tools");
  if (!tools || !rows.length) continue;
  tools.hidden = false;
  const query = tools.querySelector("input");
  const selectors = [...tools.querySelectorAll("select")];
  const pager = view.querySelector(".pager");
  const prev = pager.querySelector("[data-prev]");
  const next = pager.querySelector("[data-next]");
  const pageSize = 15;
  let page = 0;
  function refresh() {
    const needle = query.value.trim().toLocaleLowerCase();
    const matching = rows.filter(row => row.textContent.toLocaleLowerCase().includes(needle) &&
      selectors.every(select => !select.value || row.dataset[select.name] === select.value));
    for (const row of rows) row.hidden = true;
    const pages = Math.ceil(matching.length / pageSize);
    page = Math.min(page, Math.max(0, pages - 1));
    for (const row of matching.slice(page * pageSize, (page + 1) * pageSize)) row.hidden = false;
    pager.hidden = false;
    pager.querySelector("output").textContent = matching.length ?
      (page * pageSize + 1) + "–" + Math.min((page + 1) * pageSize, matching.length) + " / " + matching.length + " results" : "No matching records";
    prev.disabled = page === 0;
    next.disabled = page + 1 >= pages;
    prev.hidden = next.hidden = pages <= 1;
  }
  tools.addEventListener("input", () => { page = 0; refresh(); });
  prev.addEventListener("click", () => { page--; refresh(); });
  next.addEventListener("click", () => { page++; refresh(); });
  function revealLinkedTrial() {
    const index = rows.findIndex(row => row.id && "#" + row.id === location.hash);
    if (index < 0) return false;
    query.value = "";
    for (const select of selectors) select.value = "";
    page = Math.floor(index / pageSize);
    refresh();
    rows[index].scrollIntoView({ block: "center" });
    return true;
  }
  window.addEventListener("hashchange", revealLinkedTrial);
  if (!revealLinkedTrial()) refresh();
}
for (const chooser of document.querySelectorAll("[data-trend-picker]")) {
  chooser.hidden = false;
  const select = chooser.querySelector("select");
  function refresh() {
    for (const line of chooser.parentElement.querySelectorAll("[data-trend]")) {
      line.hidden = line.dataset.trend !== select.value;
    }
  }
  select.addEventListener("change", refresh);
  refresh();
}
for (const group of document.querySelectorAll("[data-rank-switch]")) {
  const tools = group.querySelector(":scope > .rank-tools");
  if (!tools) continue;
  const panels = group.querySelectorAll(":scope > [data-rank-option]");
  function showSelection() {
    const choice = tools.querySelector("select, input:checked").value;
    for (const panel of panels) panel.hidden = panel.dataset.rankOption !== choice;
  }
  tools.hidden = false;
  tools.addEventListener("change", showSelection);
  showSelection();
}
