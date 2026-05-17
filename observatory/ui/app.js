(function () {
  "use strict";

  function byId(id) { return document.getElementById(id); }
  function safeNumber(value, fallback) { var n = Number(value); return Number.isFinite(n) ? n : fallback; }
  function formatNumber(value) { return safeNumber(value, 0).toLocaleString(); }
  function escapeText(value) { return String(value == null ? "" : value); }

  function getData() {
    var data = window.CODEFARM_DATA || {};
    return {
      state: data.state && typeof data.state === "object" ? data.state : {},
      metrics: data.metrics && typeof data.metrics === "object" ? data.metrics : {},
      recentLog: Array.isArray(data.recent_log) ? data.recent_log : []
    };
  }

  function organismEntries(state) {
    var organisms = state.organisms && typeof state.organisms === "object" ? state.organisms : {};
    return Object.keys(organisms).sort().map(function (id) {
      var organism = organisms[id] && typeof organisms[id] === "object" ? organisms[id] : {};
      organism.id = organism.id || id;
      return organism;
    });
  }

  function isSchedulable(metrics, organism) {
    var list = Array.isArray(metrics.schedulable_organisms) ? metrics.schedulable_organisms : [];
    if (list.length) return list.indexOf(organism.id) !== -1;
    return organism.id && organism.id.indexOf("org-") === 0;
  }

  function renderKpis(state, metrics, organisms) {
    var active = Array.isArray(metrics.schedulable_organisms) ? metrics.schedulable_organisms.length : organisms.length;
    var total = safeNumber(metrics.total_state_organisms, organisms.length);
    var pool = metrics.available_calories != null ? metrics.available_calories : ((state.nutrient_pool || {}).available_calories || 0);
    var lifetime = metrics.lifetime_nutrients != null ? metrics.lifetime_nutrients : ((state.metrics || {}).lifetime_nutrients || 0);
    var deaths = metrics.deaths_24h != null ? metrics.deaths_24h : ((state.metrics || {}).deaths_24h || 0);
    byId("ecosystemStatus").textContent = active > 0 ? "Ecosystem alive" : "Ecosystem empty";
    byId("populationValue").textContent = formatNumber(active);
    byId("populationMeta").textContent = formatNumber(total) + " total records";
    byId("poolValue").textContent = formatNumber(pool);
    byId("yieldValue").textContent = formatNumber(lifetime);
    byId("deathValue").textContent = formatNumber(deaths);
    byId("cycleBadge").textContent = "Cycle " + formatNumber(state.cycle || 0);
    byId("rootPath").textContent = state.codefarm_root || "G:\\codefarm";
  }

  function renderMap(state, metrics, organisms) {
    var map = byId("ecosystemMap");
    map.innerHTML = "";
    var pool = ((state.nutrient_pool || {}).available_calories || metrics.available_calories || 0);
    var core = document.createElement("div");
    core.className = "pool-core";
    core.innerHTML = "<div><strong>" + formatNumber(pool) + "</strong><span>calories</span></div>";
    map.appendChild(core);
    var count = Math.max(organisms.length, 1);
    organisms.forEach(function (organism, index) {
      var angle = (Math.PI * 2 * index) / count - Math.PI / 2;
      var left = 50 + Math.cos(angle) * 36;
      var top = 50 + Math.sin(angle) * 33;
      var status = String(organism.status || "unknown").toLowerCase();
      var node = document.createElement("div");
      node.className = "organism-node " + (isSchedulable(metrics, organism) ? status : "observed");
      node.style.left = "calc(" + left.toFixed(2) + "% - 59px)";
      node.style.top = "calc(" + top.toFixed(2) + "% - 38px)";
      node.innerHTML = "<strong>" + escapeText(organism.id) + "</strong><span>" + escapeText(organism.status || "unknown") + "</span><span>Energy " + formatNumber(organism.energy || 0) + "</span>";
      map.appendChild(node);
    });
  }

  function renderQuality(state, metrics) {
    var chart = byId("qualityChart");
    var history = (((state.metrics || {}).quality_history) || []).filter(function (item) { return item && typeof item === "object"; });
    chart.innerHTML = "";
    byId("qualityBadge").textContent = formatNumber(metrics.quality_samples || history.length) + " samples";
    history.slice(-18).forEach(function (item) {
      var q = safeNumber(item.quality, 0);
      var bar = document.createElement("div");
      bar.className = "quality-bar" + (q < 50 ? " low" : q < 80 ? " mid" : "");
      bar.style.height = Math.max(8, Math.min(100, q)) + "%";
      bar.setAttribute("data-label", escapeText(item.organism || "unknown") + " " + q.toFixed(1));
      chart.appendChild(bar);
    });
    if (!history.length) chart.textContent = "No quality samples yet.";
  }

  function renderTable(metrics, organisms) {
    var rows = byId("organismRows");
    rows.innerHTML = "";
    var observed = Array.isArray(metrics.observed_artifacts) ? metrics.observed_artifacts : [];
    byId("artifactBadge").textContent = formatNumber(observed.length) + " observed artifacts";
    organisms.forEach(function (org) {
      var genome = org.genome && typeof org.genome === "object" ? org.genome : {};
      var tr = document.createElement("tr");
      tr.innerHTML = "<td>" + escapeText(org.id) + "</td>" +
        "<td>" + escapeText(org.status || "unknown") + "</td>" +
        "<td>" + formatNumber(org.energy || 0) + "</td>" +
        "<td>" + formatNumber(org.lifetime_nutrients || 0) + "</td>" +
        "<td>" + escapeText(genome.strain || "observed") + "</td>" +
        "<td>" + safeNumber(org.last_quality, 0).toFixed(1) + "</td>" +
        "<td class=\"muted\">" + escapeText(org.last_task || "manual artifact") + "</td>";
      rows.appendChild(tr);
    });
  }


  function calculateMonthlyValue(state, metrics) {
    var billing = state.billing || metrics.billing || {};
    var actions = safeNumber(billing.automation_actions, 0);
    var prevented = safeNumber(billing.incidents_prevented, 0);
    var uptime = safeNumber(billing.uptime_percentage, 100);
    var actionValue = actions * 0.10;
    var incidentValue = prevented * 50;
    var uptimeBonus = uptime > 99.9 ? 200 : 0;
    return (actionValue + incidentValue + uptimeBonus).toFixed(2);
  }

  function renderCommercial(state, metrics) {
    var billing = state.billing || metrics.billing || {};
    var infra = state.infrastructure || metrics.infrastructure || {};
    byId("tenantBadge").textContent = "tenant " + (state.tenant_id || metrics.tenant_id || "demo");
    byId("autoActions").textContent = formatNumber(billing.automation_actions || 0);
    byId("incidentsPrevented").textContent = formatNumber(billing.incidents_prevented || 0);
    byId("uptimePct").textContent = safeNumber(billing.uptime_percentage, 100).toFixed(2) + "%";
    byId("monthlyValue").textContent = "$" + (billing.monthly_rate != null ? safeNumber(billing.monthly_rate, 0).toFixed(2) : calculateMonthlyValue(state, metrics));
    byId("vmsProvisioned").textContent = formatNumber(infra.vms_provisioned || 0);
    byId("servicesDeployed").textContent = formatNumber(infra.services_deployed || 0);
  }
  function renderAlerts(metrics, organisms) {
    var list = byId("alertList");
    list.innerHTML = "";
    var alerts = [];
    var activeCount = Array.isArray(metrics.schedulable_organisms) ? metrics.schedulable_organisms.length : organisms.length;
    var pool = safeNumber(metrics.available_calories, 0);
    var starving = organisms.filter(function (org) { return safeNumber(org.energy, 0) < 120; });
    var lowQuality = organisms.filter(function (org) { return safeNumber(org.last_quality, 100) < 50; });
    if (activeCount < 3) alerts.push(["danger", "population_collapse", "Active organisms are below the resilience floor of 3."]);
    if (pool < 500) alerts.push(["warning", "nutrient_famine", "Pool depth is below the spawn cost threshold."]);
    if (starving.length) alerts.push(["warning", "starvation_watch", starving.map(function (o) { return o.id; }).join(", ") + " below energy threshold."]);
    if (lowQuality.length) alerts.push(["warning", "quality_plague_watch", lowQuality.map(function (o) { return o.id; }).join(", ") + " produced low-quality output."]);
    if (!alerts.length) alerts.push(["", "immune_nominal", "No active immune alerts in the current snapshot."]);
    alerts.forEach(function (alert) {
      var item = document.createElement("div");
      item.className = "alert-item " + alert[0];
      item.innerHTML = "<strong>" + alert[1] + "</strong><span>" + alert[2] + "</span>";
      list.appendChild(item);
    });
  }

  function renderLogs(logs) { byId("logOutput").textContent = logs.length ? logs.join("\n") : "No logs found."; }

  function render() {
    try {
      var data = getData();
      var organisms = organismEntries(data.state);
      renderKpis(data.state, data.metrics, organisms);
      renderMap(data.state, data.metrics, organisms);
      renderQuality(data.state, data.metrics);
      renderTable(data.metrics, organisms);
      renderCommercial(data.state, data.metrics);
      renderAlerts(data.metrics, organisms);
      renderLogs(data.recentLog);
    } catch (error) {
      byId("ecosystemStatus").textContent = "Snapshot read failed";
      byId("logOutput").textContent = String(error && error.stack ? error.stack : error);
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    byId("refreshView").addEventListener("click", render);
    render();
  });
}());

