<p align="center">
  <h1 align="center">🎙️ VoicePilot-CLI</h1>
  <p align="center">
    <strong>Lightweight Local Voice AI Agent CLI Engine</strong><br>
    轻量级本地语音AI智能体CLI引擎
  </p>
  <p align="center">
    <a href="#-简体中文">简体中文</a> ·
    <a href="#-繁體中文">繁體中文</a> ·
    <a href="#-english">English</a>
  </p>
  <p align="center">
    <img src="https://img.shields.io/badge/Python-3.8+-blue.svg" alt="Python">
    <img src="https://img.shields.io/badge/License-MIT-green.svg" alt="License">
    <img src="https://img.shields.io/badge/Zero_Dependencies-Core-ff69b4.svg" alt="Zero Deps">
    <img src="https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg" alt="Platform">
  </p>
</p>

---

## 🇨🇳 简体中文

### 🎉 项目介绍

**VoicePilot-CLI** 是一款轻量级的本地语音AI智能体CLI引擎，让你通过语音或文字与AI进行自然交互。灵感来源于当前热门的本地AI智能体趋势（如AgenticSeek），但以更轻量、更灵活的方式实现。

**核心价值**：
- 🔒 **完全本地运行**，数据不出本机，隐私零泄露
- 🪶 **零核心依赖**，仅Python标准库即可运行核心功能
- 🔌 **多后端支持**，STT/TTS/LLM均可自由切换
- 🧩 **插件化架构**，轻松扩展AI能力边界

**差异化亮点**：
- 相比AgenticSeek（Rust实现），VoicePilot-CLI使用Python，生态更丰富、开发门槛更低
- 相比其他语音助手，内置智能体框架，支持任务规划与工具调用
- 优雅的降级策略：无语音后端时自动切换为纯文本模式

### ✨ 核心特性

| 特性 | 描述 |
|------|------|
| 🎤 **多后端STT** | 支持 Whisper、PocketSphinx、系统原生语音识别 |
| 🔊 **多后端TTS** | 支持 pyttsx3、edge-tts、系统原生语音合成 |
| 🤖 **多LLM支持** | 支持 OpenAI、Ollama（本地）、GLM（智谱AI） |
| 🧠 **智能体核心** | 任务规划、上下文管理、流式响应 |
| 🧩 **插件系统** | 热加载插件，内置计算器/天气/文件操作/定时器 |
| 🖥️ **TUI仪表盘** | Rich驱动的终端交互界面，5套配色主题 |
| 🎙️ **VAD检测** | 基于能量的语音活动检测，智能断句 |
| 💾 **对话记忆** | 持久化存储，Token预算裁剪，语义搜索 |
| 📦 **零依赖核心** | 核心功能仅依赖Python标准库 |
| 🌍 **跨平台** | Windows、macOS、Linux全平台支持 |

### 🚀 快速开始

**环境要求**：
- Python 3.8+
- （可选）麦克风和扬声器（语音模式）

**安装**：

```bash
# 克隆仓库
git clone https://github.com/gitstq/VoicePilot-CLI.git
cd VoicePilot-CLI

# 安装（核心功能无需额外依赖）
pip install -e .

# 安装可选依赖（按需选择）
pip install openai          # OpenAI后端
pip install ollama          # Ollama本地模型
pip install zhipuai         # GLM智谱AI
pip install pyttsx3         # 本地TTS
pip install edge-tts        # 微软Edge TTS
pip install openai-whisper  # Whisper语音识别
pip install rich            # TUI仪表盘
```

**快速运行**：

```bash
# 文本模式对话（零依赖即可运行）
voicepilot chat --mode text

# 语音模式对话（需要TTS/STT后端）
voicepilot chat --mode voice

# 使用Ollama本地模型
voicepilot chat --backend ollama --model llama3

# 查看所有插件
voicepilot plugin list

# 查看配置
voicepilot config show
```

### 📖 详细使用指南

#### 交互模式

```bash
# 文本模式 - 纯文字交互，无需任何额外依赖
voicepilot chat --mode text

# 语音模式 - 语音输入+语音输出
voicepilot chat --mode voice

# 自定义系统提示词
voicepilot chat --system-prompt "你是一个专业的编程助手"

# 禁用TUI，使用纯文本输出
voicepilot chat --no-tui

# 开启调试日志
voicepilot chat --debug
```

#### LLM后端配置

编辑 `~/.voicepilot/config.json`：

```json
{
  "llm": {
    "backend": "openai",
    "model": "gpt-4",
    "openai": {
      "api_key": "your-api-key",
      "base_url": "https://api.openai.com/v1"
    },
    "ollama": {
      "base_url": "http://localhost:11434",
      "model": "llama3"
    },
    "glm": {
      "api_key": "your-api-key",
      "model": "glm-4"
    }
  }
}
```

#### 插件使用

```bash
# 查看已安装插件
voicepilot plugin list

# 内置插件示例对话：
# "帮我计算 (3+5)*2"        → 计算器插件
# "北京今天天气怎么样"       → 天气插件
# "读取 ~/notes.txt"        → 文件操作插件
# "5分钟后提醒我开会"        → 定时器插件
```

#### TUI主题切换

```bash
# 在config.json中设置
{
  "tui": {
    "theme": "dracula"  # dark, light, monokai, dracula, solarized_dark
  }
}
```

### 💡 设计思路与迭代规划

**设计理念**：
- **隐私优先**：所有处理在本地完成，不依赖云服务
- **渐进增强**：核心零依赖，按需安装后端能力
- **插件驱动**：通过插件扩展功能，保持核心精简

**技术选型**：
- Python标准库为核心，确保最大兼容性
- Rich库为可选TUI，提供美观的终端界面
- JSON配置文件，简单直观

**后续规划**：
- [ ] MCP协议支持
- [ ] 更多内置插件（代码执行、网页搜索等）
- [ ] 多语言STT/TTS优化
- [ ] 语音唤醒词支持
- [ ] Docker部署支持

### 📦 打包与部署

```bash
# 使用pip安装
pip install .

# 从源码运行
python -m voicepilot_cli chat

# 使用Makefile
make install    # 安装
make test       # 运行测试
make clean      # 清理
```

### 🤝 贡献指南

欢迎贡献代码！请遵循以下步骤：

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'feat: add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 发起 Pull Request

提交规范遵循 Angular Convention：
- `feat:` 新增功能
- `fix:` 修复问题
- `docs:` 文档更新
- `refactor:` 代码重构
- `test:` 测试相关
- `chore:` 构建/工具相关

### 📄 开源协议

本项目基于 [MIT License](LICENSE) 开源。

---

## 🇹🇼 繁體中文

### 🎉 專案介紹

**VoicePilot-CLI** 是一款輕量級的本地語音AI智能體CLI引擎，讓你透過語音或文字與AI進行自然互動。靈感來源於當前熱門的本地AI智能體趨勢，但以更輕量、更靈活的方式實現。

**核心價值**：
- 🔒 **完全本地運行**，資料不出本機，隱私零洩露
- 🪶 **零核心依賴**，僅Python標準庫即可運行核心功能
- 🔌 **多後端支援**，STT/TTS/LLM均可自由切換
- 🧩 **插件化架構**，輕鬆擴展AI能力邊界

**差異化亮點**：
- 相比AgenticSeek（Rust實現），VoicePilot-CLI使用Python，生態更豐富、開發門檻更低
- 相比其他語音助手，內建智能體框架，支援任務規劃與工具調用
- 優雅的降級策略：無語音後端時自動切換為純文字模式

### ✨ 核心特性

| 特性 | 描述 |
|------|------|
| 🎤 **多後端STT** | 支援 Whisper、PocketSphinx、系統原生語音辨識 |
| 🔊 **多後端TTS** | 支援 pyttsx3、edge-tts、系統原生語音合成 |
| 🤖 **多LLM支援** | 支援 OpenAI、Ollama（本地）、GLM（智譜AI） |
| 🧠 **智能體核心** | 任務規劃、上下文管理、串流回應 |
| 🧩 **插件系統** | 熱加載插件，內建計算器/天氣/檔案操作/定時器 |
| 🖥️ **TUI儀表盤** | Rich驅動的終端互動介面，5套配色主題 |
| 🎙️ **VAD檢測** | 基於能量的語音活動檢測，智慧斷句 |
| 💾 **對話記憶** | 持久化儲存，Token預算裁剪，語義搜尋 |
| 📦 **零依賴核心** | 核心功能僅依賴Python標準庫 |
| 🌍 **跨平台** | Windows、macOS、Linux全平台支援 |

### 🚀 快速開始

**環境要求**：
- Python 3.8+
- （可選）麥克風和揚聲器（語音模式）

**安裝**：

```bash
# 克隆倉庫
git clone https://github.com/gitstq/VoicePilot-CLI.git
cd VoicePilot-CLI

# 安裝（核心功能無需額外依賴）
pip install -e .

# 安裝可選依賴（按需選擇）
pip install openai          # OpenAI後端
pip install ollama          # Ollama本地模型
pip install zhipuai         # GLM智譜AI
pip install pyttsx3         # 本地TTS
pip install edge-tts        # 微軟Edge TTS
pip install openai-whisper  # Whisper語音辨識
pip install rich            # TUI儀表盤
```

**快速運行**：

```bash
# 文字模式對話（零依賴即可運行）
voicepilot chat --mode text

# 語音模式對話（需要TTS/STT後端）
voicepilot chat --mode voice

# 使用Ollama本地模型
voicepilot chat --backend ollama --model llama3

# 查看所有插件
voicepilot plugin list

# 查看配置
voicepilot config show
```

### 📖 詳細使用指南

#### 互動模式

```bash
# 文字模式 - 純文字互動，無需任何額外依賴
voicepilot chat --mode text

# 語音模式 - 語音輸入+語音輸出
voicepilot chat --mode voice

# 自訂系統提示詞
voicepilot chat --system-prompt "你是一個專業的程式設計助手"

# 停用TUI，使用純文字輸出
voicepilot chat --no-tui

# 開啟除錯日誌
voicepilot chat --debug
```

#### LLM後端配置

編輯 `~/.voicepilot/config.json`：

```json
{
  "llm": {
    "backend": "openai",
    "model": "gpt-4",
    "openai": {
      "api_key": "your-api-key",
      "base_url": "https://api.openai.com/v1"
    },
    "ollama": {
      "base_url": "http://localhost:11434",
      "model": "llama3"
    },
    "glm": {
      "api_key": "your-api-key",
      "model": "glm-4"
    }
  }
}
```

#### 插件使用

```bash
# 查看已安裝插件
voicepilot plugin list

# 內建插件範例對話：
# "幫我計算 (3+5)*2"        → 計算器插件
# "北京今天天氣怎麼樣"       → 天氣插件
# "讀取 ~/notes.txt"        → 檔案操作插件
# "5分鐘後提醒我開會"        → 定時器插件
```

### 💡 設計思路與迭代規劃

**設計理念**：
- **隱私優先**：所有處理在本地完成，不依賴雲端服務
- **漸進增強**：核心零依賴，按需安裝後端能力
- **插件驅動**：透過插件擴展功能，保持核心精簡

**後續規劃**：
- [ ] MCP協議支援
- [ ] 更多內建插件（程式碼執行、網頁搜尋等）
- [ ] 多語言STT/TTS優化
- [ ] 語音喚醒詞支援
- [ ] Docker部署支援

### 📦 打包與部署

```bash
# 使用pip安裝
pip install .

# 從原始碼運行
python -m voicepilot_cli chat

# 使用Makefile
make install    # 安裝
make test       # 執行測試
make clean      # 清理
```

### 🤝 貢獻指南

歡迎貢獻程式碼！請遵循以下步驟：

1. Fork 本倉庫
2. 建立特性分支 (`git checkout -b feature/amazing-feature`)
3. 提交變更 (`git commit -m 'feat: add amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 發起 Pull Request

### 📄 開源協議

本專案基於 [MIT License](LICENSE) 開源。

---

## 🇬🇧 English

### 🎉 Introduction

**VoicePilot-CLI** is a lightweight local voice AI agent CLI engine that enables natural interaction with AI through voice or text. Inspired by the trending local AI agent movement (like AgenticSeek), it delivers a more lightweight and flexible implementation.

**Core Value**:
- 🔒 **Fully Local** — All processing happens on your machine, zero data leakage
- 🪶 **Zero Core Dependencies** — Runs on Python standard library alone
- 🔌 **Multi-Backend** — Freely switch between STT/TTS/LLM providers
- 🧩 **Plugin Architecture** — Easily extend AI capabilities

**Differentiation**:
- Compared to AgenticSeek (Rust), VoicePilot-CLI uses Python for a richer ecosystem and lower barrier to entry
- Built-in agent framework with task planning and tool calling
- Graceful degradation: automatically falls back to text-only mode when voice backends are unavailable

### ✨ Key Features

| Feature | Description |
|---------|-------------|
| 🎤 **Multi-Backend STT** | Whisper, PocketSphinx, system-native speech recognition |
| 🔊 **Multi-Backend TTS** | pyttsx3, edge-tts, system-native speech synthesis |
| 🤖 **Multi-LLM Support** | OpenAI, Ollama (local), GLM (ZhipuAI) |
| 🧠 **Agent Core** | Task planning, context management, streaming responses |
| 🧩 **Plugin System** | Hot-loading plugins, 4 built-in plugins included |
| 🖥️ **TUI Dashboard** | Rich-powered terminal UI with 5 color themes |
| 🎙️ **VAD Detection** | Energy-based voice activity detection |
| 💾 **Conversation Memory** | Persistent storage with token budget trimming |
| 📦 **Zero Deps Core** | Core runs on Python stdlib only |
| 🌍 **Cross-Platform** | Windows, macOS, Linux |

### 🚀 Quick Start

**Requirements**:
- Python 3.8+
- (Optional) Microphone and speakers for voice mode

**Installation**:

```bash
# Clone the repository
git clone https://github.com/gitstq/VoicePilot-CLI.git
cd VoicePilot-CLI

# Install (no extra dependencies needed for core)
pip install -e .

# Install optional dependencies (as needed)
pip install openai          # OpenAI backend
pip install ollama          # Ollama local models
pip install zhipuai         # GLM ZhipuAI
pip install pyttsx3         # Local TTS
pip install edge-tts        # Microsoft Edge TTS
pip install openai-whisper  # Whisper speech recognition
pip install rich            # TUI dashboard
```

**Quick Run**:

```bash
# Text mode chat (zero dependencies required)
voicepilot chat --mode text

# Voice mode chat (requires TTS/STT backends)
voicepilot chat --mode voice

# Use Ollama local model
voicepilot chat --backend ollama --model llama3

# List all plugins
voicepilot plugin list

# Show configuration
voicepilot config show
```

### 📖 Detailed Usage Guide

#### Interaction Modes

```bash
# Text mode - pure text interaction, no extra deps needed
voicepilot chat --mode text

# Voice mode - voice input + voice output
voicepilot chat --mode voice

# Custom system prompt
voicepilot chat --system-prompt "You are a professional coding assistant"

# Disable TUI, use plain text output
voicepilot chat --no-tui

# Enable debug logging
voicepilot chat --debug
```

#### LLM Backend Configuration

Edit `~/.voicepilot/config.json`:

```json
{
  "llm": {
    "backend": "openai",
    "model": "gpt-4",
    "openai": {
      "api_key": "your-api-key",
      "base_url": "https://api.openai.com/v1"
    },
    "ollama": {
      "base_url": "http://localhost:11434",
      "model": "llama3"
    },
    "glm": {
      "api_key": "your-api-key",
      "model": "glm-4"
    }
  }
}
```

#### Plugin Usage

```bash
# List installed plugins
voicepilot plugin list

# Built-in plugin examples:
# "Calculate (3+5)*2"         → Calculator plugin
# "What's the weather today?" → Weather plugin
# "Read ~/notes.txt"          → File operations plugin
# "Remind me in 5 minutes"    → Timer plugin
```

### 💡 Design Philosophy & Roadmap

**Design Principles**:
- **Privacy First** — All processing is local, no cloud dependency
- **Progressive Enhancement** — Zero deps core, add backends as needed
- **Plugin-Driven** — Extend through plugins, keep core lean

**Roadmap**:
- [ ] MCP protocol support
- [ ] More built-in plugins (code execution, web search, etc.)
- [ ] Multi-language STT/TTS optimization
- [ ] Wake word detection
- [ ] Docker deployment support

### 📦 Packaging & Deployment

```bash
# Install via pip
pip install .

# Run from source
python -m voicepilot_cli chat

# Use Makefile
make install    # Install
make test       # Run tests
make clean      # Clean up
```

### 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork this repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

Commit convention follows Angular Convention:
- `feat:` New feature
- `fix:` Bug fix
- `docs:` Documentation
- `refactor:` Code refactoring
- `test:` Testing
- `chore:` Build/tooling

### 📄 License

This project is licensed under the [MIT License](LICENSE).

---

<p align="center">
  Made with ❤️ by <a href="https://github.com/gitstq">gitstq</a>
</p>
