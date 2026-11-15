/**
 * Tickets.js - Electronic Citations (E-Tickets) Gallery & Exporting
 * Smart Highway Speed Radar & Ticket Generator
 */

const TicketsView = {
  tickets: [],

  async load() {
    this.initListeners();
    await this.fetchTickets();
  },

  initListeners() {
    const btnGenAll = document.getElementById("btn-generate-all-tickets");
    const btnRefresh = document.getElementById("btn-refresh-tickets");

    btnGenAll?.replaceWith(btnGenAll.cloneNode(true));
    document.getElementById("btn-generate-all-tickets")?.addEventListener("click", async () => {
      try {
        App.showToast("Rendering and issuing electronic citations for all detected violators...", "info");
        const res = await App.api("/api/tickets/generate", { method: "POST" });
        App.showToast(`Success: ${res.tickets_generated} citation documents issued!`, "success");
        await this.fetchTickets();
      } catch (err) {
        App.showToast(`Ticket generation failed: ${err.message}`, "danger");
      }
    });

    btnRefresh?.replaceWith(btnRefresh.cloneNode(true));
    document.getElementById("btn-refresh-tickets")?.addEventListener("click", () => {
      this.fetchTickets();
    });
  },

  async fetchTickets() {
    try {
      const res = await App.api("/api/tickets?page=1&page_size=50");
      this.tickets = res.items || [];
      this.renderGrid();
    } catch (err) {
      console.error("Failed to load tickets:", err);
    }
  },

  renderGrid() {
    const container = document.getElementById("tickets-container");
    if (!container) return;

    if (!this.tickets || this.tickets.length === 0) {
      container.innerHTML = `
        <div style="grid-column: 1 / -1; text-align: center; color: var(--text-muted); padding: 48px;">
          No citation tickets issued yet. Scan telemetry and click "Generate Tickets for All Violators".
        </div>
      `;
      return;
    }

    container.innerHTML = this.tickets.map(t => {
      const imgUrl = `/api/tickets/${t.ticket_id}/image`;
      return `
        <div class="ticket-card">
          <div class="ticket-card-thumb" onclick="TicketsView.viewTicket('${t.ticket_id}')">
            <img src="${imgUrl}" alt="${t.ticket_id}" loading="lazy" onerror="this.src=''; this.alt='Ticket Image Rendering...';">
          </div>
          <div class="ticket-card-body">
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <span class="ticket-id">${t.ticket_id}</span>
              <span class="badge badge-violation" style="font-size: 10px;">ISSUED</span>
            </div>

            <div class="ticket-row">
              <span class="label">Target Vehicle:</span>
              <span class="val">#${t.vehicle_id} (${t.vehicle_class_name})</span>
            </div>

            <div class="ticket-row">
              <span class="label">Recorded Speed:</span>
              <span class="val" style="color: var(--red); font-weight: 700;">${t.recorded_speed.toFixed(1)} km/h</span>
            </div>

            <div class="ticket-row">
              <span class="label">Speed Limit:</span>
              <span class="val">${t.speed_limit.toFixed(1)} km/h (+${t.excess_speed.toFixed(1)})</span>
            </div>

            <div class="ticket-row">
              <span class="label">Infraction Date:</span>
              <span class="val" style="font-size: 11px;">${t.created_at}</span>
            </div>

            <div class="ticket-row" style="margin-top: 4px; padding-top: 6px; border-top: 1px dashed var(--border-light);">
              <span class="label">Statutory Fine:</span>
              <span class="ticket-fine-val">$${t.fine.toFixed(2)}</span>
            </div>
          </div>

          <div class="ticket-card-footer">
            <button class="btn btn-secondary btn-sm" style="flex: 1;" onclick="TicketsView.viewTicket('${t.ticket_id}')">
              View Citation
            </button>
            <a href="${imgUrl}" download="${t.ticket_id}.png" class="btn btn-primary btn-sm" title="Download Image">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
            </a>
            <button class="btn btn-secondary btn-sm" title="Download JSON" onclick="TicketsView.downloadJSON('${t.ticket_id}')">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>
            </button>
          </div>
        </div>
      `;
    }).join("");
  },

  async viewTicket(ticketId) {
    const modal = document.getElementById("ticket-modal");
    const titleEl = document.getElementById("modal-ticket-title");
    const imgEl = document.getElementById("modal-ticket-img");
    const metaEl = document.getElementById("modal-ticket-meta");
    const downloadImgBtn = document.getElementById("btn-download-ticket-img");
    const downloadJsonBtn = document.getElementById("btn-download-ticket-json");

    try {
      const ticket = await App.api(`/api/tickets/${ticketId}`);
      titleEl.textContent = `Official Citation Notice: ${ticket.ticket_id}`;
      imgEl.src = `/api/tickets/${ticketId}/image?t=${Date.now()}`;

      metaEl.innerHTML = `
        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin-top: 10px;">
          <div><strong>Violation Code:</strong> ${ticket.violation_id}</div>
          <div><strong>Vehicle ID:</strong> #${ticket.vehicle_id}</div>
          <div><strong>Category:</strong> ${ticket.vehicle_class_name}</div>
          <div><strong>Recorded Velocity:</strong> <span style="color: var(--red); font-weight: bold;">${ticket.recorded_speed.toFixed(1)} km/h</span></div>
          <div><strong>Speed Limit:</strong> ${ticket.speed_limit.toFixed(1)} km/h</div>
          <div><strong>Calculated Penalty:</strong> <strong style="color: var(--amber);">$${ticket.fine.toFixed(2)}</strong></div>
        </div>
      `;

      downloadImgBtn.href = `/api/tickets/${ticketId}/image`;
      downloadImgBtn.setAttribute("download", `${ticketId}.png`);

      downloadJsonBtn.onclick = () => this.downloadJSON(ticketId);

      modal.classList.add("active");
    } catch (err) {
      App.showToast(`Failed to open ticket: ${err.message}`, "danger");
    }
  },

  async downloadJSON(ticketId) {
    try {
      const ticket = await App.api(`/api/tickets/${ticketId}`);
      const jsonStr = JSON.stringify(ticket, null, 2);
      const blob = new Blob([jsonStr], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${ticketId}.json`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      App.showToast(`Downloaded ${ticketId}.json`, "success");
    } catch (err) {
      App.showToast(`Failed to download JSON: ${err.message}`, "danger");
    }
  }
};

window.TicketsView = TicketsView;
