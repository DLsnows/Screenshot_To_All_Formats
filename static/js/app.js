/* ==========================================================================
   app.js — SPA logic: routing, conversion, settings, hotkey recorder
   ========================================================================== */

const app = (() => {
    "use strict";

    /* ------------------------------------------------------------------ */
    /*  State                                                             */
    /* ------------------------------------------------------------------ */

    let currentTaskId = null;
    let pollInterval = null;
    let taskListInterval = null;
    let settingsCache = null;

    /* ------------------------------------------------------------------ */
    /*  DOM references (populated in init)                                */
    /* ------------------------------------------------------------------ */

    let $ = (sel) => document.querySelector(sel);
    let $$ = (sel) => document.querySelectorAll(sel);

    /* ------------------------------------------------------------------ */
    /*  View routing                                                      */
    /* ------------------------------------------------------------------ */

    function switchView(hash) {
        const view = hash === "#settings" ? "settings" : "main";

        // Update view visibility
        $$(".view").forEach(el => el.classList.remove("active"));
        const activeView = document.getElementById(`${view}-view`);
        if (activeView) activeView.classList.add("active");

        // Update nav link active state
        $$(".navbar-links a").forEach(el => {
            el.classList.toggle("active", el.getAttribute("href") === hash || (!hash && el.getAttribute("href") === "#main"));
        });

        // Load data when entering a view
        if (view === "settings") {
            populateSettingsForm();
        }
    }

    /* ------------------------------------------------------------------ */
    /*  Settings — load & populate form                                   */
    /* ------------------------------------------------------------------ */

    async function populateSettingsForm() {
        try {
            const s = await api.getSettings();
            settingsCache = s;

            $("#settings-default-input-path").value = s.defaults.input_path || "";
            $("#settings-default-output-path").value = s.defaults.output_path || "";
            $("#settings-default-language").value = s.defaults.language || "en";

            $("#settings-api-base-url").value = s.model.base_url || "";
            $("#settings-api-key").value = s.model.api_key || "";
            $("#settings-model-name").value = s.model.model_name || "";
            $("#settings-max-tokens").value = s.model.max_tokens || 30000;

            $("#settings-ui-language").value = s.ui.language || "en";
            $("#settings-default-format").value = s.ui.format || "markdown";
            $("#settings-copy-clipboard").checked = !!s.ui.copy_to_clipboard;

            $("#settings-hotkey-enabled").checked = !!s.hotkey.enabled;
            const combo = s.hotkey.combo || "ctrl+shift+v";
            $("#settings-hotkey-combo").value = friendlyCombo(combo);
            $("#settings-hotkey-combo").dataset.combo = combo;

            // Check hotkey listener status
            await refreshHotkeyStatus();

            showSettingsAlert("settingsLoaded", "success");
        } catch (err) {
            showSettingsAlert("settingsLoadFailed", "error", { error: err.message });
        }
    }

    async function refreshHotkeyStatus() {
        try {
            const status = await api.json("/hotkey/status");
            const indicator = $("#hotkey-status-indicator");
            const badge = $("#hotkey-status-badge");
            if (status.running) {
                indicator.style.display = "block";
                badge.className = "status-badge status-completed";
                badge.textContent = i18n.translate("hotkeyRunning");
            } else {
                indicator.style.display = "block";
                badge.className = "status-badge status-pending";
                badge.textContent = i18n.translate("hotkeyStopped");
            }
        } catch (_) {
            // ignore
        }
    }

    function gatherSettingsFromForm() {
        return {
            defaults: {
                input_path: $("#settings-default-input-path").value.trim(),
                output_path: $("#settings-default-output-path").value.trim(),
                language: $("#settings-default-language").value,
            },
            model: {
                base_url: $("#settings-api-base-url").value.trim(),
                api_key: $("#settings-api-key").value.trim(),
                model_name: $("#settings-model-name").value.trim() || "gpt-4o",
                max_tokens: parseInt($("#settings-max-tokens").value, 10) || 30000,
            },
            ui: {
                language: $("#settings-ui-language").value,
                format: $("#settings-default-format").value,
                copy_to_clipboard: $("#settings-copy-clipboard").checked,
            },
            hotkey: {
                enabled: $("#settings-hotkey-enabled").checked,
                combo: $("#settings-hotkey-combo").dataset.combo || "ctrl+shift+v",
            },
        };
    }

    function showSettingsAlert(key, type, params) {
        const el = $("#settings-alert");
        const msg = i18n.translate(key, params);
        el.innerHTML = `<div class="alert alert-${type}">${escapeHtml(msg)}</div>`;
        setTimeout(() => { el.innerHTML = ""; }, 4000);
    }

    function showToast(message) {
        const el = document.createElement("div");
        el.className = "alert alert-success";
        el.textContent = message;
        el.style.position = "fixed";
        el.style.bottom = "20px";
        el.style.right = "20px";
        el.style.zIndex = "9999";
        el.style.maxWidth = "400px";
        document.body.appendChild(el);
        setTimeout(() => { el.remove(); }, 3000);
    }

    async function saveSettings() {
        const btn = $("#save-settings-btn");
        const originalText = btn.textContent;
        btn.textContent = i18n.translate("savingSettingsBtn");
        btn.disabled = true;

        try {
            const settings = gatherSettingsFromForm();
            const saved = await api.saveSettings(settings);
            settingsCache = saved;

            // Sync UI language if changed
            const uiLang = saved.ui.language || "en";
            if (uiLang !== i18n.currentLang) {
                i18n.apply(uiLang);
            }

            showSettingsAlert("settingsSaved", "success");

            // Refresh hotkey status after save (may have changed)
            await refreshHotkeyStatus();
        } catch (err) {
            showSettingsAlert("settingsSaveFailed", "error", { error: err.message });
        } finally {
            btn.textContent = originalText;
            btn.disabled = false;
        }
    }

    /* ------------------------------------------------------------------ */
    /*  Main view — conversion form defaults                              */
    /* ------------------------------------------------------------------ */

    async function loadMainDefaults() {
        try {
            const s = settingsCache || await api.getSettings();
            settingsCache = s;

            if (s.defaults.input_path) $("#input-path").value = s.defaults.input_path;
            if (s.defaults.output_path) $("#output-path").value = s.defaults.output_path;
            if (s.defaults.language) $("#content-language").value = s.defaults.language;
            if (s.ui.format) $("#output-format").value = s.ui.format;
            $("#copy-clipboard").checked = s.ui.copy_to_clipboard !== false;
        } catch (err) {
            console.warn("Failed to load settings for defaults:", err);
        }
    }

    /* ------------------------------------------------------------------ */
    /*  Conversion — start & poll                                         */
    /* ------------------------------------------------------------------ */

    function gatherConversionParams() {
        const s = settingsCache;
        if (!s || !s.model || !s.model.api_key) {
            throw new Error(i18n.translate("errorNoApiKey"));
        }

        const inputPath = $("#input-path").value.trim();
        const outputPath = $("#output-path").value.trim();

        if (!inputPath) throw new Error(i18n.translate("errorNoInputPath"));
        if (!outputPath) throw new Error(i18n.translate("errorNoOutputPath"));

        return {
            input_path: inputPath,
            output_path: outputPath,
            language: $("#content-language").value,
            format: $("#output-format").value,
            copy_to_clipboard: $("#copy-clipboard").checked,
            model: {
                api_key: s.model.api_key,
                base_url: s.model.base_url,
                model_name: s.model.model_name,
                max_tokens: s.model.max_tokens,
            },
        };
    }

    async function startConversion() {
        // Prevent concurrent conversions
        if (pollInterval) {
            showToast(i18n.translate("conversionInProgress"));
            return;
        }

        // Validate first
        let params;
        try {
            params = gatherConversionParams();
        } catch (err) {
            showError(err.message);
            return;
        }

        // Disable button, show progress
        const btn = $("#start-btn");
        btn.disabled = true;
        btn.textContent = i18n.translate("startBtnRunning");

        showProgressCard();

        try {
            const result = await api.startConversion(params);
            currentTaskId = result.task_id;
            startPolling(result.task_id);
        } catch (err) {
            hideProgressCard();
            btn.disabled = false;
            btn.textContent = i18n.translate("startBtn");
            showError(i18n.translate("errorConvertFailed", { error: err.message }));
        }
    }

    let _lastPasteTime = 0;

    async function clipboardPaste() {
        const now = Date.now();
        if (now - _lastPasteTime < 2000) return;
        _lastPasteTime = now;

        const btn = $("#clipboard-paste-btn");
        btn.disabled = true;
        try {
            const result = await api.captureClipboard();
            if (result.error === "clipboard_empty") {
                showToast(i18n.translate("clipboardPasteEmpty"));
                return;
            }
            if (result.error) {
                showToast("Clipboard error: " + result.error);
                return;
            }
            // Fill input path (must be a directory — the conversion endpoint
            // scans the directory for all supported images)
            $("#input-path").value = result.path;
            showToast(
                i18n.translate("clipboardPasteSuccess") +
                " (" + result.filename + ")",
            );
        } catch (err) {
            showToast("Clipboard error: " + err.message);
        } finally {
            btn.disabled = false;
        }
    }

    function startPolling(taskId) {
        if (pollInterval) clearInterval(pollInterval);

        pollInterval = setInterval(async () => {
            try {
                const task = await api.getTaskStatus(taskId);
                updateProgressUI(task);

                if (task.status === "completed" || task.status === "error") {
                    stopPolling();
                    onTaskFinished(task);
                }
            } catch (err) {
                stopPolling();
                showError(i18n.translate("errorTaskNotFound"));
            }
        }, 1500);
    }

    function stopPolling() {
        if (pollInterval) {
            clearInterval(pollInterval);
            pollInterval = null;
        }
        const btn = $("#start-btn");
        btn.disabled = false;
        btn.textContent = i18n.translate("startBtn");
    }

    function updateProgressUI(task) {
        const pct = task.percentage || 0;
        $("#progress-fill").style.width = `${pct}%`;
        $("#progress-label").textContent = i18n.translate("progressText", {
            completed: task.progress,
            total: task.total,
        });
        $("#progress-pct").textContent = i18n.translate("progressPercent", { percent: pct });

        const badge = $("#status-badge");
        const title = $("#progress-title");
        const statusEl = $("#progress-status");

        switch (task.status) {
            case "pending":
                badge.className = "status-badge status-pending";
                badge.textContent = i18n.translate("taskStatusPending");
                title.textContent = i18n.translate("taskStatusPending");
                statusEl.textContent = "";
                break;
            case "running":
                badge.className = "status-badge status-running";
                badge.textContent = i18n.translate("taskStatusRunning");
                title.textContent = i18n.translate("taskStatusRunning");
                statusEl.textContent = "";
                break;
            case "completed":
                badge.className = "status-badge status-completed";
                badge.textContent = i18n.translate("taskStatusCompleted");
                title.textContent = i18n.translate("taskStatusCompleted");
                statusEl.textContent = i18n.translate("taskElapsed") + ": " + formatElapsed(task.elapsed);
                break;
            case "error":
                badge.className = "status-badge status-error";
                badge.textContent = i18n.translate("taskStatusError");
                title.textContent = i18n.translate("taskStatusError");
                statusEl.textContent = task.error || "";
                break;
        }
    }

    function onTaskFinished(task) {
        if (task.status === "completed") {
            // Show result preview
            const preview = $("#result-preview");
            preview.classList.add("visible");

            const content = task.combined_result || task.results.join("\n\n---\n\n");
            $("#result-content").textContent = content;

	        // Wire up copy button
            $("#copy-result-btn").onclick = () => {
                navigator.clipboard.writeText(content).then(() => {
                    const btn = $("#copy-result-btn");
                    const orig = btn.textContent;
                    btn.textContent = i18n.translate("copiedToast");
                    setTimeout(() => { btn.textContent = orig; }, 2000);
                }).catch(() => {
                    // fallback
                    const ta = document.createElement("textarea");
                    ta.value = content;
                    document.body.appendChild(ta);
                    ta.select();
                    document.execCommand("copy");
                    document.body.removeChild(ta);
                });
            };
        }

        // Refresh task list
        loadTaskList();
    }

    function showProgressCard() {
        const card = $("#progress-card");
        card.style.display = "block";
        $("#progress-fill").style.width = "0%";
        $("#progress-label").textContent = i18n.translate("progressText", { completed: 0, total: 0 });
        $("#progress-pct").textContent = i18n.translate("progressPercent", { percent: 0 });
        $("#result-preview").classList.remove("visible");
        updateProgressUI({ status: "pending", progress: 0, total: 0, percentage: 0, elapsed: 0 });
    }

    function hideProgressCard() {
        $("#progress-card").style.display = "none";
    }

    /* ------------------------------------------------------------------ */
    /*  Upload                                                            */
    /* ------------------------------------------------------------------ */

    async function handleUpload(files) {
        if (!files || files.length === 0) return;
        try {
            $("#upload-btn").disabled = true;
            $("#upload-btn").textContent = i18n.translate("uploadBtnRunning");
            const result = await api.uploadFiles(files);
            $("#input-path").value = result.upload_dir;
            $("#upload-btn").textContent = i18n.translate("uploadBtn");
            $("#upload-btn").disabled = false;
        } catch (err) {
            $("#upload-btn").textContent = i18n.translate("uploadBtn");
            $("#upload-btn").disabled = false;
            showError(i18n.translate("errorConvertFailed", { error: err.message }));
        }
    }

    /* ------------------------------------------------------------------ */
    /*  Task list                                                         */
    /* ------------------------------------------------------------------ */

    async function loadTaskList() {
        try {
            const tasks = await api.getTasks(20);
            const tbody = $("#task-tbody");
            const table = $("#task-table");
            const empty = $("#task-empty");

            if (!tasks || tasks.length === 0) {
                table.style.display = "none";
                empty.style.display = "block";
                return;
            }

            empty.style.display = "none";
            table.style.display = "";
            tbody.innerHTML = tasks.map(t => renderTaskRow(t)).join("");

            // Auto-track hotkey-triggered tasks: catch both running tasks
            // (for live progress) and recently-completed tasks (that finished
            // before the 5 s polling interval caught up with them).
            if (!pollInterval && tasks.length > 0) {
                const now_ts = Date.now() / 1000;
                const latest = tasks[0];
                if (latest.id !== currentTaskId) {
                    const age = now_ts - latest.created_at;
                    if (latest.status === "running") {
                        currentTaskId = latest.id;
                        showProgressCard();
                        startPolling(latest.id);
                    } else if (latest.status === "completed" && age < 10) {
                        currentTaskId = latest.id;
                        showProgressCard();
                        updateProgressUI(latest);
                        onTaskFinished(latest);
                    }
                }
            }
        } catch (err) {
            console.warn("Failed to load task list:", err);
        }
    }

    function renderTaskRow(task) {
        const statusKey = "taskStatus" + task.status.charAt(0).toUpperCase() + task.status.slice(1);
        const statusText = i18n.translate(statusKey) || task.status;
        const badgeClass = `status-badge status-${task.status}`;
        const pct = task.percentage || 0;
        const elapsedStr = formatElapsed(task.elapsed);
        const createdStr = formatTimestamp(task.created_at);

        let actions = `<button class="btn btn-ghost btn-sm task-delete-btn" data-task-id="${task.id}" data-i18n="taskDeleteBtn">Delete</button>`;

        return `<tr>
            <td>${task.progress}/${task.total}</td>
            <td><span class="${badgeClass}">${statusText}</span></td>
            <td>${task.format}</td>
            <td>${createdStr}</td>
            <td>${elapsedStr}</td>
            <td class="task-actions">${actions}</td>
        </tr>`;
    }

    /* ------------------------------------------------------------------ */
    /*  Hotkey recorder                                                   */
    /* ------------------------------------------------------------------ */

    const hotkeyRecorder = {
        active: false,
        pressedMods: new Set(),
        mainKey: null,
        comboInput: null,
        recordBtn: null,
        hintEl: null,
        finalizeTimer: null,

        init() {
            this.comboInput = $("#settings-hotkey-combo");
            this.recordBtn = $("#hotkey-record-btn");
            this.hintEl = $("#hotkey-hint");
            const clearBtn = $("#hotkey-clear-btn");

            this.recordBtn.addEventListener("click", () => this.toggle());
            clearBtn.addEventListener("click", () => this.clear());

            // Global keyboard capture
            document.addEventListener("keydown", (e) => this.onKeyDown(e));
            document.addEventListener("keyup", (e) => this.onKeyUp(e));
        },

        toggle() {
            if (this.active) {
                this.cancel();
            } else {
                this.start();
            }
        },

        start() {
            if (this.active) return;
            this.active = true;
            this.pressedMods.clear();
            this.mainKey = null;
            this.comboInput.value = i18n.translate("hotkeyRecording");
            this.comboInput.classList.add("recording");
            this.recordBtn.textContent = i18n.translate("cancel");
            // Give focus to input so blur can cancel
            this.comboInput.focus();
        },

        cancel() {
            this.active = false;
            this.pressedMods.clear();
            this.mainKey = null;
            this.comboInput.classList.remove("recording");
            this.recordBtn.textContent = i18n.translate("hotkeyRecordBtn");
            if (this.finalizeTimer) {
                clearTimeout(this.finalizeTimer);
                this.finalizeTimer = null;
            }

            // Restore existing combo display
            const existing = this.comboInput.dataset.combo;
            if (existing) {
                this.comboInput.value = friendlyCombo(existing);
            } else {
                this.comboInput.value = "";
            }
        },

        clear() {
            this.cancel();
            delete this.comboInput.dataset.combo;
            this.comboInput.value = "";
        },

        /**
         * Read modifier state from the event's built-in flags.
         * This is far more reliable than tracking keydown/keyup for
         * modifier keys individually.
         */
        readModifiersFromEvent(e) {
            this.pressedMods.clear();
            if (e.ctrlKey)  this.pressedMods.add("ctrl");
            if (e.altKey)   this.pressedMods.add("alt");
            if (e.shiftKey) this.pressedMods.add("shift");
            if (e.metaKey)  this.pressedMods.add("win");
        },

        onKeyDown(e) {
            if (!this.active) return;

            const key = this.normalizeKey(e);
            if (!key) return;

            // Escape cancels
            if (key === "escape") {
                e.preventDefault();
                this.cancel();
                return;
            }

            e.preventDefault();

            // Read modifier state from the event itself (always accurate)
            this.readModifiersFromEvent(e);

            // Track the main key (last non-modifier key wins)
            if (!this.isModifier(key)) {
                this.mainKey = key;
            }

            // Show current combo in real time
            this.comboInput.value = this.buildFriendly();

            // Safety timeout: if keyup events don't fire (e.g. user
            // switches focus while holding keys), finalize after 1 s
            if (this.mainKey && !this.finalizeTimer) {
                this.finalizeTimer = setTimeout(() => {
                    if (this.active && this.mainKey) {
                        this.finalize();
                    }
                }, 1000);
            }
        },

        onKeyUp(e) {
            if (!this.active) return;

            // Read modifier state from the event
            this.readModifiersFromEvent(e);

            // If no modifiers held and we have a main key → finalize
            if (!e.ctrlKey && !e.altKey && !e.shiftKey && !e.metaKey && this.mainKey) {
                if (this.finalizeTimer) {
                    clearTimeout(this.finalizeTimer);
                    this.finalizeTimer = null;
                }
                this.finalize();
            }
        },

        finalize() {
            const combo = this.buildCombo();
            this.comboInput.dataset.combo = combo;
            this.comboInput.value = friendlyCombo(combo);
            this.comboInput.classList.remove("recording");
            this.active = false;
            this.recordBtn.textContent = i18n.translate("hotkeyRecordBtn");
            if (this.finalizeTimer) {
                clearTimeout(this.finalizeTimer);
                this.finalizeTimer = null;
            }
        },

        normalizeKey(e) {
            const k = e.key;
            if (!k) return null;
            // Map physical key names
            const map = {
                "Control": "ctrl",
                "Alt": "alt",
                "Shift": "shift",
                "Meta": "win",
                "Escape": "escape",
            };
            if (map[k] !== undefined) return map[k];
            // Single characters
            if (k.length === 1) return k.toLowerCase();
            // Function keys, arrows, etc.
            return k.toLowerCase();
        },

        isModifier(key) {
            return ["ctrl", "alt", "shift", "win"].includes(key);
        },

        buildCombo() {
            const mods = Array.from(this.pressedMods).sort();
            if (this.mainKey) mods.push(this.mainKey);
            return mods.join("+");
        },

        buildFriendly() {
            const mods = Array.from(this.pressedMods).sort();
            const parts = mods.map(m => m.charAt(0).toUpperCase() + m.slice(1));
            if (this.mainKey) parts.push(this.mainKey.toUpperCase());
            return parts.join("+");
        },
    };

    /* ------------------------------------------------------------------ */
    /*  Format helpers                                                    */
    /* ------------------------------------------------------------------ */

    function friendlyCombo(combo) {
        if (!combo) return "";
        return combo.split("+").map(part => {
            if (["ctrl", "alt", "shift", "win"].includes(part)) {
                return part.charAt(0).toUpperCase() + part.slice(1);
            }
            return part.toUpperCase();
        }).join("+");
    }

    function formatElapsed(seconds) {
        if (!seconds && seconds !== 0) return "-";
        if (seconds < 1) return "<1s";
        if (seconds < 60) return Math.round(seconds) + "s";
        const m = Math.floor(seconds / 60);
        const s = Math.round(seconds % 60);
        return `${m}m ${s}s`;
    }

    function formatTimestamp(ts) {
        if (!ts) return "-";
        const d = new Date(ts * 1000);
        const pad = (n) => String(n).padStart(2, "0");
        return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
    }

    function escapeHtml(str) {
        const div = document.createElement("div");
        div.textContent = str;
        return div.innerHTML;
    }

    /* ------------------------------------------------------------------ */
    /*  Notifications / alerts                                            */
    /* ------------------------------------------------------------------ */

    function showError(message) {
        const card = $("#progress-card");
        const existing = card.querySelector(".alert");
        if (existing) existing.remove();

        const div = document.createElement("div");
        div.className = "alert alert-error";
        div.textContent = message;
        card.insertBefore(div, card.firstChild);
    }

    /* ------------------------------------------------------------------ */
    /*  Event binding                                                     */
    /* ------------------------------------------------------------------ */

    function bindEvents() {
        // Navigation
        window.addEventListener("hashchange", () => switchView(location.hash));

        // Language toggle
        document.querySelector(".lang-toggle").addEventListener("click", () => {
            const next = i18n.currentLang === "en" ? "zh" : "en";
            i18n.apply(next);
            // Re-translate dynamic content
            loadTaskList();
        });

        // Start conversion
        $("#start-btn").addEventListener("click", startConversion);

        // Upload
        $("#upload-btn").addEventListener("click", () => $("#file-input").click());
        $("#file-input").addEventListener("change", (e) => handleUpload(e.target.files));

        // Upload drag-and-drop
        const zone = $("#upload-zone");
        zone.addEventListener("dragover", (e) => {
            e.preventDefault();
            zone.style.borderColor = "#22c55e";
        });
        zone.addEventListener("dragleave", () => {
            zone.style.borderColor = "#333333";
        });
        zone.addEventListener("drop", (e) => {
            e.preventDefault();
            zone.style.borderColor = "#333333";
            handleUpload(e.dataTransfer.files);
        });

        // Settings save
        $("#save-settings-btn").addEventListener("click", saveSettings);

        // Settings reset
        $("#reset-settings-btn").addEventListener("click", async () => {
            if (settingsCache) {
                const defaults = {
                    defaults: { input_path: "", output_path: "", language: "en" },
                    model: { base_url: "https://api.openai.com/v1", api_key: "", model_name: "gpt-4o", max_tokens: 30000 },
                    ui: { language: "en", format: "markdown", copy_to_clipboard: true },
                    hotkey: { enabled: false, combo: "ctrl+shift+v", auto_start: true },
                };
                try {
                    await api.saveSettings(defaults);
                    await populateSettingsForm();
                    showSettingsAlert("settingsSaved", "success");
                } catch (err) {
                    showSettingsAlert("settingsSaveFailed", "error", { error: err.message });
                }
            }
        });

        // UI language change in settings → preview
        $("#settings-ui-language").addEventListener("change", function () {
            i18n.apply(this.value);
        });

        // Task list action delegation
        $("#task-tbody").addEventListener("click", async (e) => {
            const btn = e.target.closest("button");
            if (!btn) return;
            const taskId = btn.dataset.taskId;
            if (!taskId) return;

            if (btn.classList.contains("task-delete-btn")) {
                try {
                    await api.deleteTask(taskId);
                    loadTaskList();
                } catch (err) {
                    console.warn("Delete failed:", err);
                }
            }
        });

        // Clipboard paste button
        $("#clipboard-paste-btn").addEventListener("click", clipboardPaste);

        // Keyboard shortcut: Enter to start conversion on main view
        document.addEventListener("keydown", (e) => {
            if (e.key === "Enter" && document.getElementById("main-view").classList.contains("active")) {
                const active = document.activeElement;
                if (active && (active.tagName === "INPUT" || active.tagName === "SELECT")) {
                    startConversion();
                }
            }
        });
    }

    /* ------------------------------------------------------------------ */
    /*  Init                                                              */
    /* ------------------------------------------------------------------ */

    async function init() {
        // Load settings
        try {
            settingsCache = await api.getSettings();
        } catch (_) { /* offline-capable */ }

        // Init i18n
        i18n.init();

        // Populate main view defaults
        await loadMainDefaults();

        // Init hotkey recorder
        hotkeyRecorder.init();

        // Bind events
        bindEvents();

        // Switch to initial view
        switchView(location.hash || "#main");

        // Load task list
        await loadTaskList();

        // Periodically refresh task list (picks up hotkey-triggered tasks)
        taskListInterval = setInterval(() => loadTaskList(), 5000);
    }

    /* ------------------------------------------------------------------ */
    /*  Public API                                                        */
    /* ------------------------------------------------------------------ */

    return { init };
})();

/* ---------------------------------------------------------------------- */
/*  Bootstrap                                                             */
/* ---------------------------------------------------------------------- */

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => app.init());
} else {
    app.init();
}
