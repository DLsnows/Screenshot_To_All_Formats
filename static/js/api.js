/* ==========================================================================
   API Client — fetch wrappers for all backend endpoints
   ==========================================================================
   Usage:
       import { api } from "./api.js";        // ES module
       // or just use the global `api` object:
       const settings = await api.getSettings();
   ========================================================================== */

const api = (() => {
    "use strict";

    /* ------------------------------------------------------------------ */
    /*  Base URL                                                          */
    /* ------------------------------------------------------------------ */

    const BASE = "/api";

    /* ------------------------------------------------------------------ */
    /*  Generic helpers                                                   */
    /* ------------------------------------------------------------------ */

    /**
     * Core request helper.  Throws an Error with the server's detail
     * message (or the status text) when the response is not OK.
     */
    async function request(path, options = {}) {
        const url = `${BASE}${path}`;
        const {
            method = "GET",
            body = null,
            headers = {},
        } = options;

        const cfg = {
            method,
            headers: { "Accept": "application/json", ...headers },
        };

        if (body !== null) {
            if (body instanceof FormData) {
                // Let the browser set Content-Type (with boundary)
                cfg.body = body;
            } else {
                cfg.headers["Content-Type"] = "application/json";
                cfg.body = JSON.stringify(body);
            }
        }

        let res;
        try {
            res = await fetch(url, cfg);
        } catch (err) {
            throw new Error(`Network error: ${err.message}`);
        }

        if (!res.ok) {
            let detail = res.statusText;
            try {
                const errBody = await res.json();
                if (errBody.detail) detail = errBody.detail;
            } catch (_) { /* ignore */ }
            throw new Error(detail);
        }

        return res;
    }

    /** Parse JSON body. */
    async function json(path, options) {
        const res = await request(path, options);
        return res.json();
    }

    /** Parse text body. */
    async function text(path, options) {
        const res = await request(path, options);
        return res.text();
    }

    /** Get a blob (for file downloads). */
    async function blob(path, options) {
        const res = await request(path, options);
        return res.blob();
    }

    /* ------------------------------------------------------------------ */
    /*  Settings API                                                      */
    /* ------------------------------------------------------------------ */

    /**
     * Fetch all current settings.
     * @returns {Promise<{
     *   defaults: {input_path:string, output_path:string},
     *   model:    {base_url:string, api_key:string, model_name:string, max_tokens:number},
     *   ui:       {language:string, format:string, copy_to_clipboard:boolean},
     *   hotkey:   {enabled:boolean, combo:string, auto_start:boolean},
     * }>}
     */
    async function getSettings() {
        return json("/settings");
    }

    /**
     * Update and persist settings.
     * @param {object} settings  Full or partial settings object.
     * @returns {Promise<object>}  The full settings after save.
     */
    async function saveSettings(settings) {
        return json("/settings", {
            method: "PUT",
            body: settings,
        });
    }

    /**
     * Get supported content languages (e.g. ["cn","en","fr"]).
     * @returns {Promise<string[]>}
     */
    async function getLanguages() {
        return json("/languages");
    }

    /**
     * Get supported UI languages (e.g. ["en","zh"]).
     * @returns {Promise<string[]>}
     */
    async function getUiLanguages() {
        return json("/ui-languages");
    }

    /**
     * Get supported output formats.
     * @returns {Promise<string[]>}
     */
    async function getFormats() {
        return json("/formats");
    }

    /* ------------------------------------------------------------------ */
    /*  Conversion API                                                    */
    /* ------------------------------------------------------------------ */

    /**
     * Start a new conversion task.
     * @param {{
     *   input_path:  string,
     *   output_path: string,
     *   language:    string,
     *   format:      string,
     *   copy_to_clipboard: boolean,
     *   model:       { api_key:string, base_url:string, model_name:string, max_tokens:number },
     * }} params
     * @returns {Promise<{ task_id:string, total_images:number }>}
     */
    async function startConversion(params) {
        return json("/convert", {
            method: "POST",
            body: params,
        });
    }

    /**
     * Poll the status of a conversion task.
     * @param {string} taskId
     * @returns {Promise<{
     *   id: string,
     *   status: string,
     *   progress: number,
     *   total: number,
     *   percentage: number,
     *   results: string[],
     *   combined_result: string,
     *   error: string|null,
     *   input_path: string,
     *   output_path: string,
     *   language: string,
     *   format: string,
     *   created_at: number,
     *   completed_at: number|null,
     *   elapsed: number,
     * }>}
     */
    async function getTaskStatus(taskId) {
        return json(`/tasks/${encodeURIComponent(taskId)}`);
    }

    /**
     * List recent tasks (newest first).
     * @param {number} [limit=50]
     * @returns {Promise<Array>}
     */
    async function getTasks(limit = 50) {
        return json(`/tasks?limit=${limit}`);
    }

    /**
     * Delete a task.
     * @param {string} taskId
     * @returns {Promise<{ deleted: string }>}
     */
    async function deleteTask(taskId) {
        return json(`/tasks/${encodeURIComponent(taskId)}`, {
            method: "DELETE",
        });
    }

    /**
     * Download the combined result file for a completed task.
     * Triggers a browser download via a temporary anchor element.
     * @param {string} taskId
     * @param {string} [filename]  Optional filename for the download.
     */
    async function downloadResult(taskId, filename) {
        const res = await request(`/tasks/${encodeURIComponent(taskId)}/download`);
        const blob = await res.blob();

        // Get filename from Content-Disposition header, or use provided name
        const disp = res.headers.get("Content-Disposition");
        let name = filename || "all_in_one";
        if (disp) {
            const match = disp.match(/filename\*?=(?:UTF-8'')?["']?([^"'\s;]+)/i);
            if (match) name = decodeURIComponent(match[1]);
        }

        // Trigger download
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = name;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }

    /**
     * Get the download URL for a completed task (useful for <a> links).
     * @param {string} taskId
     * @returns {string}  The relative URL path.
     */
    function getDownloadUrl(taskId) {
        return `${BASE}/tasks/${encodeURIComponent(taskId)}/download`;
    }

    /* ------------------------------------------------------------------ */
    /*  Upload API                                                        */
    /* ------------------------------------------------------------------ */

    /**
     * Upload image files to the server.
     * @param {FileList|File[]} files
     * @returns {Promise<{ uploaded:string[], upload_dir:string }>}
     */
    async function uploadFiles(files) {
        const fd = new FormData();
        for (const f of files) {
            fd.append("files", f);
        }
        return json("/upload", {
            method: "POST",
            body: fd,
        });
    }

    /* ------------------------------------------------------------------ */
    /*  Public API                                                        */
    /* ------------------------------------------------------------------ */

    return {
        // Settings
        getSettings,
        saveSettings,
        getLanguages,
        getUiLanguages,
        getFormats,

        // Conversion
        startConversion,
        getTaskStatus,
        getTasks,
        deleteTask,
        downloadResult,
        getDownloadUrl,

        // Upload
        uploadFiles,

        // Low-level (for custom endpoints)
        request,
        json,
        text,
        blob,
    };
})();
