# Screenshot to Format Converter (Img2Text)

将图片中的文字通过视觉 AI 模型转换为指定格式的文本文件。

## Features

- **7 种输出格式**：Markdown、HTML、CSV、JSON、LaTeX、纯文本、代码
- **3 种内容语言**：中文 (cn)、英文 (en)、法文 (fr)
- **自定义模型**：支持任意兼容 OpenAI API 的视觉模型（GPT-4o、Claude、Qwen-VL 等）
- **全局热键**：自定义快捷键，一键从剪贴板截图并转换
- **浏览器剪贴板捕获**：点击按钮从系统剪贴板获取截图，自动填入路径
- **拖拽上传**：浏览器拖拽上传图片，自动填入路径
- **批量并发处理**：最多 50 张图片并行调用 API，大幅缩短等待时间
- **任务进度追踪**：实时进度条，支持多图片批量处理
- **单文件 + 合并输出**：每张图片生成独立文件，同时输出 `all_in_one.{ext}` 合并文件
- **已处理图片归档**：处理完成的图片自动移入 `_processed_` 子目录，避免重复处理
- **暗色主题 UI**：现代化暗色界面，中英文切换
- **剪贴板集成**：转换结果可选自动复制到剪贴板
- **自动端口检测**：端口被占用时自动递增，无需手动配置

## Quick Start

### 环境要求

- Python 3.10+
- pip（使用 `python -m pip` 而非 `pip`，避免系统多版本冲突）

### 安装

```bash
git clone <repo-url>
cd <repo-dir>               # 进入仓库根目录（目录名取决于 clone 方式）

# 安装依赖（注意：使用 python -m pip）
python -m pip install -r Screenshot_To_All_Formats/requirements.txt
```

### 启动

```bash
# 方式一：Python 模块运行（推荐）
python -m Screenshot_To_All_Formats.main

# 方式二：uvicorn
python -m uvicorn Screenshot_To_All_Formats.main:app --reload --host 127.0.0.1 --port 8000

# 方式三：启动脚本
#   Windows: 双击 start.bat（位于 Screenshot_To_All_Formats/ 目录内）
#   Linux/Mac: ./Screenshot_To_All_Formats/start.sh
```

启动后自动打开浏览器；若未自动打开，访问：
- **前端界面**：http://127.0.0.1:8000/static/index.html
- **API 文档**：http://127.0.0.1:8000/docs

> 如果 8000 端口被占用，服务会自动递增寻找可用端口，并在控制台打印实际地址。

### 首次使用

1. 打开 http://127.0.0.1:8000/static/index.html
2. 点击导航栏 **Settings** → 填写 **API Base URL**、**API Key**、**Model Name**
3. 点击 **Save Settings**
4. 返回首页，填写图片文件夹路径和输出路径（也可通过拖拽上传或「Capture Clipboard」自动填入）
5. 选择语言和格式，点击 **Start Conversion**

## Project Structure

```
Screenshot_To_All_Formats/
├── main.py                          # FastAPI 应用入口（生命周期 + 路由挂载）
├── PROMPTS_LIB.py                   # 提示词管理器（7 格式 × 3 语言 = 21 条）
├── prompt_setting.py                # 提示词注册（模块加载时自动执行）
├── core_backend_call_api.py         # OCR 核心函数（OpenAI API 调用）
├── config.json                      # [运行时生成] 用户设置（已 gitignore）
├── requirements.txt                 # Python 依赖清单
├── .gitignore
├── .gitattributes                   # 文本文件 LF 标准化
├── start.bat                        # Windows 一键启动脚本
├── start.sh                         # Linux/Mac 一键启动脚本
├── LICENSE                          # MIT 开源许可
│
├── api/                             # FastAPI 路由层
│   ├── router.py                    #   路由聚合
│   ├── conversion.py                #   转换任务 CRUD + 后台 OCR 工作线程
│   ├── settings.py                  #   设置读写 + 语言/格式列表查询
│   ├── upload.py                    #   多文件上传（时间戳子目录）
│   └── utils.py                     #   枚举 + Pydantic 模型 + 依赖注入
│
├── services/                        # 业务逻辑层
│   ├── ocr_engine.py                #   OCR 引擎（ThreadPool + as_completed）
│   ├── task_manager.py              #   线程安全内存任务存储
│   └── settings_manager.py          #   config.json 持久化 + 校验
│
├── hotkey/                          # 全局热键模块
│   └── listener.py                  #   pynput 键盘监听（自定义组合键）
│
├── static/                          # 前端 SPA
│   ├── index.html                   #   主页面（SPA + 哈希路由）
│   ├── css/style.css                #   暗色主题样式（响应式）
│   └── js/
│       ├── api.js                   #   API 客户端（fetch 封装）
│       ├── app.js                   #   应用逻辑（路由、转换、快捷键录制）
│       └── i18n.js                  #   中英文翻译
│
├── docs/api.md                      # 完整 API 参考文档（中文）
├── tests/                           # 测试套件
│   └── test_smoke.py                #   综合冒烟测试（覆盖设置、任务生命周期、上传）
├── uploads/                         # 上传图片存储目录
└── outputs/                         # 默认输出目录
```

## Configuration

设置保存在项目根目录的 `config.json` 中（自动生成）：

```json
{
  "defaults": {
    "input_path": "",
    "output_path": "",
    "language": "en"
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

### 支持的模型服务商

设置 `base_url` 和 `api_key` 即可接入任意兼容 OpenAI API 的服务：

| 服务商 | Base URL | 推荐模型 |
|--------|----------|----------|
| OpenAI | `https://api.openai.com/v1` | `gpt-4o`, `gpt-4o-mini` |
| Anthropic | `https://api.anthropic.com/v1` | `claude-sonnet-4-6`, `claude-3-5-sonnet` |
| 阿里通义千问 | `https://dashscope.aliyuncs.com/compatible-mode/v1` | `qwen-vl-max` |
| 百度千帆 | 需兼容代理 | `ERNIE-Bot` |
| 本地模型 (vLLM) | `http://localhost:8000/v1` | `llava` 等 |

## API Endpoints

完整 API 文档见 [docs/api.md](docs/api.md)，快速索引：

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/settings` | 获取所有设置 |
| PUT | `/api/settings` | 更新设置 |
| GET | `/api/languages` | 内容语言列表 |
| GET | `/api/ui-languages` | UI 语言列表 |
| GET | `/api/formats` | 输出格式列表 |
| POST | `/api/convert` | 启动转换任务 |
| GET | `/api/tasks/{id}` | 查询任务状态 |
| GET | `/api/tasks` | 最近任务列表 |
| DELETE | `/api/tasks/{id}` | 删除任务 |
| GET | `/api/tasks/{id}/download` | 下载合并结果 |
| POST | `/api/upload` | 上传图片 |
| POST | `/api/clipboard/capture` | 从系统剪贴板捕获图片并保存 |
| GET | `/api/hotkey/status` | 查询全局热键监听器状态 |
| GET | `/api/hotkey/events` | 获取最近热键触发事件日志 |

## Frontend Usage

### 热键设置

1. 进入 **Settings → Hotkey Settings**
2. 勾选 **Enable Global Hotkey**
3. 点击 **Record** 按钮
4. 在键盘上按下想要的组合键（如 `Ctrl+Shift+V`）
5. 松开按键自动完成录制
6. 点击 **Save Settings**

热键触发时：截取剪贴板图片 → 保存到输入路径 → 自动开始转换。

### 拖拽上传

1. 在主页面点击 **Upload & Convert** 展开上传区域
2. 拖拽图片到虚线区域，或点击选择文件
3. 上传完成后输入路径自动填充
4. 点击 **Start Conversion** 开始

支持的图片格式：`png`、`jpg`、`jpeg`、`webp`、`bmp`、`gif`。

## Development Notes

### Python 版本注意事项

如果系统同时安装了多个 Python 版本，务必使用 `python -m pip` 而不是 `pip`：

```bash
# ✅ 正确
python -m pip install -r Screenshot_To_All_Formats/requirements.txt

# ❌ 可能装错 Python 版本
pip install -r Screenshot_To_All_Formats/requirements.txt
```

### 提示词系统

`PROMPTS_LIB.py` 管理 21 条提示词（7 格式 × 3 语言），`prompt_setting.py` 在导入时将提示词注册到 `prompts_library.promptLibraryMap` 中。

**必须确保 `prompt_setting` 在 OCR 调用前被导入**——`main.py` 通过 `import Screenshot_To_All_Formats.prompt_setting as prompt_setting` 在应用启动时完成注册。

### 任务存储

任务存储在内存中（`services/task_manager.py`），**重启后丢失**。输出文件已持久化到磁盘，不受影响。

### 前端架构

纯原生 HTML/CSS/JS，零框架依赖。使用哈希路由（`#main` / `#settings`）切换视图，`data-i18n` 属性模式实现中英文切换。

## Tests

```bash
# 安装测试依赖
python -m pip install httpx pytest

# 启动服务后，在另一个终端运行测试
python -m pytest Screenshot_To_All_Formats/tests/test_smoke.py -v
```

测试脚本也支持自动启动服务器模式，详情见 `tests/test_smoke.py`。

## License

[MIT](LICENSE)
