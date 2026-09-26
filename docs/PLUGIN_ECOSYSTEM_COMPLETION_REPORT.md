# 插件生态「非 Learning 功能」补齐完成报告（2026-09-26）

> 范围：TJU Info Retrieval / Local Video / Camera Vision / 根文档与安装 / 默认 clone 验收。
> Voice 与 BiliInsight 仅回归保护；learning_focus 全程零改动（WIP / OUT_OF_SCOPE）。
> 判定全部来自本轮真实执行证据——代码存在、单测通过、README 写完都不构成 COMPLETE。

## 仓库基线与终态

| 仓库 | BASE_SHA（本轮起点） | 终态 |
|---|---|---|
| Firefly-AI-Pet（宿主） | main=df18cc4 / plugins-integration=b32916d | **零改动**（555 个 WIP 文件未纳入任何提交） |
| Firefly-AI-Pet-Plugins | main=e46ad90 | main=**2249f46**（PR #3 四笔提交：c0ff1fd TJU / 31dd983 video / de782fd camera / 6ad947d docs） |
| tju-research-assistant | main=c3205bc | main=**add5ec8**（PR #1：.gitignore 保护运行期登录产物） |

## 分能力终态

### TJU Info Retrieval — 源码与工程 COMPLETE；真实检索 = AUTH_REQUIRED

- **补齐内容**：`adapter.py`（薄桥接客户端）+ `plugin.py`（search/open_login/open_ui/status 四态）+ 12 个宿主无关单测 + README + `docs/TJU_BRIDGE_CONTRACT.md`；INTERFACE.md 更新为指向公开核心工程。
- **去机器化**：外部工程根 = `TJU_INFO_RETRIEVAL_ROOT` 环境变量唯一来源，无内置路径，未配置时 fail-fast 输出克隆指引。
- **Bridge 复用判定**：公开仓 `src/tju_info_retrieval/bridge.py` **已存在**且与作者在用部署逐字一致（换行归一化 diff 为空）——零重写，仅复核契约（health/auth_status/auth/search、stdout 单 JSON、业务失败不非零退出）。
- **真实 E2E 证据**：
  - `TJU_PLUGIN_LOAD = PASS`（宿主模块在位、工厂真实构造、manifest.id=tju-info-retrieval）
  - `TJU_BRIDGE_HEALTH = PASS`（全新克隆、真 Edge 检出、v0.9.0、1734→821ms 级别延迟）
  - `TJU_STATUS_MACHINE = PASS`（OFFLINE/AUTH_REQUIRED/ERROR 真实命中；READY 启发式按设计只看本地快照）
  - `TJU_AUTH_FLOW = PASS`（公开克隆真实检索→真浏览器→门户→`TjuAuthRequiredError` 零 crash；受控 Edge 手动登录流真实打开并优雅超时，恢复文案与聊天重登 UX 对接）
  - `TJU_OPEN_UI = PASS`（GUI 真实启动 pid=15312，0.7s 诚实探测 alive→opened→清理）
  - `TJU_REAL_SEARCH = AUTH_REQUIRED`：本机两份 profile 的门户会话均已过期（快照 mtime 新鲜但服务端会话失效——「真实校验延迟到使用时」的设计如实生效）。**登录是人工动作，本轮不代做**；重登→retry 路径已实测可用。

### Local Video — COMPLETE

- 部署闭环：`requirements.txt` + README 部署节 + `scripts/check_environment.py`（FFmpeg 实跑 `-version`，不只 import）+ `scripts/smoke_test.py`（`--video` 真实六要素，测试视频不入库）。
- 真实证据：环境自检 7/7；真实 MP4（70.5s，含人声+画面文字）六要素 **6/6**（ASR 16 段 115 字 / SCENE 19 / OCR 76 字）；宿主 `VideoProcessor` 全链 34.5s（**18 段真实 ASR 字幕、477 个真实 OCR 字符**）；宿主插件测试 22/22。
- 视觉边界判定：`VISUAL_DESCRIPTION = NOT_ADVERTISED`——插件与文档只承诺时长/音频/ASR/场景/关键帧/OCR；「AI 理解画面」属宿主视觉链路与 B站服务，README 已写明。
- 已知限制：Quick Tools 文件对话框为人工步骤（宿主 seam 生命周期测试覆盖）；OCR/ASR 对无文字/无人声内容如实报空。

### Camera Vision — COMPLETE

- 文档语义修正：适配器=能力开关+设备可用性；真实实现在宿主 `CameraCapture → ScreenVisionService`（架构如此，未复制、未造第二份）。
- 新增 `scripts/check_camera.py`（只枚举 `QMediaDevices.videoInputs()`，绝不拍照）。
- 隐私 Gate：`CAMERA_BACKGROUND_CAPTURE = ZERO`、`CAMERA_DISK_PERSISTENCE = ZERO`（源码 grep：无 imwrite/save/write_bytes；QTimer 仅为单次抓取 watchdog）、`CAMERA_ONE_SHOT = PASS`（契约「camera stops before returning」）。
- 真实 E2E：`CAMERA_PLUGIN_LOAD = PASS`（READY）、`CAMERA_DEVICE_FOUND = YES`（USB webcam）、`CAMERA_REAL_FRAME = YES`（capture 1040ms）、`VISION_PROVIDER_REAL = YES`（tju-qwen / tju-llm，remote_calls=1）、**`CAMERA_REAL_ANSWER = YES`**（真实中文描述摄像头前实景：鱼缸设备+银灰色鼠标）、`CAMERA_RELEASED_AFTER_REQUEST = PASS`（one-shot 契约+watchdog 保证）。

### Voice / BiliInsight — 回归保护

- 功能代码零改动。Voice：插件单测 3/3；BiliInsight：全新克隆+全新 venv 后 health(1734ms)/metadata(170ms) 双 PASS。`VOICE_REGRESSION = PASS`、`BILI_REGRESSION = PASS`。

### Learning Focus — WIP / OUT_OF_SCOPE（零改动）

## 文档与发布

- 根 README：移除不准确的「四个插件全部符合 Extension v2」；按真实架构与实测状态重写（COMPLETE/WIP 分明）；安装说明分两层（插件目录 vs **不得复制为插件**的服务型能力）。
- INTERFACE.md：PluginLoader 五插件与外部/服务型组件（BiliInsight Service、voice_module）分列。
- `docs/PLUGIN_COMPLETENESS_AUDIT.md`：六能力矩阵，全部基于本轮真实执行证据。

## Gate

- `SECRET_SCAN = ZERO` / `COOKIE = ZERO` / `TJU_SESSION = ZERO` / `STORAGE_STATE = ZERO` / `API_KEY = ZERO` / `PASSWORD = ZERO`（staged 全量正则扫描 + 人工复核，拦下一处 pytest 残留暂存险情）
- `ABSOLUTE_PERSONAL_PATH = ZERO`（无 C:\Users\、AI_Workspace、E:\ 盘符路径）
- `VIDEO_FILE_STAGED = ZERO` / `CAMERA_FRAME_STAGED = ZERO` / 模型二进制 ZERO（根 .gitignore 既有禁令未触碰）
- Git identity：两仓提交全部 `Liuyingandying@users.noreply.github.com`
- 测试矩阵：插件仓 15/15 + learning_focus OK；宿主 video 22/22、camera/screen_vision 53/54、loader/quick_tools/tju 93/94
- **已知基线失败 2 项（非本轮引入）**：Voice 加入受管目录后宿主两处陈旧断言（catalog/allowlist 期望 4 插件实为 5）。宿主与私有插件根本轮零改动。

## Clean Clone 友人测试

全新临时目录克隆三仓（插件/TJU/BiliInsight 上游）：默认 main 全部必需文件在位；15/15 单测通过；环境自检与相机设备自检 PASS；BiliInsight 全新 venv 双 action PASS。`DEFAULT_CLONE_TEST = PASS`。

## Complete Gate

| Gate | 结果 |
|---|---|
| TJU_PLUGIN_SOURCE_ON_MAIN / TJU_BRIDGE_ON_MAIN / TJU_PLUGIN_LOAD | YES / YES / PASS |
| TJU_REAL_FLOW | **PARTIAL**（六项证据五 PASS；真实检索 AUTH_REQUIRED——校园会话过期，重登为人工动作，恢复路径已实测） |
| VIDEO_REQUIREMENTS_DOCUMENTED / VIDEO_ENV_CHECK / VIDEO_REAL_E2E | YES / PASS / PASS |
| CAMERA_PLUGIN_LOAD / CAMERA_DEVICE_CHECK / CAMERA_REAL_E2E | PASS / PASS / PASS |
| ROOT_README_ACCURATE / INTERFACE_ACCURATE | YES / YES |
| VOICE_REGRESSION / BILI_REGRESSION | PASS / PASS |
| SECRET / COOKIE / PRIVATE_PATH | ZERO / ZERO / ZERO |
| DEFAULT_CLONE_TEST | PASS |
| LEARNING_FOCUS_MODIFIED | NO |

## 最终判定

**PLUGIN_ECOSYSTEM_NON_LEARNING = PARTIAL（95%）**

唯一未闭合项：TJU 真实检索需要一次**人工**校园登录（打开受控 Edge → 统一身份认证 → 重发检索）。该登录流本身已真实走通并被验证（浏览器打开、轮询、优雅超时、错误分类、聊天重登 UX 对接全部 PASS）；受同一凭证依赖的 Camera Vision 真实回答已用可用 Provider 实测通过，进一步佐证链路健康。完成人工登录后，仅重跑 `plugin.search("…")` 一步即可将本判定升为 COMPLETE。
