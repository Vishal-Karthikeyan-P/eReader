/* =============================================================
   Theme controller: mode (light / dark / system) + colour palette.
   Loaded in <head> so the right theme is applied before first paint.
   Any element with [data-theme-open] opens the picker.
============================================================= */
(function () {
    "use strict";

    var PALETTES = [
        ["ink", "Ink"], ["ocean", "Ocean"], ["moss", "Moss"], ["ember", "Ember"],
        ["rose", "Rose"], ["plum", "Plum"], ["paper", "Paper"]
    ];
    var MODE_KEY = "readerMode";
    var PALETTE_KEY = "readerPalette";
    var root = document.documentElement;
    var media = window.matchMedia ? window.matchMedia("(prefers-color-scheme: dark)") : null;

    function read(key) {
        try { return localStorage.getItem(key); } catch (e) { return null; }
    }
    function write(key, value) {
        try { localStorage.setItem(key, value); } catch (e) { /* storage unavailable */ }
    }

    // Migrate the old three-way reader theme (dark / light / sepia).
    if (!read(MODE_KEY) && !read(PALETTE_KEY)) {
        var legacy = read("readerTheme");
        if (legacy === "sepia") { write(MODE_KEY, "light"); write(PALETTE_KEY, "paper"); }
        else if (legacy === "light" || legacy === "dark") { write(MODE_KEY, legacy); }
    }

    var mode = read(MODE_KEY) || "system";
    var palette = read(PALETTE_KEY) || "ink";
    if (["light", "dark", "system"].indexOf(mode) < 0) mode = "system";
    if (!PALETTES.some(function (p) { return p[0] === palette; })) palette = "ink";

    function resolved() {
        if (mode === "system") return media && media.matches ? "dark" : "light";
        return mode;
    }

    function apply() {
        root.setAttribute("data-theme", resolved());
        root.setAttribute("data-palette", palette);
        var meta = document.querySelector('meta[name="theme-color"]');
        if (meta) {
            var bg = getComputedStyle(root).getPropertyValue("--bg").trim();
            if (bg) meta.setAttribute("content", bg);
        }
        document.dispatchEvent(new CustomEvent("themechange", {
            detail: { mode: mode, theme: resolved(), palette: palette }
        }));
    }

    apply();
    if (media) {
        var onSystem = function () { if (mode === "system") apply(); };
        if (media.addEventListener) media.addEventListener("change", onSystem);
        else if (media.addListener) media.addListener(onSystem);
    }

    window.Theme = {
        get: function () { return { mode: mode, theme: resolved(), palette: palette }; },
        setMode: function (value) { mode = value; write(MODE_KEY, value); apply(); sync(); },
        setPalette: function (value) { palette = value; write(PALETTE_KEY, value); apply(); sync(); },
        cssVar: function (name) { return getComputedStyle(root).getPropertyValue(name).trim(); }
    };

    /* ---------- picker UI ---------- */
    var panel, backdrop, lastTrigger;

    function icon(name) {
        return '<svg class="i" aria-hidden="true"><use href="#i-' + name + '"/></svg>';
    }

    function build() {
        backdrop = document.createElement("div");
        backdrop.className = "sheet-backdrop";
        panel = document.createElement("div");
        panel.className = "sheet";
        panel.setAttribute("role", "dialog");
        panel.setAttribute("aria-label", "Appearance");
        panel.innerHTML =
            '<div class="tp-head"><h3>Appearance</h3>' +
            '<button class="icon-btn" data-tp-close aria-label="Close">' + icon("close") + "</button></div>" +
            '<div><h3>Mode</h3><div class="segmented" data-tp-modes>' +
            '<button data-mode="light">' + icon("sun") + "Light</button>" +
            '<button data-mode="dark">' + icon("moon") + "Dark</button>" +
            '<button data-mode="system">' + icon("monitor") + "Auto</button></div></div>" +
            '<div><h3>Colour theme</h3><div class="tp-swatches" data-tp-palettes>' +
            PALETTES.map(function (p) {
                return '<button class="tp-swatch" data-palette-choice="' + p[0] + '">' +
                    '<span class="tp-dot" data-palette="' + p[0] + '"></span>' + p[1] + "</button>";
            }).join("") + "</div></div>";
        document.body.appendChild(backdrop);
        document.body.appendChild(panel);

        panel.addEventListener("click", function (e) {
            var m = e.target.closest("[data-mode]");
            var p = e.target.closest("[data-palette-choice]");
            if (m) window.Theme.setMode(m.getAttribute("data-mode"));
            else if (p) window.Theme.setPalette(p.getAttribute("data-palette-choice"));
            else if (e.target.closest("[data-tp-close]")) close();
        });
        backdrop.addEventListener("click", close);
        document.addEventListener("keydown", function (e) {
            if (e.key === "Escape" && panel.classList.contains("open")) close();
        });
        sync();
    }

    function sync() {
        if (!panel) return;
        panel.querySelectorAll("[data-mode]").forEach(function (b) {
            b.setAttribute("aria-pressed", String(b.getAttribute("data-mode") === mode));
        });
        panel.querySelectorAll("[data-palette-choice]").forEach(function (b) {
            b.setAttribute("aria-pressed", String(b.getAttribute("data-palette-choice") === palette));
        });
    }

    function open(trigger) {
        if (!panel) build();
        lastTrigger = trigger || null;
        panel.classList.add("open");
        backdrop.classList.add("open");
        var first = panel.querySelector('[aria-pressed="true"]');
        if (first) first.focus({ preventScroll: true });
    }
    function close() {
        if (!panel) return;
        panel.classList.remove("open");
        backdrop.classList.remove("open");
        if (lastTrigger) lastTrigger.focus({ preventScroll: true });
    }
    window.Theme.openPicker = open;
    window.Theme.closePicker = close;

    document.addEventListener("click", function (e) {
        var t = e.target.closest("[data-theme-open]");
        if (t) { e.preventDefault(); open(t); }
    });
})();
