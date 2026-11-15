/**
 * Radar.js - Radar Telemetry Stream, Simulation Controls, and Live HUD
 * Smart Highway Speed Radar & Ticket Generator
 */

const RadarView = {
  isStreaming: false,
  streamInterval: null,
  cachedVehicles: [],
  currentIndex: 0,

  async load() {
    await this.updateStatus();
    this.initControls();
  },

  async updateStatus() {
    try {
      const status = await App.api("/api/radar/status");
      const hudState = document.getElementById("hud-state-text");
      const hudCount = document.getElementById("hud-count-text");
      const hudCam = document.getElementById("hud-cam-id");
      const hudLimit = document.getElementById("radar-hud-limit");

      if (hudState) hudState.textContent = status.is_processing ? "SCANNING HIGHWAY" : "STANDBY";
      if (hudCount) hudCount.textContent = status.records_processed;
      if (hudCam) hudCam.textContent = status.camera_id;
      if (hudLimit) hudLimit.textContent = `${status.speed_limit} km/h`;

      // Update source tag
      const modeTag = document.getElementById("radar-mode-tag");
      if (modeTag) {
        modeTag.textContent = `${(status.active_source || 'DEMO').toUpperCase()} PLAYBACK SIMULATION`;
      }
    } catch (err) {
      console.error("Failed to update radar status:", err);
    }
  },

  initControls() {
    const btnStart = document.getElementById("btn-radar-start");
    const btnStop = document.getElementById("btn-radar-stop");

    btnStart?.replaceWith(btnStart.cloneNode(true));
    btnStop?.replaceWith(btnStop.cloneNode(true));

    document.getElementById("btn-radar-start")?.addEventListener("click", async () => {
      await this.startScan();
    });

    document.getElementById("btn-radar-stop")?.addEventListener("click", async () => {
      await this.stopScan();
    });
  },

  async startScan() {
    try {
      App.showToast("Initiating radar scan and loading telemetry frames...", "info");
      const res = await App.api("/api/radar/start", {
        method: "POST",
        body: JSON.stringify({ source: App.settings.dataset_source || "demo" })
      });

      App.showToast(`Scan complete: ${res.data.total_vehicles} vehicles evaluated. Streaming playback...`, "success");
      await this.updateStatus();

      // Fetch vehicles to stream into observation feed
      const vehiclesRes = await App.api("/api/vehicles?page=1&page_size=40");
      this.cachedVehicles = vehiclesRes.items || [];
      this.currentIndex = 0;
      this.startObservationStream();
    } catch (err) {
      App.showToast(`Radar start failed: ${err.message}`, "danger");
    }
  },

  async stopScan() {
    try {
      if (this.streamInterval) {
        clearInterval(this.streamInterval);
        this.streamInterval = null;
      }
      this.isStreaming = false;

      const reticle = document.getElementById("radar-target-reticle");
      if (reticle) reticle.style.display = "none";

      await App.api("/api/radar/stop", { method: "POST" });
      await this.updateStatus();
      App.showToast("Radar simulation halted.", "info");
    } catch (err) {
      console.error("Stop failed:", err);
    }
  },

  startObservationStream() {
    if (this.streamInterval) clearInterval(this.streamInterval);
    this.isStreaming = true;

    const streamContainer = document.getElementById("radar-observation-stream");
    const reticle = document.getElementById("radar-target-reticle");
    const reticleTag = document.getElementById("radar-target-tag");
    const viewport = document.getElementById("radar-viewport");
    if (streamContainer) streamContainer.innerHTML = "";

    let displayedCount = 0;

    this.streamInterval = setInterval(() => {
      if (this.currentIndex >= this.cachedVehicles.length) {
        this.currentIndex = 0; // Loop stream
      }

      const v = this.cachedVehicles[this.currentIndex++];
      if (!v) return;

      displayedCount++;
      const countEl = document.getElementById("live-obs-count");
      if (countEl) countEl.textContent = `${displayedCount} Records`;

      // Animate target reticle on radar screen
      if (reticle && viewport) {
        reticle.style.display = "block";
        // Random screen coordinates centered around radar radius
        const angle = Math.random() * Math.PI * 2;
        const dist = 40 + Math.random() * 110;
        const cx = 50 + (Math.cos(angle) * dist) / (viewport.clientWidth / 100);
        const cy = 50 + (Math.sin(angle) * dist) / (viewport.clientHeight / 100);

        reticle.style.left = `${Math.min(85, Math.max(15, cx))}%`;
        reticle.style.top = `${Math.min(85, Math.max(15, cy))}%`;

        const isVio = v.status === "VIOLATION";
        reticle.children[0].style.borderColor = isVio ? "var(--red)" : "var(--green)";
        reticle.children[0].style.boxShadow = isVio ? "0 0 10px var(--red)" : "0 0 10px var(--green)";
        reticleTag.textContent = `#${v.vehicle_id} | ${v.speed.toFixed(1)} km/h`;
        reticleTag.style.color = isVio ? "var(--red)" : "var(--green)";
      }

      // Prepend card to stream
      const card = document.createElement("div");
      card.className = `observation-card ${v.status === 'VIOLATION' ? 'violation' : 'safe'}`;
      card.innerHTML = `
        <div style="display: flex; align-items: center; gap: 10px;">
          <div style="width: 28px; height: 28px; border-radius: 6px; background: rgba(255,255,255,0.05); display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: bold; color: var(--text-main);">
            #${v.vehicle_id}
          </div>
          <div>
            <div style="font-size: 12px; font-weight: 600; color: var(--text-main);">${v.vehicle_class_name}</div>
            <div style="font-size: 10px; color: var(--text-muted); font-family: monospace;">POS (${v.position_x.toFixed(1)}, ${v.position_y.toFixed(1)}) • ${v.timestamp.slice(11)}</div>
          </div>
        </div>
        <div style="text-align: right;">
          <div class="speed-tag ${v.status === 'VIOLATION' ? 'violation' : 'safe'}">${v.speed.toFixed(1)} km/h</div>
          <span class="badge ${v.status === 'VIOLATION' ? 'badge-violation' : 'badge-safe'}" style="font-size: 9px; padding: 2px 6px;">
            ${v.status}
          </span>
        </div>
      `;

      if (streamContainer) {
        streamContainer.insertBefore(card, streamContainer.firstChild);
        // Keep at most 15 cards in DOM for high performance
        if (streamContainer.children.length > 15) {
          streamContainer.removeChild(streamContainer.lastChild);
        }
      }
    }, 1200);
  }
};

window.RadarView = RadarView;
