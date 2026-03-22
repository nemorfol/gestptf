/* ==========================================================================
   Portfolio Manager - Application JavaScript
   ========================================================================== */

(function () {
  "use strict";

  /* ========================================================================
     1. THEME MANAGER
     ======================================================================== */

  const ThemeManager = {
    STORAGE_KEY: "pm-theme",

    init() {
      // Apply saved theme immediately (called before DOMContentLoaded too)
      const saved = localStorage.getItem(this.STORAGE_KEY);
      const prefersDark =
        window.matchMedia &&
        window.matchMedia("(prefers-color-scheme: dark)").matches;
      const theme = saved || (prefersDark ? "dark" : "light");
      this.apply(theme);

      // When DOM is ready, wire up the toggle button
      document.addEventListener("DOMContentLoaded", () => {
        this.updateIcon();
        document.querySelectorAll("[data-pm-theme-toggle]").forEach((btn) => {
          btn.addEventListener("click", () => this.toggle());
        });
      });
    },

    apply(theme) {
      document.documentElement.setAttribute("data-bs-theme", theme);
      localStorage.setItem(this.STORAGE_KEY, theme);
    },

    current() {
      return (
        document.documentElement.getAttribute("data-bs-theme") || "light"
      );
    },

    toggle() {
      const next = this.current() === "light" ? "dark" : "light";
      this.apply(next);
      this.updateIcon();
    },

    updateIcon() {
      const isDark = this.current() === "dark";
      document.querySelectorAll("[data-pm-theme-toggle]").forEach((btn) => {
        const icon = btn.querySelector("i");
        if (!icon) return;
        icon.className = isDark ? "bi bi-sun-fill" : "bi bi-moon-fill";
      });
    },
  };

  // Apply theme as early as possible to prevent flash
  ThemeManager.init();

  /* ========================================================================
     2. SIDEBAR MANAGER
     ======================================================================== */

  const SidebarManager = {
    STORAGE_KEY: "pm-sidebar-collapsed",

    init() {
      this.sidebar = document.querySelector(".pm-sidebar");
      this.overlay = document.querySelector(".pm-sidebar-overlay");
      if (!this.sidebar) return;

      // Restore collapsed state (desktop only)
      if (window.innerWidth > 767 && localStorage.getItem(this.STORAGE_KEY) === "true") {
        this.sidebar.classList.add("collapsed");
        document.body.classList.add("sidebar-collapsed");
      }

      // Toggle buttons
      document.querySelectorAll("[data-pm-sidebar-toggle]").forEach((btn) => {
        btn.addEventListener("click", () => this.toggle());
      });

      // Overlay click closes sidebar on mobile
      if (this.overlay) {
        this.overlay.addEventListener("click", () => this.closeMobile());
      }

      // Manage active nav link
      this.setActiveLink();

      // Close mobile sidebar on resize to desktop
      window.addEventListener("resize", () => {
        if (window.innerWidth > 767) {
          this.closeMobile();
        }
      });
    },

    toggle() {
      if (window.innerWidth <= 767) {
        // Mobile: off-canvas toggle
        this.sidebar.classList.toggle("show");
        if (this.overlay) {
          this.overlay.classList.toggle("active", this.sidebar.classList.contains("show"));
        }
      } else {
        // Desktop: collapse toggle
        this.sidebar.classList.toggle("collapsed");
        const isCollapsed = this.sidebar.classList.contains("collapsed");
        document.body.classList.toggle("sidebar-collapsed", isCollapsed);
        localStorage.setItem(this.STORAGE_KEY, isCollapsed);
      }
    },

    closeMobile() {
      if (!this.sidebar) return;
      this.sidebar.classList.remove("show");
      if (this.overlay) {
        this.overlay.classList.remove("active");
      }
    },

    setActiveLink() {
      const path = window.location.pathname;
      this.sidebar.querySelectorAll(".nav-link").forEach((link) => {
        link.classList.remove("active");
        const href = link.getAttribute("href");
        if (href && (href === path || (path.startsWith(href) && href !== "/"))) {
          link.classList.add("active");
        }
      });
      // Fallback: if nothing matched and path is "/", activate first link
      if (path === "/" && !this.sidebar.querySelector(".nav-link.active")) {
        const first = this.sidebar.querySelector(".nav-link");
        if (first) first.classList.add("active");
      }
    },
  };

  /* ========================================================================
     3. TOAST NOTIFICATION SYSTEM
     ======================================================================== */

  const Toast = {
    _container: null,
    _icons: {
      success: "bi bi-check-circle-fill",
      error: "bi bi-x-circle-fill",
      warning: "bi bi-exclamation-triangle-fill",
      info: "bi bi-info-circle-fill",
    },

    _getContainer() {
      if (!this._container) {
        this._container = document.createElement("div");
        this._container.className = "pm-toast-container";
        document.body.appendChild(this._container);
      }
      return this._container;
    },

    show(message, type) {
      type = type || "info";
      const container = this._getContainer();

      const toast = document.createElement("div");
      toast.className = "pm-toast toast-" + type;
      toast.innerHTML =
        '<i class="pm-toast-icon ' +
        (this._icons[type] || this._icons.info) +
        '"></i>' +
        '<div class="pm-toast-body">' +
        this._escapeHtml(message) +
        "</div>" +
        '<button class="pm-toast-close" aria-label="Chiudi">&times;</button>';

      container.appendChild(toast);

      // Close button
      toast.querySelector(".pm-toast-close").addEventListener("click", () => {
        this._dismiss(toast);
      });

      // Auto-dismiss after 5 seconds
      setTimeout(() => this._dismiss(toast), 5000);
    },

    _dismiss(el) {
      if (!el || el.classList.contains("removing")) return;
      el.classList.add("removing");
      el.addEventListener("animationend", () => el.remove());
    },

    _escapeHtml(str) {
      const div = document.createElement("div");
      div.textContent = str;
      return div.innerHTML;
    },
  };

  /* ========================================================================
     4. LOADING OVERLAY
     ======================================================================== */

  const Loading = {
    _overlay: null,

    _getOverlay() {
      if (!this._overlay) {
        this._overlay = document.createElement("div");
        this._overlay.className = "pm-loading-overlay";
        this._overlay.innerHTML =
          '<div class="pm-spinner"></div>' +
          '<div class="pm-loading-message"></div>';
        document.body.appendChild(this._overlay);
      }
      return this._overlay;
    },

    show(message) {
      const overlay = this._getOverlay();
      const msg = overlay.querySelector(".pm-loading-message");
      msg.textContent = message || "";
      msg.style.display = message ? "block" : "none";
      overlay.classList.add("active");
    },

    hide() {
      const overlay = this._getOverlay();
      overlay.classList.remove("active");
    },
  };

  /* ========================================================================
     5. NUMBER FORMATTING (Italian locale)
     ======================================================================== */

  const Fmt = {
    /**
     * Format as Italian currency: "€ 1.234,56"
     */
    currency(value) {
      if (value == null || isNaN(value)) return "—";
      const num = Number(value);
      const formatted = num.toLocaleString("it-IT", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      });
      return "\u20AC " + formatted; // € symbol
    },

    /**
     * Format as percent with sign: "+12,34%"  /  "-3,21%"
     */
    percent(value) {
      if (value == null || isNaN(value)) return "—";
      const num = Number(value);
      const sign = num > 0 ? "+" : "";
      return (
        sign +
        num.toLocaleString("it-IT", {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        }) +
        "%"
      );
    },

    /**
     * Format a number with given decimals, Italian locale
     */
    number(value, decimals) {
      if (value == null || isNaN(value)) return "—";
      decimals = decimals != null ? decimals : 2;
      return Number(value).toLocaleString("it-IT", {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals,
      });
    },
  };

  /* ========================================================================
     6. DATATABLES DEFAULTS & HELPER
     ======================================================================== */

  const DT = {
    italianLanguage: {
      processing: "Elaborazione...",
      search: "Cerca:",
      lengthMenu: "Mostra _MENU_ righe",
      info: "Da _START_ a _END_ di _TOTAL_ righe",
      infoEmpty: "Nessun risultato",
      infoFiltered: "(filtrate da _MAX_ righe totali)",
      loadingRecords: "Caricamento...",
      zeroRecords: "Nessun risultato trovato",
      emptyTable: "Nessun dato disponibile",
      paginate: {
        first: "Inizio",
        previous: "&laquo;",
        next: "&raquo;",
        last: "Fine",
      },
      aria: {
        sortAscending: ": attiva per ordinare in modo crescente",
        sortDescending: ": attiva per ordinare in modo decrescente",
      },
    },

    defaults: {
      responsive: true,
      pageLength: 25,
      lengthMenu: [10, 25, 50, 100],
      order: [],
      dom:
        "<'row'<'col-sm-12 col-md-6'l><'col-sm-12 col-md-6'f>>" +
        "<'row'<'col-sm-12'tr>>" +
        "<'row'<'col-sm-12 col-md-5'i><'col-sm-12 col-md-7'p>>",
      autoWidth: false,
    },

    /**
     * Initialise a DataTable with sensible defaults and Italian language.
     * @param {string} selector  - CSS selector for the table element
     * @param {object} options   - custom DataTables options (merged with defaults)
     * @returns {object} DataTable instance
     */
    init(selector, options) {
      if (typeof $ === "undefined" || !$.fn.DataTable) {
        console.warn("DataTables library not loaded.");
        return null;
      }
      const settings = Object.assign(
        {},
        this.defaults,
        { language: this.italianLanguage },
        options || {}
      );
      return $(selector).DataTable(settings);
    },
  };

  /* ========================================================================
     7. API HELPER
     ======================================================================== */

  /**
   * Fetch wrapper with loading overlay and automatic error toasts.
   * @param {string} url
   * @param {string} method  - GET, POST, PUT, DELETE, etc.
   * @param {object|null} data - body payload (will be JSON-stringified)
   * @param {object} opts - extra options: { loading: true/false, loadingMsg: "" }
   * @returns {Promise<any>} parsed JSON response
   */
  async function apiCall(url, method, data, opts) {
    method = (method || "GET").toUpperCase();
    opts = opts || {};
    const showLoad = opts.loading !== false;

    if (showLoad) Loading.show(opts.loadingMsg || "");

    const fetchOpts = {
      method: method,
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
    };

    if (data && method !== "GET" && method !== "HEAD") {
      fetchOpts.body = JSON.stringify(data);
    }

    try {
      const response = await fetch(url, fetchOpts);
      const contentType = response.headers.get("content-type") || "";
      let result;
      if (contentType.includes("application/json")) {
        result = await response.json();
      } else {
        result = await response.text();
      }

      if (!response.ok) {
        const errMsg =
          (result && result.error) ||
          (result && result.message) ||
          "Errore " + response.status;
        throw new Error(errMsg);
      }
      return result;
    } catch (err) {
      Toast.show(err.message || "Errore di rete", "error");
      throw err;
    } finally {
      if (showLoad) Loading.hide();
    }
  }

  /* ========================================================================
     8. CONFIRMATION DIALOG
     ======================================================================== */

  /**
   * Show a Bootstrap modal confirmation.
   * @param {string} message  - Prompt text
   * @param {function} onConfirm - Called when user clicks "Conferma"
   */
  function confirmAction(message, onConfirm) {
    const id = "pmConfirmModal";
    let modal = document.getElementById(id);

    if (!modal) {
      modal = document.createElement("div");
      modal.id = id;
      modal.className = "modal fade pm-modal";
      modal.tabIndex = -1;
      modal.innerHTML =
        '<div class="modal-dialog modal-dialog-centered modal-sm">' +
        '  <div class="modal-content">' +
        '    <div class="modal-header">' +
        '      <h5 class="modal-title">Conferma</h5>' +
        '      <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Chiudi"></button>' +
        "    </div>" +
        '    <div class="modal-body"><p class="pm-confirm-msg mb-0"></p></div>' +
        '    <div class="modal-footer">' +
        '      <button type="button" class="pm-btn pm-btn-ghost" data-bs-dismiss="modal">Annulla</button>' +
        '      <button type="button" class="pm-btn pm-btn-danger pm-confirm-ok">Conferma</button>' +
        "    </div>" +
        "  </div>" +
        "</div>";
      document.body.appendChild(modal);
    }

    modal.querySelector(".pm-confirm-msg").textContent = message;

    const bsModal = new bootstrap.Modal(modal);
    const okBtn = modal.querySelector(".pm-confirm-ok");

    // Remove previous listeners by cloning
    const newOk = okBtn.cloneNode(true);
    okBtn.parentNode.replaceChild(newOk, okBtn);

    newOk.addEventListener("click", function () {
      bsModal.hide();
      if (typeof onConfirm === "function") onConfirm();
    });

    bsModal.show();
  }

  /* ========================================================================
     9. FORM HELPERS
     ======================================================================== */

  const FormHelper = {
    /**
     * Collect form inputs into a plain object.
     * Keys are taken from the name attribute.
     */
    collect(formSelector) {
      const form = document.querySelector(formSelector);
      if (!form) return {};
      const data = {};
      const elements = form.querySelectorAll(
        "input, select, textarea"
      );
      elements.forEach((el) => {
        const name = el.name;
        if (!name) return;
        if (el.type === "checkbox") {
          data[name] = el.checked;
        } else if (el.type === "radio") {
          if (el.checked) data[name] = el.value;
        } else {
          data[name] = el.value;
        }
      });
      return data;
    },

    /**
     * Populate form inputs from a data object.
     */
    populate(formSelector, data) {
      const form = document.querySelector(formSelector);
      if (!form || !data) return;
      Object.keys(data).forEach((key) => {
        const el = form.querySelector('[name="' + key + '"]');
        if (!el) return;
        if (el.type === "checkbox") {
          el.checked = !!data[key];
        } else if (el.type === "radio") {
          form.querySelectorAll('[name="' + key + '"]').forEach((r) => {
            r.checked = r.value === String(data[key]);
          });
        } else {
          el.value = data[key] != null ? data[key] : "";
        }
      });
    },

    /**
     * Reset all inputs in a form.
     */
    clear(formSelector) {
      const form = document.querySelector(formSelector);
      if (form) form.reset();
    },
  };

  /* ========================================================================
     10. P/L CELL COLORING
     ======================================================================== */

  /**
   * Scan cells with data-pl attribute or class .pl-value and apply
   * .positive / .negative based on numeric value.
   */
  function colorPLCells(scope) {
    const root = scope || document;
    root.querySelectorAll("[data-pl], .pl-value").forEach((cell) => {
      // Get numeric value: try data attribute first, then text content
      let raw = cell.getAttribute("data-pl");
      if (raw == null) {
        raw = cell.textContent
          .replace(/[€%\s+]/g, "")
          .replace(/\./g, "")
          .replace(",", ".");
      }
      const num = parseFloat(raw);
      cell.classList.remove("positive", "negative");
      if (!isNaN(num)) {
        cell.classList.add(num >= 0 ? "positive" : "negative");
      }
    });
  }

  /* ========================================================================
     11. EVENT DELEGATION HELPER
     ======================================================================== */

  /**
   * Delegated event listener for dynamic content.
   * @param {string} parentSelector - static ancestor
   * @param {string} eventType      - e.g. "click"
   * @param {string} childSelector  - dynamic element selector
   * @param {function} handler      - event handler, receives (event, matchedElement)
   */
  function onDelegate(parentSelector, eventType, childSelector, handler) {
    const parent = document.querySelector(parentSelector);
    if (!parent) return;
    parent.addEventListener(eventType, function (e) {
      const target = e.target.closest(childSelector);
      if (target && parent.contains(target)) {
        handler.call(target, e, target);
      }
    });
  }

  /* ========================================================================
     DOMContentLoaded - Initialise modules
     ======================================================================== */

  document.addEventListener("DOMContentLoaded", function () {
    SidebarManager.init();
    colorPLCells();
  });

  /* ========================================================================
     PUBLIC API  -  window.PM
     ======================================================================== */

  /* ========================================================================
     12. PLOTLY THEME HELPERS
     ======================================================================== */
  function plotlyIsDark() {
    return document.documentElement.getAttribute('data-bs-theme') === 'dark';
  }

  function plotlyTheme() {
    var isDark = plotlyIsDark();
    return {
      paper_bgcolor: 'rgba(0,0,0,0)',
      plot_bgcolor: 'rgba(0,0,0,0)',
      font: { color: isDark ? '#dee2e6' : '#495057' },
      colorway: ['#4e79a7','#f28e2b','#e15759','#76b7b2','#59a14f','#edc948','#b07aa1','#ff9da7','#9c755f','#bab0ac'],
      xaxis: { gridcolor: isDark ? '#495057' : '#e9ecef' },
      yaxis: { gridcolor: isDark ? '#495057' : '#e9ecef' },
      hoverlabel: {
        bgcolor: isDark ? '#2b3035' : '#fff',
        bordercolor: isDark ? '#495057' : '#dee2e6',
        font: { color: isDark ? '#dee2e6' : '#212529', size: 13 }
      }
    };
  }

  function plotlyLayout(title) {
    var theme = plotlyTheme();
    return Object.assign({}, theme, {
      title: title ? { text: title, font: { size: 14 } } : undefined,
      margin: { t: title ? 40 : 20, r: 20, b: 40, l: 70 },
      autosize: true
    });
  }

  window.PM = {
    Theme: ThemeManager,
    Sidebar: SidebarManager,
    Toast: Toast,
    Loading: Loading,
    Fmt: Fmt,
    DT: DT,
    apiCall: apiCall,
    confirmAction: confirmAction,
    Form: FormHelper,
    colorPLCells: colorPLCells,
    onDelegate: onDelegate,
    Plotly: { theme: plotlyTheme, layout: plotlyLayout, isDark: plotlyIsDark },
  };
})();
