window.MFUI = (function () {
  const state = { messages: {} };

  function lang() {
    return localStorage.getItem("mf_lang") || "en";
  }

  function t(key, fallback = "") {
    return state.messages[key] || fallback || key;
  }

  function localizeErrorMessage(msg) {
    const text = String(msg || "");
    const lower = text.toLowerCase();
    if (lower.includes("authentication required")) return t("error.auth_required", "Authentication required.");
    if (lower.includes("invalid email")) return t("error.invalid_email", "Invalid email format.");
    if (lower.includes("at least 8")) return t("error.password_min_8", "Password must have at least 8 characters.");
    if (lower.includes("cannot set properties of null")) return t("error.ui_runtime", "Page rendering error. Please reload.");
    return text;
  }

  async function parseError(res) {
    try {
      const data = await res.json();
      if (data?.error?.details?.length) {
        const joined = data.error.details.map((d) => `${d.field}: ${d.message}`).join("; ");
        return localizeErrorMessage(joined);
      }
      return localizeErrorMessage(data?.detail || `HTTP ${res.status}`);
    } catch (_) {
      return `HTTP ${res.status}`;
    }
  }

  async function api(path, method = "GET", body = null, formData = null) {
    const init = { method, credentials: "include" };
    if (formData) {
      init.body = formData;
    } else {
      init.headers = { "Content-Type": "application/json" };
      init.body = body ? JSON.stringify(body) : null;
    }
    const res = await fetch(path, init);
    if (!res.ok) throw new Error(await parseError(res));
    const ct = res.headers.get("content-type") || "";
    return ct.includes("application/json") ? await res.json() : res;
  }

  function applyTheme() {
    const theme = localStorage.getItem("mf_theme") || "system";
    document.body.classList.remove("dark");
    if (
      theme === "dark" ||
      (theme === "system" &&
        window.matchMedia &&
        window.matchMedia("(prefers-color-scheme: dark)").matches)
    ) {
      document.body.classList.add("dark");
    }
  }

  function applyLayout() {
    const mode = localStorage.getItem("mf_layout_width") || "full";
    document.body.classList.remove("layout-limited");
    if (mode === "limited") document.body.classList.add("layout-limited");
  }

  async function bootstrapLocale() {
    try {
      const settings = await api("/api/v1/settings/app");
      if (settings?.defaultLocale) {
        localStorage.setItem("mf_lang", settings.defaultLocale);
      }
    } catch (_) {}
    try {
      const res = await fetch(`/api/v1/i18n/${lang()}`, { credentials: "include" });
      if (res.ok) {
        const data = await res.json();
        state.messages = data.messages || {};
      }
    } catch (_) {
      state.messages = {};
    }
  }

  function bindUserMenu() {
    const btn = document.getElementById("userBtn");
    const menu = document.getElementById("userMenu");
    if (!btn || !menu) return;
    btn.addEventListener("click", () => menu.classList.toggle("open"));
    document.addEventListener("click", (e) => {
      if (!e.target.closest(".user-menu")) menu.classList.remove("open");
    });
  }

  async function populateUser() {
    const btn = document.getElementById("userBtn");
    if (!btn) return;
    try {
      const me = await api("/api/v1/auth/me");
      btn.textContent = me.fullName ? me.fullName : me.email;
    } catch (_) {
      btn.textContent = "...";
    }
  }

  function bindLogout() {
    const logout = document.getElementById("logoutBtn");
    if (!logout) return;
    logout.addEventListener("click", async () => {
      try {
        await api("/api/v1/auth/logout", "POST");
      } catch (_) {}
      window.location.href = "/ui/get-started";
    });
  }

  function setMsg(text, isError = false) {
    const el = document.getElementById("msg");
    if (!el) return;
    el.textContent = text;
    el.className = `msg ${isError ? "err" : "ok"}`;
  }

  function applyCommonNav() {
    const map = {
      navOverview: t("common.overview", "Overview"),
      navTransactions: t("common.transactions", "Transactions"),
      navInvestments: t("common.savings_investments", "Savings & Investments"),
      navRates: t("common.rates", "Rates"),
      navServices: t("common.services", "Services"),
      menuSettingsLink: t("common.settings", "Settings"),
    };
    Object.entries(map).forEach(([id, val]) => {
      const el = document.getElementById(id);
      if (el) el.textContent = val;
    });
    const logout = document.getElementById("logoutBtn");
    if (logout) logout.textContent = t("common.logout", "Logout");
    const footer = document.getElementById("footerText");
    if (footer) {
      footer.textContent = t(
        "common.disclaimer",
        "Copyright (c) My-Finance. Experimental software. Verify data and recommendations before acting."
      );
    }
  }

  async function init() {
    applyTheme();
    applyLayout();
    await bootstrapLocale();
    applyCommonNav();
    bindUserMenu();
    bindLogout();
    await populateUser();
    document.body.classList.add("ui-ready");
  }

  function periodicRefresh(fn, ms = 60000) {
    const timer = setInterval(fn, ms);
    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "visible") fn();
    });
    return () => clearInterval(timer);
  }

  return { t, api, init, setMsg, applyTheme, applyLayout, periodicRefresh, formatError: localizeErrorMessage };
})();
