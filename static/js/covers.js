/* =============================================================
   Book covers.
   1. /api/cover (Open Library, then Google Books)
   2. the book's own first page: PDF page 1, or the EPUB's cover image
   3. nothing: the caller keeps its typographic placeholder
   Results are cached in IndexedDB so each book is looked up once.
============================================================= */
(function () {
    "use strict";

    var PDFJS = "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js";
    var PDFJS_WORKER = "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js";
    var JSZIP = "https://cdn.jsdelivr.net/npm/jszip@3.10.1/dist/jszip.min.js";
    var WIDTH = 420;
    var RETRY_AFTER = 14 * 24 * 3600 * 1000;

    /* ---------- tiny helpers ---------- */

    function limiter(max) {
        var running = 0;
        var queue = [];
        function pump() {
            while (running < max && queue.length) {
                var job = queue.shift();
                running++;
                job.fn().then(job.resolve, job.reject).finally(function () { running--; pump(); });
            }
        }
        return function (fn) {
            return new Promise(function (resolve, reject) {
                queue.push({ fn: fn, resolve: resolve, reject: reject });
                pump();
            });
        };
    }
    var apiSlot = limiter(4);
    var pageSlot = limiter(1);

    var scripts = {};
    function loadScript(src) {
        if (!scripts[src]) {
            scripts[src] = new Promise(function (resolve, reject) {
                var tag = document.createElement("script");
                tag.src = src;
                tag.onload = resolve;
                tag.onerror = function () { reject(new Error("Could not load " + src)); };
                document.head.appendChild(tag);
            });
        }
        return scripts[src];
    }

    /* ---------- IndexedDB cache ---------- */

    var dbPromise;
    function db() {
        if (!dbPromise) {
            dbPromise = new Promise(function (resolve) {
                try {
                    var request = indexedDB.open("reader-covers", 1);
                    request.onupgradeneeded = function () { request.result.createObjectStore("covers"); };
                    request.onsuccess = function () { resolve(request.result); };
                    request.onerror = function () { resolve(null); };
                } catch (e) { resolve(null); }
            });
        }
        return dbPromise;
    }
    async function cacheGet(key) {
        var d = await db();
        if (!d) return null;
        return new Promise(function (resolve) {
            try {
                var r = d.transaction("covers").objectStore("covers").get(key);
                r.onsuccess = function () { resolve(r.result || null); };
                r.onerror = function () { resolve(null); };
            } catch (e) { resolve(null); }
        });
    }
    async function cachePut(key, value) {
        var d = await db();
        if (!d) return;
        try { d.transaction("covers", "readwrite").objectStore("covers").put(value, key); } catch (e) { /* quota */ }
    }

    /* ---------- thumbnails ---------- */

    function canvasToBlob(canvas) {
        return new Promise(function (resolve) { canvas.toBlob(resolve, "image/jpeg", 0.85); });
    }

    async function imageBlobToThumb(blob) {
        var url = URL.createObjectURL(blob);
        try {
            var img = new Image();
            img.src = url;
            await img.decode();
            var w = img.naturalWidth || WIDTH;
            var h = img.naturalHeight || Math.round(WIDTH * 1.5);
            var scale = Math.min(1, WIDTH / w);
            var canvas = document.createElement("canvas");
            canvas.width = Math.max(1, Math.round(w * scale));
            canvas.height = Math.max(1, Math.round(h * scale));
            var ctx = canvas.getContext("2d");
            ctx.fillStyle = "#fff";
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
            return await canvasToBlob(canvas);
        } finally {
            URL.revokeObjectURL(url);
        }
    }

    async function pdfFirstPage(book) {
        await loadScript(PDFJS);
        window.pdfjsLib.GlobalWorkerOptions.workerSrc = PDFJS_WORKER;
        var task = window.pdfjsLib.getDocument({
            url: window.BookFile.urlFor(book),
            disableAutoFetch: true
        });
        var doc = await task.promise;
        try {
            var page = await doc.getPage(1);
            var base = page.getViewport({ scale: 1 });
            var viewport = page.getViewport({ scale: WIDTH / base.width });
            var canvas = document.createElement("canvas");
            canvas.width = Math.round(viewport.width);
            canvas.height = Math.round(viewport.height);
            var ctx = canvas.getContext("2d");
            ctx.fillStyle = "#fff";
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            await page.render({ canvasContext: ctx, viewport: viewport }).promise;
            return await canvasToBlob(canvas);
        } finally {
            task.destroy();
        }
    }

    function joinPath(base, rel) {
        var url = new URL(rel, "http://epub/" + base);
        return decodeURIComponent(url.pathname.slice(1));
    }

    var MIME = { png: "image/png", jpg: "image/jpeg", jpeg: "image/jpeg", gif: "image/gif", svg: "image/svg+xml", webp: "image/webp" };

    async function epubFirstPage(book) {
        await loadScript(JSZIP);
        var buffer = await window.BookFile.download(window.BookFile.urlFor(book));
        var zip = await window.JSZip.loadAsync(buffer);

        var container = await zip.file("META-INF/container.xml").async("string");
        var opfPath = /full-path="([^"]+)"/.exec(container)[1];
        var opfDir = opfPath.indexOf("/") >= 0 ? opfPath.slice(0, opfPath.lastIndexOf("/") + 1) : "";
        var opf = new DOMParser().parseFromString(await zip.file(opfPath).async("string"), "application/xml");

        var items = Array.prototype.slice.call(opf.getElementsByTagName("item"));
        var byId = {};
        items.forEach(function (item) { byId[item.getAttribute("id")] = item; });
        var isImage = function (item) { return item && /^image\//.test(item.getAttribute("media-type") || ""); };

        var coverItem = items.filter(function (item) {
            return /(^|\s)cover-image(\s|$)/.test(item.getAttribute("properties") || "");
        })[0];
        if (!coverItem) {
            var metas = Array.prototype.slice.call(opf.getElementsByTagName("meta"));
            var meta = metas.filter(function (m) { return m.getAttribute("name") === "cover"; })[0];
            if (meta) coverItem = byId[meta.getAttribute("content")];
        }
        if (!isImage(coverItem)) coverItem = null;

        var entryPath;
        if (coverItem) {
            entryPath = joinPath(opfDir, coverItem.getAttribute("href"));
        } else {
            // "First page": the first spine document usually holds the cover image.
            var refs = opf.getElementsByTagName("itemref");
            var first = refs.length ? byId[refs[0].getAttribute("idref")] : null;
            if (!first) return null;
            var docPath = joinPath(opfDir, first.getAttribute("href"));
            var html = await zip.file(docPath).async("string");
            var found = /<img[^>]+src=["']([^"']+)["']/i.exec(html) ||
                /<image[^>]+href=["']([^"']+)["']/i.exec(html);
            if (!found) return null;
            entryPath = joinPath(docPath.slice(0, docPath.lastIndexOf("/") + 1), found[1]);
        }

        var entry = zip.file(entryPath);
        if (!entry) return null;
        var ext = entryPath.split(".").pop().toLowerCase();
        var data = await entry.async("arraybuffer");
        return imageBlobToThumb(new Blob([data], { type: MIME[ext] || "image/jpeg" }));
    }

    async function firstPage(book) {
        var type = String(book.type || "").toLowerCase();
        if (type === "pdf") return pdfFirstPage(book);
        if (type === "epub") return epubFirstPage(book);
        return null;
    }

    /* ---------- resolution ---------- */

    async function resolve(book) {
        var title = book.title || book.name || "";
        var cached = await cacheGet(String(book.id));
        if (cached && cached.title === title) {
            if (cached.source === "api" || Date.now() - cached.ts < RETRY_AFTER) return cached.blob;
        }

        var transient = false;
        try {
            var response = await apiSlot(function () {
                return fetch("/api/cover?title=" + encodeURIComponent(book.name || title));
            });
            if (response.ok) {
                var blob = await response.blob();
                await cachePut(String(book.id), { blob: blob, source: "api", title: title, ts: Date.now() });
                return blob;
            }
            if (response.status !== 404) transient = true;
        } catch (e) { transient = true; }

        // The catalogues had nothing: reuse the earlier first-page image if we have one.
        if (cached && cached.title === title) {
            cached.ts = Date.now();
            await cachePut(String(book.id), cached);
            return cached.blob;
        }

        try {
            var thumb = await pageSlot(function () { return firstPage(book); });
            if (thumb) {
                if (!transient) {
                    await cachePut(String(book.id), { blob: thumb, source: "page", title: title, ts: Date.now() });
                }
                return thumb;
            }
        } catch (e) {
            console.warn("First-page cover failed for", title, e);
        }
        return null;
    }

    /* ---------- DOM ---------- */

    var urls = {};
    var observer = null;
    var pending = new WeakMap();

    function show(el, url) {
        var img = el.querySelector("img.cover-img");
        if (!img) {
            img = document.createElement("img");
            img.className = "cover-img";
            img.alt = "";
            img.decoding = "async";
            el.appendChild(img);
        }
        img.onload = function () { el.classList.add("has-image"); el.classList.remove("is-loading"); };
        img.src = url;
    }

    async function load(el, book) {
        var key = String(book.id) + "|" + (book.title || book.name || "");
        if (urls[key]) { show(el, urls[key]); return; }
        el.classList.add("is-loading");
        try {
            var blob = await resolve(book);
            if (blob) {
                urls[key] = URL.createObjectURL(blob);
                show(el, urls[key]);
                return;
            }
        } catch (e) {
            console.warn("Cover failed:", e);
        }
        el.classList.remove("is-loading");
    }

    function attach(el, book) {
        if (!("IntersectionObserver" in window)) { load(el, book); return; }
        if (!observer) {
            observer = new IntersectionObserver(function (entries) {
                entries.forEach(function (entry) {
                    if (!entry.isIntersecting) return;
                    observer.unobserve(entry.target);
                    var item = pending.get(entry.target);
                    if (item) load(entry.target, item);
                });
            }, { rootMargin: "300px" });
        }
        pending.set(el, book);
        observer.observe(el);
    }

    window.Covers = { attach: attach };
})();
