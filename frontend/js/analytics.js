/**
 * Analytics.js - Comprehensive Traffic Enforcement Data Visualizations
 * Smart Highway Speed Radar & Ticket Generator
 */

const AnalyticsView = {
  charts: {
    classes: null,
    hours: null,
    histogram: null,
    fines: null
  },

  async load() {
    try {
      await Promise.all([
        this.loadMetrics(),
        this.loadClassesChart(),
        this.loadHourlyTrendChart(),
        this.loadHistogramChart(),
        this.loadFinesChart()
      ]);
    } catch (err) {
      console.error("Analytics load failed:", err);
    }
  },

  async loadMetrics() {
    const stats = await App.api("/api/dashboard");
    document.getElementById("analytics-avg-speed").textContent = `${stats.avg_speed || 0} km/h`;
    document.getElementById("analytics-max-speed").textContent = `${stats.max_speed || 0} km/h`;
    document.getElementById("analytics-limit").textContent = `${stats.speed_limit || 80} km/h`;
    document.getElementById("analytics-ticket-count").textContent = (stats.tickets_generated || 0).toLocaleString();
  },

  async loadClassesChart() {
    const data = await App.api("/api/analytics/categories");
    const ctx = document.getElementById("chart-analytics-classes");
    if (!ctx) return;

    if (this.charts.classes) this.charts.classes.destroy();

    this.charts.classes = new Chart(ctx, {
      type: "bar",
      data: {
        labels: data.labels,
        datasets: [
          {
            label: "Compliant (Safe)",
            data: data.safe,
            backgroundColor: "rgba(16, 185, 129, 0.75)",
            borderRadius: 4
          },
          {
            label: "Violations",
            data: data.violations,
            backgroundColor: "rgba(255, 71, 87, 0.75)",
            borderRadius: 4
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
            stacked: true,
            grid: { display: false },
            ticks: { color: "#64748b", font: { size: 10 } }
          },
          y: {
            stacked: true,
            grid: { color: "rgba(255, 255, 255, 0.05)" },
            ticks: { color: "#64748b", font: { size: 10 } }
          }
        }
      }
    });
  },

  async loadHourlyTrendChart() {
    const data = await App.api("/api/analytics/hourly");
    const ctx = document.getElementById("chart-analytics-hours");
    if (!ctx) return;

    if (this.charts.hours) this.charts.hours.destroy();

    this.charts.hours = new Chart(ctx, {
      type: "bar",
      data: {
        labels: data.labels,
        datasets: [
          {
            label: "Violations Detected",
            data: data.violations,
            backgroundColor: "rgba(255, 71, 87, 0.8)",
            borderRadius: 3
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
            ticks: { color: "#64748b", font: { size: 9 }, maxRotation: 45 }
          },
          y: {
            grid: { color: "rgba(255, 255, 255, 0.05)" },
            ticks: { color: "#64748b", font: { size: 10 } }
          }
        }
      }
    });
  },

  async loadHistogramChart() {
    const data = await App.api("/api/analytics/distribution");
    const ctx = document.getElementById("chart-analytics-histogram");
    if (!ctx) return;

    if (this.charts.histogram) this.charts.histogram.destroy();

    this.charts.histogram = new Chart(ctx, {
      type: "line",
      data: {
        labels: data.labels,
        datasets: [
          {
            label: "Vehicle Frequency",
            data: data.counts,
            borderColor: "#00f0ff",
            backgroundColor: "rgba(0, 240, 255, 0.12)",
            borderWidth: 2,
            tension: 0.3,
            fill: true,
            pointBackgroundColor: "#00f0ff",
            pointRadius: 4
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
            grid: { color: "rgba(255, 255, 255, 0.05)" },
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
    const ctx = document.getElementById("chart-analytics-fines");
    if (!ctx) return;

    if (this.charts.fines) this.charts.fines.destroy();

    this.charts.fines = new Chart(ctx, {
      type: "doughnut",
      data: {
        labels: data.brackets,
        datasets: [
          {
            data: data.ticket_counts,
            backgroundColor: [
              "#3b82f6",
              "#00f0ff",
              "#f59e0b",
              "#ef4444",
              "#b91c1c"
            ],
            borderColor: "#0b111e",
            borderWidth: 2
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: "60%",
        plugins: {
          legend: {
            position: "right",
            labels: { color: "#94a3b8", font: { size: 11 } }
          }
        }
      }
    });
  }
};

window.AnalyticsView = AnalyticsView;
