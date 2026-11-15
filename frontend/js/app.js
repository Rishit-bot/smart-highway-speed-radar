/**
 * App.js - Core Application Router, State Management, and API Client
 * Smart Highway Speed Radar & Ticket Generator
 */

const App = {
  currentView: "dashboard",
  settings: {},
  healthCheckTimer: null,

  // Global API Client
  async api(endpoint, options = {}) {
    const url = endpoint.startsWith("http") ? endpoint : endpoint;
    const defaultHeaders = {
      "Accept": "application/json"
    };

    if (!(options.body instanceof FormData)) {
      defaultHeaders["Content-Type"] = "application/json";
    }

    const config = {
      ...options,
      headers: {
        ...defaultHeaders,
        ...(options.headers || {})
      }
    };

    try {
      const response = await fetch(url, config);
      const isJson = (response.headers.get("content-type") || "").includes("application/json");
      const data = isJson ? await response.json() : await response.text();

      if (!response.ok) {
        const errorMsg = (data && data.detail) || data.message || `HTTP ${response.status}: ${response.statusText}`;
        throw new Error(errorMsg);
      }
      return data;
    } catch (err) {
      console.error(`API Error on ${endpoint}:`, err);
      throw err;
    }
  },

  // Toast Notification System
  showToast(message, type = "info", duration = 4000) {
    const container = document.getElementById("toast-container");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = `toast ${type}`;

    let iconSvg = "";
    if (type === "success") {
      iconSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>`;
    } else if (type === "danger") {
      iconSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>`;
    } else {
      iconSvg = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>`;
    }

    toast.innerHTML = `
      ${iconSvg}
      <div style="flex: 1;">${message}</div>
    `;

    container.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transform = "translateX(40px)";
      toast.style.transition = "all 0.25s ease";
      setTimeout(() => toast.remove(), 260);
    }, duration);
  },

  // Initialize Application
  async init() {
    this.initClock();
    this.initNavigation();
    this.initModals();
    this.initSettingsForm();
    this.initDataSources();

    await this.checkHealth();
    await this.loadSettings();

    // Load initial view data
    this.switchView("dashboard");
  },

  // Clock
  initClock() {
    const el = document.getElementById("current-datetime");
    const update = () => {
      const now = new Date();
      el.textContent = now.toLocaleDateString() + " " + now.toLocaleTimeString();
    };
    update();
    setInterval(update, 1000);
  },

  // Navigation Routing
  initNavigation() {
    const navItems = document.querySelectorAll(".nav-item");
    navItems.forEach(item => {
      item.addEventListener("click", (e) => {
        e.preventDefault();
        const targetView = item.getAttribute("data-view");
        this.switchView(targetView);
      });
    });
  },

  switchView(viewName) {
    this.currentView = viewName;

    // Update active nav link
    document.querySelectorAll(".nav-item").forEach(item => {
      if (item.getAttribute("data-view") === viewName) {
        item.classList.add("active");
      } else {
        item.classList.remove("active");
      }
    });

    // Update view sections
    document.querySelectorAll(".view-section").forEach(sec => {
      sec.classList.remove("active");
    });
    const targetSection = document.getElementById(`view-${viewName}`);
    if (targetSection) {
      targetSection.classList.add("active");
    }

    // Update top bar title
    const titles = {
      dashboard: "Enforcement Dashboard",
      radar: "Radar Monitoring & HUD",
      vehicles: "Vehicle Observation Records",
      tickets: "Electronic Citations (E-Tickets)",
      analytics: "Traffic Enforcement Analytics",
      datasources: "NGSIM Data Ingestion",
      settings: "Radar Configuration & System Settings"
    };
    document.getElementById("page-title").textContent = titles[viewName] || "Speed Radar System";

    // Trigger view-specific data refresh
    if (viewName === "dashboard" && window.DashboardView) {
      DashboardView.load();
    } else if (viewName === "radar" && window.RadarView) {
      RadarView.load();
    } else if (viewName === "vehicles" && window.VehiclesView) {
      VehiclesView.load();
    } else if (viewName === "tickets" && window.TicketsView) {
      TicketsView.load();
    } else if (viewName === "analytics" && window.AnalyticsView) {
      AnalyticsView.load();
    }
  },

  // Backend Health Check
  async checkHealth() {
    try {
      const health = await this.api("/api/health");
      const pill = document.getElementById("backend-status-pill");
      pill.innerHTML = `<div class="pulse-dot" style="width: 7px; height: 7px;"></div> BACKEND ONLINE`;
      pill.style.borderColor = "var(--border-green)";
      pill.style.color = "var(--green)";
      return true;
    } catch (err) {
      const pill = document.getElementById("backend-status-pill");
      pill.innerHTML = `<div class="pulse-dot" style="width: 7px; height: 7px; background: var(--red); box-shadow: 0 0 8px var(--red);"></div> OFFLINE`;
      pill.style.borderColor = "var(--border-red)";
      pill.style.color = "var(--red)";
      return false;
    }
  },

  // Load Settings
  async loadSettings() {
    try {
      this.settings = await this.api("/api/settings");

      // Update badge
      const srcName = (this.settings.dataset_source || "DEMO").toUpperCase();
      document.getElementById("source-name").textContent = srcName;

      // Populate form
      document.getElementById("setting-speed-limit").value = this.settings.speed_limit || 80;
      document.getElementById("setting-base-fine").value = this.settings.base_fine || 500;
      document.getElementById("setting-fine-per-kmh").value = this.settings.fine_per_kmh || 50;
      document.getElementById("setting-camera-id").value = this.settings.camera_id || "RADAR-HWY-101-N";
      document.getElementById("setting-location-name").value = this.settings.location_name || "Interstate 80";
      document.getElementById("setting-output-dir").value = this.settings.ticket_output_dir || "generated_tickets";

      // Update HUD elements
      const limitDisplay = `${this.settings.speed_limit} ${this.settings.unit || 'km/h'}`;
      const hudEl = document.getElementById("radar-hud-limit");
      if (hudEl) hudEl.textContent = limitDisplay;
      const camEl = document.getElementById("hud-cam-id");
      if (camEl) camEl.textContent = this.settings.camera_id;
    } catch (err) {
      console.error("Failed to load settings:", err);
    }
  },

  // Settings Form Submit
  initSettingsForm() {
    const form = document.getElementById("settings-form");
    if (!form) return;

    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const payload = {
        speed_limit: parseFloat(document.getElementById("setting-speed-limit").value),
        base_fine: parseFloat(document.getElementById("setting-base-fine").value),
        fine_per_kmh: parseFloat(document.getElementById("setting-fine-per-kmh").value),
        camera_id: document.getElementById("setting-camera-id").value.trim(),
        location_name: document.getElementById("setting-location-name").value.trim()
      };

      try {
        const res = await this.api("/api/settings", {
          method: "PUT",
          body: JSON.stringify(payload)
        });
        this.settings = res.settings;
        this.showToast("Radar parameters updated and saved successfully.", "success");
        await this.loadSettings();
      } catch (err) {
        this.showToast(`Failed to update settings: ${err.message}`, "danger");
      }
    });
  },

  // Modals & Reset Confirmation
  initModals() {
    // Ticket Modal
    const ticketModal = document.getElementById("ticket-modal");
    document.getElementById("btn-close-ticket-modal")?.addEventListener("click", () => {
      ticketModal.classList.remove("active");
    });
    document.getElementById("btn-dismiss-ticket-modal")?.addEventListener("click", () => {
      ticketModal.classList.remove("active");
    });

    // Reset Modal
    const resetModal = document.getElementById("reset-modal");
    document.getElementById("btn-open-reset-modal")?.addEventListener("click", () => {
      resetModal.classList.add("active");
    });
    document.getElementById("btn-close-reset-modal")?.addEventListener("click", () => {
      resetModal.classList.remove("active");
    });
    document.getElementById("btn-cancel-reset")?.addEventListener("click", () => {
      resetModal.classList.remove("active");
    });

    document.getElementById("btn-confirm-reset")?.addEventListener("click", async () => {
      try {
        await this.api("/api/database/reset", {
          method: "POST",
          body: JSON.stringify({ confirm: true })
        });
        resetModal.classList.remove("active");
        this.showToast("Database and citations reset to clean factory state.", "success");
        if (window.DashboardView) DashboardView.load();
        if (window.VehiclesView) VehiclesView.load();
        if (window.TicketsView) TicketsView.load();
      } catch (err) {
        this.showToast(`Reset failed: ${err.message}`, "danger");
      }
    });
  },

  // Data Sources Handlers
  initDataSources() {
    // Demo source
    document.getElementById("btn-load-demo-source")?.addEventListener("click", async () => {
      try {
        this.showToast("Generating and processing synthetic NGSIM telemetry...", "info");
        const res = await this.api("/api/dataset/process", {
          method: "POST",
          body: JSON.stringify({ source: "demo" })
        });
        this.showToast(`Processed ${res.result.total_vehicles} vehicles (${res.result.violations_detected} violations).`, "success");
        await this.loadSettings();
        this.switchView("dashboard");
      } catch (err) {
        this.showToast(`Failed to load demo telemetry: ${err.message}`, "danger");
      }
    });

    // Sample CSV
    document.getElementById("btn-load-sample-csv")?.addEventListener("click", async () => {
      try {
        this.showToast("Ingesting bundled sample_ngsim.csv...", "info");
        const res = await this.api("/api/dataset/process", {
          method: "POST",
          body: JSON.stringify({ source: "csv" })
        });
        this.showToast(`Successfully processed CSV: ${res.result.total_vehicles} vehicles analyzed.`, "success");
        await this.loadSettings();
        this.switchView("dashboard");
      } catch (err) {
        this.showToast(`Failed to load sample CSV: ${err.message}`, "danger");
      }
    });

    // File input trigger
    const fileInput = document.getElementById("csv-file-input");
    document.getElementById("btn-choose-csv")?.addEventListener("click", () => {
      fileInput.click();
    });

    fileInput?.addEventListener("change", async (e) => {
      const file = e.target.files[0];
      if (!file) return;

      const formData = new FormData();
      formData.append("file", file);

      try {
        this.showToast(`Uploading and validating ${file.name}...`, "info");
        const res = await this.api("/api/dataset/upload", {
          method: "POST",
          body: formData
        });
        this.showToast(`CSV Uploaded: ${res.records_processed} vehicles processed!`, "success");
        await this.loadSettings();
        this.switchView("dashboard");
      } catch (err) {
        this.showToast(`Upload failed: ${err.message}`, "danger");
      } finally {
        fileInput.value = "";
      }
    });

    // Socrata DOT API
    document.getElementById("btn-fetch-api")?.addEventListener("click", async () => {
      try {
        this.showToast("Contacting DOT Socrata endpoint (https://data.transportation.gov)...", "info");
        const res = await this.api("/api/dataset/process", {
          method: "POST",
          body: JSON.stringify({ source: "api" })
        });
        this.showToast(`DOT API Success: ${res.result.total_vehicles} vehicles retrieved!`, "success");
        await this.loadSettings();
        this.switchView("dashboard");
      } catch (err) {
        this.showToast(`API Connection failed: ${err.message}`, "danger", 6000);
      }
    });
  }
};

window.addEventListener("DOMContentLoaded", () => {
  App.init();
});
