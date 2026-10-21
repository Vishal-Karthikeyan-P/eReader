/* =============================================================
   Downloads a whole book through the /api/file proxy.

   Serverless hosts cap the size of a single response (Vercel: 4.5 MB),
   so the file is fetched in Range chunks and reassembled in the
   browser. If the server ignores Range, the full body is streamed.
============================================================= */
(function () {
    "use strict";

    var CHUNK = 3 * 1024 * 1024;
    var PARALLEL = 3;
    var RETRIES = 2;

    async function failure(response) {
        var detail = "";
        try {
            var text = await response.text();
            try {
                var json = JSON.parse(text);
                detail = json.error || json.message || "";
            } catch (e) { detail = text.slice(0, 200); }
        } catch (e) { /* ignore */ }
        if (/quota/i.test(detail)) {
            return new Error("Google Drive's download quota for this file has been reached. Try again later.");
        }
        if (response.status === 404 || response.status === 403) {
            return new Error("Google Drive refused the download (" + response.status +
                "). Check that the file is shared as \"Anyone with the link\".");
        }
        return new Error("Download failed (" + response.status + ")" + (detail ? ": " + detail : "."));
    }

    async function readStream(response, onProgress) {
        var total = Number(response.headers.get("Content-Length")) || 0;
        if (!response.body || !response.body.getReader) {
            var whole = await response.arrayBuffer();
            if (onProgress) onProgress(whole.byteLength, whole.byteLength);
            return whole;
        }
        var reader = response.body.getReader();
        var parts = [];
        var loaded = 0;
        for (;;) {
            var step = await reader.read();
            if (step.done) break;
            parts.push(step.value);
            loaded += step.value.length;
            if (onProgress) onProgress(loaded, total);
        }
        var out = new Uint8Array(loaded);
        var offset = 0;
        parts.forEach(function (part) { out.set(part, offset); offset += part.length; });
        return out.buffer;
    }

    async function fetchRange(url, start, end) {
        var lastError;
        for (var attempt = 0; attempt <= RETRIES; attempt++) {
            try {
                var response = await fetch(url, { headers: { Range: "bytes=" + start + "-" + end } });
                if (response.status === 206 || response.status === 200) {
                    return await response.arrayBuffer();
                }
                lastError = await failure(response);
                if (response.status < 500) break;
            } catch (error) {
                lastError = error;
            }
            await new Promise(function (r) { setTimeout(r, 400 * (attempt + 1)); });
        }
        throw lastError || new Error("Download failed.");
    }

    async function download(url, onProgress) {
        var first = await fetch(url, { headers: { Range: "bytes=0-" + (CHUNK - 1) } });
        if (!first.ok) throw await failure(first);

        // Server ignored Range: one streamed response.
        if (first.status === 200) return readStream(first, onProgress);

        var match = /\/(\d+)\s*$/.exec(first.headers.get("Content-Range") || "");
        var total = match ? Number(match[1]) : 0;
        var firstBuffer = await first.arrayBuffer();
        if (!total || firstBuffer.byteLength >= total) {
            if (onProgress) onProgress(firstBuffer.byteLength, firstBuffer.byteLength);
            return firstBuffer;
        }

        var out = new Uint8Array(total);
        out.set(new Uint8Array(firstBuffer), 0);
        var loaded = firstBuffer.byteLength;
        if (onProgress) onProgress(loaded, total);

        var starts = [];
        for (var s = CHUNK; s < total; s += CHUNK) starts.push(s);
        var next = 0;

        async function worker() {
            while (next < starts.length) {
                var start = starts[next++];
                var end = Math.min(total - 1, start + CHUNK - 1);
                var part = await fetchRange(url, start, end);
                out.set(new Uint8Array(part), start);
                loaded += part.byteLength;
                if (onProgress) onProgress(loaded, total);
            }
        }

        var workers = [];
        for (var i = 0; i < PARALLEL; i++) workers.push(worker());
        await Promise.all(workers);
        return out.buffer;
    }

    function urlFor(book) {
        var type = String(book.type || "").toLowerCase();
        var url = book.download_url || book.downloadUrl ||
            (book.id ? "/api/file/" + encodeURIComponent(book.id) + "?type=" + type : "");
        return url ? new URL(url, window.location.origin).toString() : "";
    }

    window.BookFile = { download: download, urlFor: urlFor };
})();
