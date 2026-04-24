/* ==========================================================================
   i18n — Chinese / English Translation Module
   ==========================================================================
   Usage:
       <label data-i18n="inputPathLabel"></label>
       <input data-i18n-placeholder="inputPathPlaceholder">
       <option data-i18n-option="langCn" value="cn"></option>

       i18n.apply("en");   // switch to English
       i18n.currentLang;   // "en" | "zh"
   ========================================================================== */

const i18n = (() => {
    "use strict";

    /* ------------------------------------------------------------------ */
    /*  Translations                                                      */
    /* ------------------------------------------------------------------ */

    const TRANSLATIONS = {

        /* ============================================================== */
        /*  Navigation                                                     */
        /* ============================================================== */

        brandTitle:          { en: "Screenshot_To_All_Formats", zh: "Screenshot_To_All_Formats" },
        navHome:             { en: "Home",             zh: "首页" },
        navSettings:         { en: "Settings",         zh: "设置" },
        langSwitch:          { en: "中文",              zh: "EN" },

        /* ============================================================== */
        /*  Main View — Conversion Page                                    */
        /* ============================================================== */

        pageTitle:           { en: "Image to Text Converter", zh: "图片转文本转换器" },

        inputPathLabel:      { en: "Input Path",       zh: "输入路径" },
        inputPathPlaceholder:{ en: "Folder containing images…", zh: "图片所在文件夹路径…" },
        outputPathLabel:     { en: "Output Path",      zh: "输出路径" },
        outputPathPlaceholder:{en: "Where to save results…", zh: "结果保存文件夹路径…" },

        languageLabel:       { en: "Content Language", zh: "内容语言" },
        langCn:              { en: "Chinese",          zh: "中文" },
        langEn:              { en: "English",          zh: "英文" },
        langFr:              { en: "French",           zh: "法文" },

        formatLabel:         { en: "Output Format",    zh: "输出格式" },
        formatMarkdown:      { en: "Markdown",         zh: "Markdown" },
        formatHtml:          { en: "HTML",             zh: "HTML" },
        formatCsv:           { en: "CSV",              zh: "CSV" },
        formatJson:          { en: "JSON",             zh: "JSON" },
        formatLatex:         { en: "LaTeX",            zh: "LaTeX" },
        formatText:          { en: "Plain Text",       zh: "纯文本" },
        formatCode:          { en: "Code",             zh: "代码" },

        copyClipboardLabel:  { en: "Copy result to clipboard", zh: "复制结果到剪贴板" },

        startBtn:            { en: "Start Conversion", zh: "开始转换" },
        startBtnRunning:     { en: "Converting…",      zh: "转换中…" },
        conversionInProgress:{ en: "A conversion is already in progress", zh: "已有任务正在转换中" },

        uploadBtn:           { en: "Upload & Convert", zh: "上传并转换" },
        uploadBtnRunning:    { en: "Uploading…",       zh: "上传中…" },
        uploadDropHint:     { en: "Drop images here or click to upload", zh: "拖拽图片到此处或点击上传" },
        uploadLimitHint:    { en: "Supported: PNG, JPG, WEBP, BMP, GIF", zh: "支持格式：PNG、JPG、WEBP、BMP、GIF" },

        clipboardPasteBtn:   { en: "Paste from Clipboard", zh: "从剪贴板粘贴" },
        clipboardPasteSuccess:{en: "Clipboard image captured!", zh: "剪贴板图片已捕获！" },
        clipboardPasteEmpty: { en: "Clipboard contains no image", zh: "剪贴板中没有图片" },
        clickTooFast:        { en: "Please wait a moment before pasting again", zh: "请稍后再粘贴" },

        /* ============================================================== */
        /*  Task Progress & Status                                         */
        /* ============================================================== */

        taskStatusPending:   { en: "Pending",          zh: "等待中" },
        taskStatusRunning:   { en: "Running",          zh: "处理中" },
        taskStatusCompleted: { en: "Completed",         zh: "已完成" },
        taskStatusError:     { en: "Error",            zh: "出错" },
        taskStatusCancelled: { en: "Cancelled",        zh: "已取消" },

        progressText:        { en: "{completed} / {total} images", zh: "{completed} / {total} 张图片" },
        progressPercent:     { en: "{percent}%",        zh: "{percent}%" },

        resultPreviewTitle:  { en: "Result Preview",   zh: "结果预览" },
        downloadBtn:         { en: "Download",         zh: "下载" },
        copyResultBtn:       { en: "Copy to Clipboard",zh: "复制到剪贴板" },
        copiedToast:         { en: "Copied!",          zh: "已复制！" },
        viewDetailBtn:      { en: "Details",           zh: "详情" },

        taskCreated:         { en: "Created",           zh: "创建时间" },
        taskElapsed:         { en: "Elapsed",           zh: "耗时" },
        taskActions:         { en: "Actions",           zh: "操作" },
        taskDeleteBtn:      { en: "Delete",            zh: "删除" },

        taskHistory:         { en: "History",           zh: "历史记录" },
        noTasks:             { en: "No conversion tasks yet.", zh: "暂无转换任务。" },
        noTasksHint:         { en: "Select images and click start above.", zh: "请选择图片后点击上方的开始转换。" },

        /* ============================================================== */
        /*  Settings View                                                  */
        /* ============================================================== */

        settingsTitle:       { en: "Settings",         zh: "设置" },
        settingsSaved:       { en: "Settings saved successfully!", zh: "设置已保存成功！" },
        settingsSaveFailed: { en: "Failed to save settings: {error}", zh: "保存设置失败：{error}" },
        settingsLoaded:     { en: "Settings loaded.",  zh: "设置已加载。" },
        settingsLoadFailed: { en: "Failed to load settings: {error}", zh: "加载设置失败：{error}" },

        sectionPaths:        { en: "Default Paths",    zh: "默认路径" },
        sectionModel:        { en: "Model Configuration", zh: "模型配置" },
        sectionUi:           { en: "Display Settings", zh: "显示设置" },
        sectionHotkey:       { en: "Hotkey Settings",  zh: "快捷键设置" },

        defaultInputPathLabel:{en: "Default Input Path", zh: "默认输入路径" },
        defaultOutputPathLabel:{en:"Default Output Path",zh: "默认输出路径" },

        apiBaseUrlLabel:     { en: "API Base URL",     zh: "API 地址" },
        apiBaseUrlPlaceholder:{en:"https://api.openai.com/v1", zh:"https://api.openai.com/v1" },
        apiKeyLabel:         { en: "API Key",          zh: "API 密钥" },
        apiKeyPlaceholder:   { en: "sk-…",             zh: "sk-…" },
        modelNameLabel:      { en: "Model Name",       zh: "模型名称" },
        modelNamePlaceholder:{ en: "gpt-4o",           zh: "gpt-4o" },
        maxTokensLabel:      { en: "Max Tokens",       zh: "最大 Token 数" },

        uiLanguageLabel:     { en: "UI Language",      zh: "界面语言" },
        uiLangEn:            { en: "English",          zh: "英文" },
        uiLangZh:            { en: "Chinese",          zh: "中文" },
        defaultFormatLabel:  { en: "Default Format",   zh: "默认格式" },

        hotkeyEnableLabel:   { en: "Enable Global Hotkey", zh: "启用全局快捷键" },
        hotkeyComboLabel:    { en: "Shortcut Key",     zh: "快捷键组合" },
        hotkeyPlaceholder:   { en: "Click to record…", zh: "点击录制…" },
        hotkeyRecording:     { en: "Press shortcut…",  zh: "按下快捷键…" },
        hotkeyRecordBtn:     { en: "Record",           zh: "录制" },
        hotkeyClearBtn:      { en: "Clear",            zh: "清除" },
        hotkeyHint:          { en: "Press your desired key combination", zh: "按下您想要设置的快捷键组合" },
        hotkeyRunning:       { en: "Hotkey listener is running", zh: "快捷键监听器运行中" },
        hotkeyStopped:       { en: "Hotkey listener is stopped", zh: "快捷键监听器已停止" },

        saveSettingsBtn:     { en: "Save Settings",    zh: "保存设置" },
        savingSettingsBtn:   { en: "Saving…",          zh: "保存中…" },
        resetSettingsBtn:    { en: "Reset to Defaults",zh: "恢复默认" },

        /* ============================================================== */
        /*  Errors & Alerts                                                */
        /* ============================================================== */

        errorNoInputPath:    { en: "Please enter an input path.", zh: "请输入输入路径。" },
        errorNoOutputPath:   { en: "Please enter an output path.", zh: "请输入输出路径。" },
        errorNoApiKey:       { en: "Please configure API Key in Settings first.", zh: "请先在设置中配置 API 密钥。" },
        errorNoImages:       { en: "No supported images found in the input path.", zh: "输入路径中未找到支持的图片文件。" },
        errorConvertFailed:  { en: "Conversion failed: {error}", zh: "转换失败：{error}" },
        errorNetwork:        { en: "Network error, please check the connection.", zh: "网络错误，请检查网络连接。" },
        errorUnknown:        { en: "An unknown error occurred.", zh: "发生未知错误。" },
        errorTaskNotFound:   { en: "Task not found.",   zh: "任务未找到。" },

        /* ============================================================== */
        /*  Misc / Generic                                                 */
        /* ============================================================== */

        loading:             { en: "Loading…",         zh: "加载中…" },
        saving:              { en: "Saving…",          zh: "保存中…" },
        confirmDelete:       { en: "Are you sure you want to delete this task?", zh: "确定要删除此任务吗？" },
        close:               { en: "Close",            zh: "关闭" },
        cancel:              { en: "Cancel",           zh: "取消" },
        ok:                  { en: "OK",               zh: "确定" },
    };

    /* ------------------------------------------------------------------ */
    /*  State                                                             */
    /* ------------------------------------------------------------------ */

    let currentLang = localStorage.getItem("ui-lang") || "en";
    let fallbackLang = "en";

    /* ------------------------------------------------------------------ */
    /*  Core helpers                                                      */
    /* ------------------------------------------------------------------ */

    function t(key, lang) {
        const entry = TRANSLATIONS[key];
        if (!entry) return `{${key}}`;
        return entry[lang] || entry[fallbackLang] || `{${key}}`;
    }

    function replacePlaceholders(text, params) {
        if (!params) return text;
        return Object.keys(params).reduce(
            (str, k) => str.replace(new RegExp(`\\{${k}\\}`, "g"), params[k]),
            text,
        );
    }

    /* ------------------------------------------------------------------ */
    /*  DOM update                                                        */
    /* ------------------------------------------------------------------ */

    function apply(lang) {
        lang = lang || currentLang;
        currentLang = lang;
        localStorage.setItem("ui-lang", lang);

        // 1. data-i18n — replace textContent
        document.querySelectorAll("[data-i18n]").forEach(el => {
            const key = el.getAttribute("data-i18n");
            const raw = t(key, lang);
            el.textContent = raw;
        });

        // 2. data-i18n-placeholder
        document.querySelectorAll("[data-i18n-placeholder]").forEach(el => {
            const key = el.getAttribute("data-i18n-placeholder");
            el.placeholder = t(key, lang);
        });

        // 3. data-i18n-option — options inside <select>
        document.querySelectorAll("[data-i18n-option]").forEach(el => {
            const key = el.getAttribute("data-i18n-option");
            el.textContent = t(key, lang);
        });

        // 4. data-i18n-title — tooltip / title attribute
        document.querySelectorAll("[data-i18n-title]").forEach(el => {
            const key = el.getAttribute("data-i18n-title");
            el.title = t(key, lang);
        });

        // 5. data-i18n-value — value attribute (buttons, inputs)
        document.querySelectorAll("[data-i18n-value]").forEach(el => {
            const key = el.getAttribute("data-i18n-value");
            el.value = t(key, lang);
        });

        // 6. data-i18n-label — label text for custom elements
        document.querySelectorAll("[data-i18n-label]").forEach(el => {
            const key = el.getAttribute("data-i18n-label");
            el.setAttribute("aria-label", t(key, lang));
        });

        // 7. Update lang-toggle button text
        const langToggle = document.querySelector(".lang-toggle");
        if (langToggle) {
            langToggle.textContent = t("langSwitch", lang);
        }

        // 8. Dispatch custom event for any JS-driven updates
        document.dispatchEvent(new CustomEvent("i18n:changed", {
            detail: { lang },
        }));
    }

    /* ------------------------------------------------------------------ */
    /*  Translation helper — for JS usage                                  */
    /* ------------------------------------------------------------------ */

    function translate(key, params) {
        const raw = t(key, currentLang);
        return params ? replacePlaceholders(raw, params) : raw;
    }

    /* ------------------------------------------------------------------ */
    /*  Init — auto-apply on DOM ready                                     */
    /* ------------------------------------------------------------------ */

    function init() {
        // Wait for DOM if not already ready
        if (document.readyState === "loading") {
            document.addEventListener("DOMContentLoaded", () => apply(currentLang));
        } else {
            apply(currentLang);
        }
    }

    /* ------------------------------------------------------------------ */
    /*  Public API                                                        */
    /* ------------------------------------------------------------------ */

    return {
        /** Current active language code ("en" | "zh"). */
        get currentLang() { return currentLang; },

        /** All translation keys (for debugging / inspection). */
        keys: TRANSLATIONS,

        /**
         * Switch the UI to the given language.
         * @param {"en"|"zh"} lang
         */
        apply,

        /**
         * Translate a single key in the current language, optionally
         * replacing {placeholders}.
         * @param {string} key
         * @param {object} [params]  e.g. { completed: 5, total: 10 }
         * @returns {string}
         */
        translate,

        /**
         * Initialise — call once on page load.
         */
        init,
    };
})();
