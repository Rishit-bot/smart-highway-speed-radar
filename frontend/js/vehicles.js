/**
 * Vehicles.js - Vehicle Telemetry Observation Table & Search/Filter
 * Smart Highway Speed Radar & Ticket Generator
 */

const VehiclesView = {
  currentPage: 1,
  pageSize: 15,
  totalPages: 1,
  totalRecords: 0,

  async load() {
    this.initListeners();
    await this.fetchVehicles();
  },

  initListeners() {
    const searchInput = document.getElementById("vehicle-search");
    const statusFilter = document.getElementById("vehicle-status-filter");
    const classFilter = document.getElementById("vehicle-class-filter");
    const btnRefresh = document.getElementById("btn-refresh-vehicles");
    const btnPrev = document.getElementById("btn-prev-page");
    const btnNext = document.getElementById("btn-next-page");

    // Debounced search
    let debounceTimer;
    searchInput?.replaceWith(searchInput.cloneNode(true));
    document.getElementById("vehicle-search")?.addEventListener("input", (e) => {
      clearTimeout(debounceTimer);
      debounceTimer = setTimeout(() => {
        this.currentPage = 1;
        this.fetchVehicles();
      }, 300);
    });

    statusFilter?.replaceWith(statusFilter.cloneNode(true));
    document.getElementById("vehicle-status-filter")?.addEventListener("change", () => {
      this.currentPage = 1;
      this.fetchVehicles();
    });

    classFilter?.replaceWith(classFilter.cloneNode(true));
    document.getElementById("vehicle-class-filter")?.addEventListener("change", () => {
      this.currentPage = 1;
      this.fetchVehicles();
    });

    btnRefresh?.replaceWith(btnRefresh.cloneNode(true));
    document.getElementById("btn-refresh-vehicles")?.addEventListener("click", () => {
      this.fetchVehicles();
    });

    btnPrev?.replaceWith(btnPrev.cloneNode(true));
    document.getElementById("btn-prev-page")?.addEventListener("click", () => {
      if (this.currentPage > 1) {
        this.currentPage--;
        this.fetchVehicles();
      }
    });

    btnNext?.replaceWith(btnNext.cloneNode(true));
    document.getElementById("btn-next-page")?.addEventListener("click", () => {
      if (this.currentPage < this.totalPages) {
        this.currentPage++;
        this.fetchVehicles();
      }
    });
  },

  async fetchVehicles() {
    const search = document.getElementById("vehicle-search")?.value.trim() || "";
    const status = document.getElementById("vehicle-status-filter")?.value || "ALL";
    const vClass = document.getElementById("vehicle-class-filter")?.value || "";

    let query = `/api/vehicles?page=${this.currentPage}&page_size=${this.pageSize}`;
    if (search) query += `&search=${encodeURIComponent(search)}`;
    if (status && status !== "ALL") query += `&status_filter=${status}`;
    if (vClass) query += `&vehicle_class=${vClass}`;

    try {
      const res = await App.api(query);
      this.totalRecords = res.total;
      this.totalPages = res.total_pages;

      this.renderTable(res.items);
      this.renderPagination();
    } catch (err) {
      console.error("Failed to load vehicles:", err);
    }
  },

  renderTable(vehicles) {
    const tbody = document.getElementById("vehicles-tbody");
    if (!tbody) return;

    if (!vehicles || vehicles.length === 0) {
      tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; color: var(--text-muted); padding: 30px;">No vehicles match the selected criteria.</td></tr>`;
      return;
    }

    tbody.innerHTML = vehicles.map(v => {
      const isVio = v.status === "VIOLATION";
      return `
        <tr>
          <td><strong style="color: var(--text-main);">#${v.vehicle_id}</strong></td>
          <td>
            <span class="badge badge-cyan" style="font-size: 10px;">${v.vehicle_class_name}</span>
          </td>
          <td>
            <span class="speed-tag ${isVio ? 'violation' : 'safe'}">${v.speed.toFixed(1)} km/h</span>
          </td>
          <td style="color: var(--text-muted); font-size: 12px;">${v.timestamp}</td>
          <td style="font-family: monospace; font-size: 11px; color: var(--text-dim);">${v.position_x.toFixed(1)}, ${v.position_y.toFixed(1)}</td>
          <td>
            <span class="badge ${isVio ? 'badge-violation' : 'badge-safe'}">${v.status}</span>
          </td>
          <td style="font-weight: 600; color: ${isVio ? 'var(--amber)' : 'var(--text-muted)'};">
            ${isVio ? '$' + v.fine.toFixed(2) : '-'}
          </td>
        </tr>
      `;
    }).join("");
  },

  renderPagination() {
    const info = document.getElementById("vehicles-pagination-info");
    const pageNum = document.getElementById("current-page-num");
    const btnPrev = document.getElementById("btn-prev-page");
    const btnNext = document.getElementById("btn-next-page");

    if (info) {
      const start = this.totalRecords === 0 ? 0 : (this.currentPage - 1) * this.pageSize + 1;
      const end = Math.min(this.currentPage * this.pageSize, this.totalRecords);
      info.textContent = `Showing records ${start} - ${end} of ${this.totalRecords}`;
    }

    if (pageNum) {
      pageNum.textContent = `${this.currentPage} / ${this.totalPages}`;
    }

    if (btnPrev) btnPrev.disabled = this.currentPage <= 1;
    if (btnNext) btnNext.disabled = this.currentPage >= this.totalPages;
  }
};

window.VehiclesView = VehiclesView;
