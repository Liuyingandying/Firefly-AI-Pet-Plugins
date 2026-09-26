# Firefly AI Pet — Plugin Extension Package

Firefly AI Pet 的插件扩展包（比赛提交 / 开源展示用）。四个插件全部符合
FireflyExtension v2 契约：Python 包（`__init__.py`）+ `plugin.py::create_plugin(parent=None)`
工厂，由宿主 `core/plugin_loader.py` 在启动时自动发现加载，manifest 内嵌于
`QuickToolManifest`（无需 plugin.json）。

## 包内容

| 目录 | 功能 | 分发形式 | 状态 |
|---|---|---|---|
| `firefly_video_extension/` | 本地视频文件分析：时长 / 场景检测 / 关键帧 / 字幕（调用宿主 VideoProcessor） | 完整源码 | ✅ 可直接使用 |
| `firefly_bili_insight_service/` | **B站 URL / BV号 视频阅读服务**：`metadata` / `transcribe`（本地 faster-whisper ASR）/ `frame` 抽帧，subprocess JSONL，供宿主 `BiliInsightClient` 调用 | 完整源码（GPL-3.0，见下文 License） | 🔧 需按其 README 部署 |
| `firefly_camera_vision/` | 摄像头视觉能力适配器：按需单帧、永不后台开摄像头，设备状态声明卡 | 完整源码 | ✅ 可直接使用 |
| `learning_focus/` | 学习专注：知识图谱规划 × 学习者画像记忆 × 作答证据评估（算法层纯标准库） | 完整源码 + 测试 | ✅ 可直接使用 |
| `tju_info_retrieval/` | 天津大学信息检索**薄适配器**（桥接外部私有工程） | 仅接口契约文档 | 📄 文档分发 |
| `firefly_voice/` | **插件控制层**：TTS+RVC 服务状态/开关/显式启停（Voice Settings 面板） | 完整源码 + 测试 | ✅ 可直接使用 |
| `firefly_voice/voice_module/` | **真实 TTS + RVC 服务端**（`firefly_voice` 插件管理的外部服务进程）：edge-TTS → RVC 声线转换 → 本机播放，FastAPI 127.0.0.1:8300 | 完整源码 + vendor 引擎快照(MIT) + 启动/诊断脚本 + 测试；**模型权重不入库**（License 边界，见其 models/README.md） | 🔧 需按其 README 部署 |

> **语音能力 = 控制层 + 服务端两部分，源码均已包含**。`firefly_voice/` 插件负责状态/开关/启停管理；
> 真正出声的是 [`firefly_voice/voice_module/`](firefly_voice/voice_module/README.md) 服务端——
> 克隆后按其 README 安装依赖并下载模型权重即可（模型因许可证原因外置，源码零缺失）。未部署时聊天链路零影响。
>
> **视频能力同样 = 两部分**：[`firefly_video_extension/`](firefly_video_extension/README.md)
> 管**本地视频文件**（FFmpeg / 场景 / 关键帧 / OCR，随宿主即用）；
> [`firefly_bili_insight_service/`](firefly_bili_insight_service/README.md) 管
> **B站 URL / BV号**（metadata / transcribe / frame）。两条链互不相同。
> B站服务**不需要安装 B站桌面客户端**；**登录 OPTIONAL**——公开视频匿名即可
> `metadata` / `transcribe` / `frame` 全通过（2026-09-26 实测），`transcribe` 是
> **本地 faster-whisper ASR**，不是 B站官方字幕。

## 安装

将插件目录放入 Firefly 的插件根目录即可（默认 `%LOCALAPPDATA%/FireflyAI/plugins`；
可用 `FIREFLY_PLUGIN_ROOT` 环境变量或 `config/path_config.yaml` 的 `paths.plugin_root` 指定）。

### 安装流程（普通用户）

1. **下载插件包**：本仓库页面 → `Releases`（v1.0.0 起，含介绍 PDF）或
   `Code → Download ZIP`；建议使用 tag 归档（如
   `archive/refs/tags/v1.0.0.zip`），与发布状态零偏差。
2. **复制插件目录**：解压后将 `firefly_video_extension/`、`firefly_camera_vision/`、
   `learning_focus/` 三个目录复制到插件根目录
   `%LOCALAPPDATA%\FireflyAI\plugins\`——该目录不存在时宿主会在首次启动时自动创建
   （已在 v1.0-rc2 新用户安装验证中实测）。
3. **重启宿主**：托盘右键退出 Firefly AI Pet 后重新启动，插件在启动时被自动发现加载。
4. **确认加载**：在宠物快捷工具 / 设置面板中查看对应插件入口。
5. **tju_info_retrieval**：为接口契约文档分发，需按 `tju_info_retrieval/INTERFACE.md`
   配合外部工程使用，普通用户可跳过。

> 卸载：删除插件根目录下对应的插件目录并重启宿主即可；宿主对插件故障相互隔离，
> 移除单个插件不影响其余功能。

## 依赖概览

- 宿主模块（由 Firefly 主仓库提供）：`core.extension_api`、`core.quick_tools`、
  `core.video_pipeline`、`core.plugin_api`
- 第三方：PySide6（宿主已含）；`firefly_video_extension` 的视频能力依赖宿主管线的
  FFmpeg / 场景检测 / OCR
- `learning_focus/learner|memory|planner`：纯 Python 标准库，测试可独立运行：
  `python -m unittest discover -s learning_focus/tests`

## 各插件说明

详细功能、架构与设计要点见各插件目录内 README / 文档：

- `firefly_video_extension/README.md`：本地视频分析与 B站 URL 阅读两条链的区别
- `firefly_bili_insight_service/README.md`：B站服务的安装（Python/ffmpeg/上游克隆）、
  Firefly 指向配置、登录态安全边界、冒烟测试
- `firefly_camera_vision/`：见源码模块 docstring
- `learning_focus/README.md`：架构、能力面、数据布局、测试
- `tju_info_retrieval/INTERFACE.md`：桥接协议、状态机、环境变量契约、
  桥接类插件的通用设计经验
- `firefly_voice/README.md`：能力管理接口、配置优先级与迁移、服务启停策略、无 GPU 降级、隐私说明
- `firefly_voice/voice_module/README.md`：语音服务架构、安装、模型部署与 License 边界、
  启动/验证命令、Firefly 宿主对接、内存/CUDA Troubleshooting

## 分发边界说明

- 本包**不含**任何 API 密钥、token、cookie、用户数据或本机绝对路径。
- 本包**不含任何模型权重**：语音服务的说话人模型与基础模型（HuBERT/rmvpe）因授权边界
  由用户按 `firefly_voice/voice_module/models/README.md` 自行下载（含 SHA256 校验值）；
  B站服务的 Whisper 模型首次运行时自动下载（见其 README）。
- `tju_info_retrieval` 的核心检索工程为私有项目，本包仅公开宿主侧适配契约；
  复现该插件需要按 `INTERFACE.md` 实现同构的 bridge CLI。
- TJU 登录态（cookies/storage state）归属外部工程，本包不含、也不读取其内容。

## License

本仓库为 **multi-license repository**：

- 各插件目录（`firefly_video_extension/`、`firefly_camera_vision/`、`learning_focus/`、
  `firefly_voice/` 等）按仓库根 [`LICENSE`](LICENSE)（**MIT**）分发；
- **例外**：[`firefly_bili_insight_service/`](firefly_bili_insight_service/) 为
  **GPL-3.0-or-later**（见该目录内 [`LICENSE`](firefly_bili_insight_service/LICENSE)）。
  该目录及其衍生代码**不受根 MIT LICENSE 覆盖**；它与宿主经 subprocess JSONL 解耦，
  与上游 GPL 依赖保持同谱系；
- 上游依赖与完整第三方许可清单见 [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)。
