# API 文档 — Screenshot to Format Converter

## 基础信息

- **Base URL**: `/api`
- **Content-Type**: `application/json`（上传除外）
- **认证**: 无内置认证（API Key 放在请求 body 中传给下游模型服务）

---

## 一、设置管理 (Settings)

### GET /api/settings

获取所有当前设置（包含默认值）。

**Response 200**:
```json
{
  "defaults": {
    "input_path": "",
    "output_path": ""
  },
  "model": {
    "base_url": "https://api.openai.com/v1",
    "api_key": "",
    "model_name": "gpt-4o",
    "max_tokens": 30000
  },
  "ui": {
    "language": "en",
    "format": "markdown",
    "copy_to_clipboard": true
  },
  "hotkey": {
    "enabled": false,
    "combo": "ctrl+shift+v",
    "auto_start": true
  }
}
```

---

### PUT /api/settings

更新并持久化设置。只发送需要修改的字段即可，未提供的字段保持原值。

**Request** (partial update):
```json
{
  "model": {
    "api_key": "sk-xxx",
    "base_url": "https://api.openai.com/v1",
    "model_name": "gpt-4o",
    "max_tokens": 30000
  }
}
```

**Response 200**: 完整的设置对象（同 GET）。

---

### GET /api/languages

获取 OCR 支持的内容语言列表。

**Response 200**:
```json
["cn", "en", "fr"]
```

---

### GET /api/ui-languages

获取界面支持的 UI 语言列表。

**Response 200**:
```json
["en", "zh"]
```

---

### GET /api/formats

获取支持的输出格式列表。

**Response 200**:
```json
["markdown", "html", "csv", "json", "latex", "text", "code"]
```

---

## 二、转换任务 (Conversion)

### POST /api/convert

创建并启动一个新的图片转换任务。后端会将任务交给后台线程异步执行。

**Request**:
```json
{
  "input_path": "C:/images/screenshots",
  "output_path": "C:/images/output",
  "language": "en",
  "format": "markdown",
  "copy_to_clipboard": false,
  "model": {
    "api_key": "sk-xxx",
    "base_url": "https://api.openai.com/v1",
    "model_name": "gpt-4o",
    "max_tokens": 30000
  }
}
```

**字段说明**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `input_path` | string | 是 | 图片所在文件夹路径 |
| `output_path` | string | 是 | 结果输出文件夹路径 |
| `language` | string | 否 | `cn` / `en` / `fr`，默认 `en` |
| `format` | string | 否 | `markdown` / `html` / `csv` / `json` / `latex` / `text` / `code`，默认 `markdown` |
| `copy_to_clipboard` | bool | 否 | 完成后将最后结果复制到剪贴板，默认 `false` |
| `model` | object | 是 | 模型配置（见下表） |

**model 字段**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `api_key` | string | 是 | API 密钥 |
| `base_url` | string | 是 | API 地址（兼容 OpenAI 格式） |
| `model_name` | string | 是 | 模型名称（如 gpt-4o, claude-3-opus 等） |
| `max_tokens` | int | 否 | 最大 Token 数，范围 1024~200000，默认 30000 |

**Response 201**:
```json
{
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "total_images": 5
}
```

**Error 400**:
```json
{
  "detail": "Input path not found: C:/invalid/path"
}
```
```json
{
  "detail": "No supported image files found in input directory"
}
```

---

### GET /api/tasks/{task_id}

获取单个任务的当前状态。

**Response 200**:
```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "running",
  "progress": 3,
  "total": 5,
  "percentage": 60,
  "results": [],
  "combined_result": "",
  "error": null,
  "input_path": "C:/images/screenshots",
  "output_path": "C:/images/output",
  "language": "en",
  "format": "markdown",
  "created_at": 1713912345.678,
  "completed_at": null,
  "elapsed": 0
}
```

**status 取值**:
| 值 | 含义 |
|---|---|
| `pending` | 排队等待中 |
| `running` | 正在处理 |
| `completed` | 已完成 |
| `error` | 出错 |

**制作完成后的 response**:
```json
{
  "id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "completed",
  "progress": 5,
  "total": 5,
  "percentage": 100,
  "results": [
    "## Screenshot 1\n\nContent of image 1...",
    "## Screenshot 2\n\nContent of image 2..."
  ],
  "combined_result": "## Screenshot 1\n\nContent of image 1...\n\n## Screenshot 2\n\nContent of image 2...",
  "error": null,
  "completed_at": 1713912390.123,
  "elapsed": 44.445
}
```

**Error 404**:
```json
{
  "detail": "Task not found"
}
```

---

### GET /api/tasks

获取最近的任务列表（按创建时间倒序）。

**Query Parameters**:

| 参数 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `limit` | int | 否 | 50 | 返回的最大任务数 |

**Response 200**:
```json
[
  {
    "id": "a1b2c3d4-...",
    "status": "completed",
    "progress": 5,
    "total": 5,
    "percentage": 100,
    "results": ["..."],
    "combined_result": "...",
    "error": null,
    "input_path": "...",
    "output_path": "...",
    "language": "en",
    "format": "markdown",
    "created_at": 1713912345.678,
    "completed_at": 1713912390.123,
    "elapsed": 44.445
  }
]
```

---

### DELETE /api/tasks/{task_id}

删除一个任务（仅从内存中移除，不影响已输出的文件）。

**Response 200**:
```json
{
  "deleted": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
}
```

**Error 404**:
```json
{
  "detail": "Task not found"
}
```

---

### GET /api/tasks/{task_id}/download

下载已完成任务的合并输出文件（`all_in_one.{ext}`）。

**行为**: 返回文件流供浏览器下载。

**Response 200**: 二进制文件流（Content-Type 根据格式自动设置）。

**Error 400**:
```json
{
  "detail": "Task is not yet completed"
}
```

**Error 404**:
```json
{
  "detail": "Output file not found on disk"
}
```

**文件扩展名映射**:

| Format | Extension |
|--------|-----------|
| markdown | `.md` |
| html | `.html` |
| csv | `.csv` |
| json | `.json` |
| latex | `.tex` |
| text | `.txt` |
| code | `.txt` |

---

## 三、文件上传 (Upload)

### POST /api/upload

上传一个或多个图片文件。文件会保存到自动创建的时间戳子目录下。

**Request**: `multipart/form-data`

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `files` | File[] | 是 | 一个或多个图片文件 |

**Response 200**:
```json
{
  "uploaded": ["screenshot1.png", "screenshot2.png"],
  "upload_dir": "C:/project/uploads/20250424_153022"
}
```

`upload_dir` 可以直接作为后续 `/api/convert` 的 `input_path` 使用。

---

## 四、前端 API 客户端

前端 `static/js/api.js` 已封装上述所有端点，通过全局 `api` 对象调用：

### 方法速查

```js
// 设置
const settings       = await api.getSettings();
const saved          = await api.saveSettings({ model: { api_key: "..." } });
const langs          = await api.getLanguages();       // ["cn","en","fr"]
const uiLangs        = await api.getUiLanguages();     // ["en","zh"]
const formats        = await api.getFormats();

// 转换
const { task_id }    = await api.startConversion({ input_path, output_path, ... });
const status         = await api.getTaskStatus(task_id);
const tasks          = await api.getTasks(20);
const { deleted }    = await api.deleteTask(task_id);
await api.downloadResult(task_id);                     // 触发浏览器下载
const url            = api.getDownloadUrl(task_id);    // 获取下载链接

// 上传
const { upload_dir } = await api.uploadFiles(fileList);
```

### 错误处理

所有方法在请求失败时会抛出 `Error`，message 为服务端返回的 `detail` 信息：

```js
try {
  const result = await api.startConversion({ ... });
} catch (err) {
  console.error(err.message);  // "Input path not found: ..."
}
```

### 低层方法

```js
const res  = await api.request("/custom-endpoint");
const data = await api.json("/custom-endpoint");
const txt  = await api.text("/custom-endpoint");
const blob = await api.blob("/custom-endpoint");
```

---

## 五、数据模型

### ConversionRequest

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `input_path` | string | 是 | 输入目录 |
| `output_path` | string | 是 | 输出目录 |
| `language` | string | 否 | cn/en/fr，默认 en |
| `format` | string | 否 | 见 formats，默认 markdown |
| `copy_to_clipboard` | bool | 否 | 默认 false |
| `model` | ModelConfig | 是 | 模型配置 |

### ModelConfig

| 字段 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `api_key` | string | 是 | — | 服务商 API 密钥 |
| `base_url` | string | 是 | — | 兼容 OpenAI 的 API 地址 |
| `model_name` | string | 是 | — | 视觉模型名称 |
| `max_tokens` | int | 否 | 30000 | 范围 1024~200000 |

### TaskStatusResponse

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | string | UUID 任务 ID |
| `status` | string | pending / running / completed / error |
| `progress` | int | 已处理的图片数 |
| `total` | int | 总图片数 |
| `percentage` | int | 0~100 |
| `results` | string[] | 每张图片的转换结果列表 |
| `combined_result` | string | 全部结果的合并文本 |
| `error` | string\|null | 错误信息 |
| `input_path` | string | 输入目录 |
| `output_path` | string | 输出目录 |
| `language` | string | 内容语言 |
| `format` | string | 输出格式 |
| `created_at` | float | Unix 时间戳（秒） |
| `completed_at` | float\|null | 完成时间戳 |
| `elapsed` | float | 已耗时（秒） |
