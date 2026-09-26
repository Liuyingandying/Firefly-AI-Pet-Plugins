# INTERFACE — Firefly 插件接入契约总览

本文件概述 Firefly AI Pet 对外部插件的统一接入契约；各插件更细的能力说明见其目录内
README / docstring，桥接类插件的完整协议见 [`tju_info_retrieval/INTERFACE.md`](tju_info_retrieval/INTERFACE.md)。

## 统一接入契约（Extension API v2）

| 环节 | 契约 |
|---|---|
| 插件发现 | 宿主启动时扫描插件根目录（Plugin Root）；目录为 Python 包（含 `__init__.py`）且 `plugin.py` 暴露 `create_plugin(parent=None)` 工厂即视为插件 |
| 生命周期 | `initialize(context)` → `start()` → `open()`（Quick Tools 激活）→ `stop()` → `shutdown()` |
| 能力声明 | `QuickToolManifest` 内嵌于插件（id / name / description / capabilities / version / min_api），无需额外 plugin.json |
| 门控 | 逐插件持久化 Enable 开关 + 宿主禁用名单；插件调用前经能力门控检查 |
| Fail-closed | 包结构不符、工厂缺失、返回类型不符或命中禁用名单即拒绝加载，异常隔离在插件边界内 |
| 状态发布 | 插件经状态总线发布 READY / WORKING / OFFLINE / ERROR，Quick Tools 面板据此渲染入口与状态 |

Plugin Root 默认位于 Firefly 用户数据目录的 `plugins` 子目录，可用环境变量
`FIREFLY_PLUGIN_ROOT` 或 `config/path_config.yaml` 的 `paths.plugin_root` 重定向。

## 五插件能力入口一览

| 插件 | 主要入口 | 详细契约 |
|---|---|---|
| firefly_video_extension | `open()`：选择本地视频，输出时长 / 场景 / 关键帧 / 字幕摘要（复用宿主视频管线） | 源码模块 docstring |
| firefly_camera_vision | `status()` / `start()` / `stop()`：设备可用性声明与能力暴露（永不后台开启摄像头） | 源码模块 docstring |
| learning_focus | `open()`、`enter_learning(goal)`、`submit_answer(node_id, answer, expected)`、`review_due_items()` | [`learning_focus/README.md`](learning_focus/README.md) |
| tju_info_retrieval | `search(query, top_k)`、`open_login()`、`open_ui()`、`status()` | [`tju_info_retrieval/INTERFACE.md`](tju_info_retrieval/INTERFACE.md) |
| firefly_voice | `status()`、`health_check()`、`enable()`、`disable()`、`set_auto_play()`、`test_play()`、`start_service()`、`stop_service()`、`restart_service()` | 见下文 Voice Capability 与 [`firefly_voice/README.md`](firefly_voice/README.md) |

## Voice Capability（firefly_voice）

语音能力插件：把 TTS + RVC 语音链路（宿主侧 `voice_client` → 外部 `voice_module` 服务
→ edge-TTS → RVC → sounddevice 播放）纳入插件生态的**状态管理层**。

```python
class VoicePlugin:            # 实现于 firefly_voice/plugin.py（FireflyExtension 基类）
    def status(self) -> str          # 卡片状态位: "ONLINE" / "OFFLINE"（TCP 探测 127.0.0.1:8300）
    def health_check(self) -> dict   # 完整健康: online/latency/enabled/auto_play/config source
    def enable(self) -> dict         # 打开语音能力（写用户插件配置, 免重启即时生效）
    def disable(self) -> dict        # 关闭语音能力（关闭后零 HTTP 调用）
    def set_auto_play(self, value: bool) -> dict   # 自动朗读开关（默认 False, v1.3: 仅播放按钮）
    def test_play(self, text: str = "…") -> dict   # 显式试听（经宿主 voice_client.speak）
```

**职责边界**：插件只负责**能力管理**（开关 / 状态 / 服务显式生命周期 / 配置落盘）。
**不负责**：聊天逻辑、LLM 调用、Agent 决策、语音合成与播放实现（链路全部属宿主与外部服务）。

### Voice Module（服务端本体）

真实 TTS + RVC 服务端源码位于本仓库
[`firefly_voice/voice_module/`](firefly_voice/voice_module/README.md)
（edge-tts → RVC → sounddevice，完整源码 + vendor 引擎快照；模型权重因许可证外置）。

| 约定 | 内容 |
|---|---|
| 进程形态 | **HTTP external local service**：独立于宿主的本地进程（FastAPI + uvicorn） |
| API 边界 | **127.0.0.1:8300**（仅本机回环）：`GET /health`、`POST /voice/speak`、`POST /voice/queue/stop`、`GET /voice/queue` |
| 解耦原则 | 插件/服务端**不 import 宿主 `app.py`**，宿主也不 import 服务端——两侧只经 HTTP + 用户配置解耦；`voice_client`（宿主）与 `voice_module`（服务端）是唯一对接面 |
| 源码唯一性 | 服务端源码只在本仓库这一份；宿主仓库不再内嵌第二份，避免漂移 |

| 约定 | 内容 |
|---|---|
| 配置落点 | `%LOCALAPPDATA%/FireflyAI/plugins/firefly_voice/config.yaml`（优先级：环境变量 > 用户插件配置 > 旧 `voice_config.yaml` > 默认值） |
| 服务生命周期 | **绝不自动启动**；仅经用户显式动作启停；宿主退出不代管服务进程 |
| 降级 | 服务离线时宿主与聊天零影响（`voice_client` 永不抛异常）；插件显示 OFFLINE |
| 隐私 | 无用户数据采集；文本只发本机回环端口；不含模型权重/音频/密钥/本机路径 |

## 桥接类插件

`tju_info_retrieval` 为薄适配器：Firefly 侧零检索逻辑，每个请求通过一次性隔离子进程
调用外部工程的 Bridge CLI，以 JSON 协议返回并归一化。其完整桥接协议、状态机与环境
变量契约见 [`tju_info_retrieval/INTERFACE.md`](tju_info_retrieval/INTERFACE.md)。
