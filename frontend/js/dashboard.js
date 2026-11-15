/**
 * Dashboard.js - Main KPI Telemetry, Charts, and Recent Violations
 * Smart Highway Speed Radar & Ticket Generator
 */

const DashboardView = {
  charts: {
    hourly: null,
    ratio: null,
    speedDist: null,
    fines: null
  },

  async load() {
    try {
      await Promise.all([
        this.loadKPIs(),
        this.loadHourlyChart(),
        this.loadRatioChart(),
        this.loadSpeedDistChart(),
        this.loadFinesChart(),
        this.loadRecentViolations()
      ]);
    } catch (err) {
      console.error("Dashboard load failed:", err);
    }
  },

  async loadKPIs() {
    const stats = await App.api("/api/dashboard");

    document.getElementById("kpi-total-vehicles").textContent = (stats.total_vehicles || 0).toLocaleString();
    document.getElementById("kpi-violations").textContent = (stats.total_violations || 0).toLocaleString();
    document.getElementById("kpi-safe-vehicles").textContent = (stats.total_safe || 0).toLocaleString();
    document.getElementById("kpi-tickets-count").textContent = (stats.tickets_generated || 0).toLocaleString();
    document.getElementById("kpi-total-fines").textContent = `${stats.currency_symbol || '$'}${(stats.total_fines || 0).toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
    document.getElementById("kpi-violation-rate").textContent = `${stats.violation_rate || 0}%`;
    document.getElementById("kpi-avg-speed").innerHTML = `${stats.avg_speed || 0} <span style="font-size: 14px; color: var(--text-muted)">${stats.unit || 'km/h'}</span>`;
    document.getElementById("kpi-speed-limit").textContent = `${stats.speed_limit} ${stats.unit || 'km/h'}`;

    // Update pulse dot in sidebar
    const pulseDot = document.getElementById("radar-pulse");
    const statusText = document.getElementById("radar-status-text");
    if (stats.is_processing) {
      pulseDot.className = "pulse-dot processing";
      statusText.textContent = "SCANNING";
    } else if (stats.total_vehicles > 0) {
      pulseDot.className = "pulse-dot";
      statusText.textContent = "ONLINE - ACTIVE";
    } else {
      pulseDot.className = "pulse-dot idle";
      statusText.textContent = "STANDBY";
    }
  },

  async loadHourlyChart() {
    const data = await App.api("/api/analytics/hourly");
    const ctx = document.getElementById("chart-hourly");
    if (!ctx) return;

    if (this.charts.hourly) {
      this.charts.hourly.destroy();
    }

    this.charts.hourly = new Chart(ctx, {
      type: "line",
      data: {
        labels: data.labels,
        datasets: [
          {
            label: "Speeding Violations",
            data: data.violations,
            borderColor: "#ff4757",
            backgroundColor: "rgba(255, 71, 87, 0.15)",
            borderWidth: 2,
            tension: 0.35,
            fill: true,
            pointBackgroundColor: "#ff4757",
            pointRadius: 3
          },
          {
            label: "Compliant Vehicles",
            data: data.safe,
            borderColor: "#10b981",
            backgroundColor: "transparent",
            borderWidth: 1.5,
            borderDash: [4, 4],
            tension: 0.35,
            pointRadius: 0
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: "top",
            labels: { color: "#94a3b8", font: { size: 11 } }
          }
        },
        scales: {
          x: {
            grid: { color: "rgba(255, 255, 255, 0.05)" },
            ticks: { color: "#64748b", font: { size: 10 } }
          },
          y: {
            grid: { color: "rgba(255, 255, 255, 0.05)" },
            ticks: { color: "#64748b", font: { size: 10 }, stepSize: 5 }
          }
        }
      }
    });
  },

  async loadRatioChart() {
    const stats = await App.api("/api/dashboard");
    const ctx = document.getElementById("chart-ratio");
    if (!ctx) return;

    if (this.charts.ratio) {
      this.charts.ratio.destroy();
    }

    const safe = stats.total_safe || 0;
    const vios = stats.total_violations || 0;
    const hasData = (safe + vios) > 0;

    this.charts.ratio = new Chart(ctx, {
      type: "doughnut",
      data: {
        labels: ["Compliant (Safe)", "Speeding Violations"],
        datasets: [
          {
            data: hasData ? [safe, vios] : [1, 0],
            backgroundColor: hasData ? ["#10b981", "#ff4757"] : ["#334155", "#1e293b"],
            borderColor: "#0b111e",
            borderWidth: 3
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: "72%",
        plugins: {
          legend: {
            position: "bottom",
            labels: { color: "#94a3b8", font: { size: 11 }, padding: 14 }
          }
        }
      }
    });
  },

  async loadSpeedDistChart() {
    const data = await App.api("/api/analytics/distribution");
    const ctx = document.getElementById("chart-speed-dist");
    if (!ctx) return;

    if (this.charts.speedDist) {
      this.charts.speedDist.destroy();
    }

    // Color bars: Cyan for <= limit, Red for > limit
    const bgColors = data.labels.map(label => {
      if (label.includes(">") || label.includes("80-") || label.includes("90-") || label.includes("100-") || label.includes("110-")) {
        return "rgba(255, 71, 87, 0.75)";
      }
      return "rgba(0, 240, 255, 0.65)";
    });

    this.charts.speedDist = new Chart(ctx, {
      type: "bar",
      data: {
        labels: data.labels,
        datasets: [
          {
            label: "Vehicle Count",
            data: data.counts,
            backgroundColor: bgColors,
            borderRadius: 4
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false }
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: { color: "#64748b", font: { size: 10 } }
          },
          y: {
            grid: { color: "rgba(255, 255, 255, 0.05)" },
            ticks: { color: "#64748b", font: { size: 10 } }
          }
        }
      }
    });
  },

  async loadFinesChart() {
    const data = await App.api("/api/analytics/fines");
    const ctx = document.getElementById("chart-fines");
    if (!ctx) return;

    if (this.charts.fines) {
      this.charts.fines.destroy();
    }

    this.charts.fines = new Chart(ctx, {
      type: "bar",
      data: {
        labels: data.brackets,
        datasets: [
          {
            label: "Total Fines ($)",
            data: data.total_fines_by_bracket,
            backgroundColor: "rgba(245, 158, 11, 0.7)",
            borderRadius: 4
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: { display: false }
        },
        scales: {
          x: {
            grid: { display: false },
            ticks: { color: "#64748b", font: { size: 10 } }
          },
          y: {
            grid: { color: "rgba(255, 255, 255, 0.05)" },
            ticks: {
              color: "#64748b",
              font: { size: 10 },
              callback: val => `$${val}`
            }
          }
        }
      }
    });
  },

  async loadRecentViolations() {
    const res = await App.api("/api/violations?limit=8");
    const tbody = document.getElementById("dashboard-violations-tbody");
    if (!tbody) return;

    if (!res.items || res.items.length === 0) {
      tbody.innerHTML = `<tr><td colspan="8" style="text-align: center; color: var(--text-muted); padding: 24px;">No violation records found. Load data or run radar scan.</td></tr>`;
      return;
    }

    tbody.innerHTML = res.items.map(v => {
      return `
        <tr>
          <td><span class="badge badge-violation">${v.violation_id}</span></td>
          <td><strong>#${v.vehicle_id}</strong></td>
          <td><span class="speed-tag violation">${v.recorded_speed.toFixed(1)} km/h</span></td>
          <td>${v.speed_limit.toFixed(1)} km/h</td>
          <td><span style="color: var(--red); font-weight: 600;">+${v.excess_speed.toFixed(1)} km/h</span></td>
          <td style="font-weight: 700; color: var(--amber);">$${v.fine.toFixed(2)}</td>
          <td style="color: var(--text-muted); font-size: 11px;">${v.timestamp}</td>
          <td>
            <button class="btn btn-primary btn-sm btn-issue-ticket" data-vio-id="${v.violation_id}">
              Issue Ticket
            </button>
          </td>
        </tr>
      `;
    }).join("");

    // Hook issue ticket buttons
    tbody.querySelectorAll(".btn-issue-ticket").forEach(btn => {
      btn.addEventListener("click", async () => {
        const vioId = btn.getAttribute("data-vio-id");
        try {
          btn.disabled = true;
          btn.textContent = "Issuing...";
          const res = await App.api(`/api/tickets/generate?violation_id=${vioId}`, { method: "POST" });
          App.showToast(`Ticket generated: ${res.tickets[0]}`, "success");
          btn.textContent = "Issued";
          btn.classList.remove("btn-primary");
          btn.classList.add("btn-secondary");
          await DashboardView.loadKPIs();
        } catch (err) {
          App.showToast(`Failed to generate ticket: ${err.message}`, "danger");
          btn.disabled = false;
          btn.textContent = "Issue Ticket";
        }
      });
    });

    // Hook Issue All button
    document.getElementById("btn-quick-generate-all")?.addEventListener("click", async () => {
      try {
        App.showToast("Generating official citation tickets for all violations...", "info");
        const res = await App.api("/api/tickets/generate", { method: "POST" });
        App.showToast(`Generated ${res.tickets_generated} tickets successfully!`, "success");
        await DashboardView.load();
      } catch (err) {
        App.showToast(`Generation failed: ${err.message}`, "danger");
      }
    });
  }
};

window.DashboardView = DashboardView;
