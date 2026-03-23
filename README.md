# 企业微信 × Claude Code Bot

基于企业微信智能机器人（长连接模式）与 [claude-agent-sdk](https://github.com/anthropics/claude-agent-sdk-python) 构建的 AI 助手。用户在企业微信中发消息，机器人通过 Claude Code channel 进行多轮对话，并可调用真实工具完成文件操作、命令执行、网络搜索等任务。

## 能力

| 能力 | 说明 |
|------|------|
| 💬 多轮对话 | 每个用户独立会话，上下文跨消息保持 |
| 📡 流式回复 | 打字机效果，Claude 边生成边推送到企业微信 |
| 📁 文件读写 | 读取、创建、编辑服务器上的文件（Read / Write / Edit） |
| ⚡ 命令执行 | 执行 Bash 命令，运行脚本、查询系统状态等（Bash） |
| 🔍 代码搜索 | 按文件名或内容搜索代码库（Glob / Grep） |
| 🌐 网络搜索 | 实时搜索网页、获取页面内容（WebSearch / WebFetch） |
| 🤖 子 Agent | 调用子 Agent 并行处理复杂任务（Agent） |

所有工具能力由 `claude-agent-sdk` 内置的 Claude Code CLI（v2.1.81）提供，**无需额外安装 Claude Code**。

## 架构

```
企业微信
  │  WebSocket 长连接（无需公网 URL / 域名）
  ▼
main.py（wecom-aibot-python-sdk）
  │
  ▼
agent_client.py（claude-agent-sdk）
  │  启动 Claude Code CLI 子进程
  ▼
Claude Code CLI（内置于 SDK）
  ├── Read / Write / Edit（文件操作）
  ├── Bash（命令执行）
  ├── Glob / Grep（代码搜索）
  └── WebSearch / WebFetch（网络搜索）
```

与直接调用 Anthropic API 相比，本项目通过 `claude-agent-sdk` 驱动完整的 Claude Code 工具链，工具执行结果由 Claude 自动消化并生成最终回复。

## 环境依赖

- Python 3.11+
- [claude-agent-sdk](https://pypi.org/project/claude-agent-sdk/) >= 0.1.50（内置 Claude Code CLI，无需单独安装）
- [wecom-aibot-python-sdk](https://pypi.org/project/wecom-aibot-python-sdk/) >= 1.0.2
- **Windows 用户**：需安装 [Git for Windows](https://git-scm.com/)（提供 bash.exe，claude-agent-sdk 依赖）

## 快速开始

### 1. 克隆并安装依赖

```bash
git clone https://github.com/TSorzZZ/wecom_claude_bot.git
cd wecom_claude_bot
pip install -r requirements.txt
```

### 2. 在企业微信后台创建智能机器人

进入企业微信管理后台 → **「智能机器人」→「创建机器人」→「API 配置」→「使用长连接」**，获取：

- `WECOM_BOT_ID`（机器人 ID，格式 `aib-xxx`）
- `WECOM_SECRET`（密钥）

### 3. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`，至少填写以下三项：

```env
ANTHROPIC_API_KEY=sk-ant-xxxxxxxx
WECOM_BOT_ID=aib-xxxxxxxx
WECOM_SECRET=xxxxxxxx
```

Windows 用户还需额外填写（必须）：

```env
CLAUDE_CODE_GIT_BASH_PATH=C:\Program Files\Git\usr\bin\bash.exe
```

### 4. 启动

```bash
python main.py
```

看到 `认证成功，机器人在线 ✅` 即表示连接成功，在企业微信中找到该机器人发送消息即可。

## 配置参数

所有配置通过 `.env` 文件设置，参考 `.env.example`。

### 必填

| 变量 | 说明 |
|------|------|
| `ANTHROPIC_API_KEY` | Anthropic API Key |
| `WECOM_BOT_ID` | 企业微信智能机器人 ID（格式 `aib-xxx`） |
| `WECOM_SECRET` | 企业微信智能机器人密钥 |

### Claude 模型

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `ANTHROPIC_BASE_URL` | （空，使用官方地址） | 自定义 API 代理地址 |
| `CLAUDE_MODEL` | `claude-opus-4-6` | 使用的模型 |
| `CLAUDE_MAX_TOKENS` | `2048` | 单次回复最大 token 数 |
| `SYSTEM_PROMPT` | 见 `.env.example` | 系统提示词，定义机器人角色 |

### Agent 工具

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `AGENT_CWD` | `F:/workspace` | Agent 默认工作目录（文件操作的相对路径基准） |
| `AGENT_ALLOWED_TOOLS` | `Read,Write,Edit,Bash,Glob,Grep,WebSearch,WebFetch` | 允许使用的工具（逗号分隔） |
| `CLAUDE_CODE_GIT_BASH_PATH` | （空） | **Windows 必填**：git-bash 路径，如 `C:\Program Files\Git\usr\bin\bash.exe` |

### 工具权限示例

仅允许只读操作（禁止写文件和执行命令）：

```env
AGENT_ALLOWED_TOOLS=Read,Glob,Grep,WebSearch,WebFetch
```

纯对话模式，不使用任何工具：

```env
AGENT_ALLOWED_TOOLS=
```

## 用户指令

| 指令 | 说明 |
|------|------|
| `/clear` | 清除当前对话记录，开始新会话 |
| `/help` | 显示帮助信息 |

## 项目结构

```
wecom_claude_bot/
├── main.py            # 入口，企业微信 WebSocket 事件处理与流式回复
├── agent_client.py    # claude-agent-sdk 封装，会话管理与流式输出
├── config.py          # 环境变量加载
├── utils.py           # 工具函数（流式消息 ID 生成）
├── requirements.txt
├── .env.example       # 配置模板
└── .gitignore
```

## 注意事项

- **安全**：`AGENT_ALLOWED_TOOLS` 包含 `Bash` 和 `Write` 时，Claude 可在服务器上执行命令和写文件，请在受信任环境中使用，或根据需要缩小工具权限
- **文件访问范围**：`AGENT_CWD` 只是默认工作目录，Claude 使用绝对路径可访问服务器任意位置
- **会话持久化**：会话 ID 存储在内存，重启后丢失，用户需重新开始对话
- **工具执行延迟**：调用工具（如 Bash）时，流式输出会暂停至工具执行完毕，属于正常现象

## License

[MIT](LICENSE)
