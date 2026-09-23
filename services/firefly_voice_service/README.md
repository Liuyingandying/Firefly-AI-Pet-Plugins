# Firefly Voice Service

Firefly AI Pet 的**语音服务**（独立进程）：文本 → edge-TTS → RVC 声线转换 → 本机扬声器播放。
配套的宿主侧插件 [`firefly_voice/`](../../firefly_voice/) 只负责能力开关与服务启停管理；
本目录是真正执行合成与播放的服务本体。

> 当前版本：v1.4（情绪表达层）。已在 RTX 4060 Laptop 8GB / Python 3.10 / torch 2.5.1+cu121
> 实测：热态单句（约 3s 文本）合成 ≈ 240ms，端到端含播放验证通过。

## 1. 架构

```
Firefly (宿主)
   │  LLM FINAL 回复
   ▼
firefly_voice plugin  ── 能力开关 / 服务状态 / 显式启停（本仓库 firefly_voice/）
   │
   ▼
voice_client (宿主)  ──POST /voice/speak──►  Voice Service (本目录, 127.0.0.1:8300)
                                                ├─ edge-tts   云端 TTS (LGPLv3, 需联网)
                                                ├─ RVC        声线转换 (MIT 引擎, 本地)
                                                └─ AudioQueue 优先级播放 (sounddevice)
   ◄──JSON 分段元数据(口型/表情联动)──────────────┘
```

职责边界：**Plugin 管宿主集成与控制；Service 管 TTS / RVC / 音频 / 8300 API**。

## 2. Quick Start

```powershell
# 前置: Windows 10/11, Python 3.10, 已装 git
git clone https://github.com/Liuyingandying/Firefly-AI-Pet-Plugins.git
cd Firefly-AI-Pet-Plugins\services\firefly_voice_service

# 1) 环境（默认 CPU 版 torch，可用 -Gpu nvidia|amd 切换）
powershell -ExecutionPolicy Bypass -File setup.ps1            # 或 -Gpu nvidia

# 2) 放置模型（见 §4 Model Setup，仓库不分发模型权重）

# 3) 启动
powershell -ExecutionPolicy Bypass -File start.ps1
# 冷启动模型加载约 20-50s

# 4) 健康检查
curl http://127.0.0.1:8300/health
# {"status":"ok","device":"cuda:0","speakers":{"firefly":"流萤 (Firefly)"},"loaded":["firefly"]}
```

## 3. Requirements

| 项 | 要求 |
|---|---|
| OS | Windows 10/11（Linux/macOS 未验证，理论可跑，播放层用 sounddevice） |
| Python | **3.10**（实测 3.10.21；不要用 3.12+，引擎快照按 3.10 验证） |
| 网络 | edge-TTS 需访问微软服务；模型首次部署需从 HuggingFace 下载 |
| FFmpeg | 引擎音频解码依赖（`ffmpeg-python`）；需在 PATH 或自备 |
| 显存 | GPU 路径约需 2-4GB；CPU 可跑但明显变慢 |

**⚠️ 独立虚拟环境（强制）**：本服务要求 `numpy<2`，与 Firefly 主程序依赖存在冲突风险。
**禁止与 Firefly 主工程共用 venv/conda 环境**。`setup.ps1` 默认创建服务私有 `.venv`。

## 4. Model Setup（重要：模型不在本仓库中）

本仓库**不分发任何模型权重**（License 边界见 §11）。服务启动与推理需要以下文件：

### 4.1 RVC 说话人模型（流萤）

| 文件 | 放置位置 | 来源 | SHA256 |
|---|---|---|---|
| `firefly-chinese.pth` | `models/firefly/` | [Waterwzy/RVC-firefly-finetuning](https://hf-mirror.com/Waterwzy/RVC-firefly-finetuning) `weights/` | `f59e5cb51343c84a412bc9f82397563e9c33380c5372d1f0b4b1b84579ae8ca3` |
| `firefly-chinese_v2.index` | `models/firefly/` | 同仓库 `indices/`（文件名可能带 IVF 前缀，重命名即可） | `4b708b783ebbf1aae24a138e778387982fa02946c7460e0b7820079405c501fd` |

> ⚠️ 该模型 **AGPL-3.0**，训练数据为米哈游《崩坏：星穹铁道》游戏语音，**仅限个人研究/学习**，
> 严禁商用，不得用于伪造他人言论。下载即代表你接受其 LICENSE 与上游声明。

### 4.2 基础模型（RVC 引擎资产）

| 文件 | 放置位置 | 来源 | SHA256 |
|---|---|---|---|
| `pytorch_model.bin` | `vendor/.../assets/hubert_base/` | [lj1995/VoiceConversionWebUI](https://hf-mirror.com/lj1995/VoiceConversionWebUI) `hubert_base/` | `cc8c20f4b90a520757260197a3ff2505705a7adbd20ad9eeaa4e1a9b38442ef5` |
| `rmvpe.pt` | `models/` | 同仓库 `rmvpe/` | `6d62215f4306e3ca278246188607209f09af3dc77ed4232efdd069798c4ec193` |

`hubert_base/config.json` 与 `preprocessor_config.json` 已随仓库提供（引擎按本地目录加载 HuBERT）。

下载示例（PowerShell，`hubert_base/pytorch_model.bin` 同法）：

```powershell
Invoke-WebRequest -Uri "https://hf-mirror.com/Waterwzy/RVC-firefly-finetuning/resolve/main/weights/firefly-chinese.pth" -OutFile models\firefly\firefly-chinese.pth
Invoke-WebRequest -Uri "https://hf-mirror.com/lj1995/VoiceConversionWebUI/resolve/main/rmvpe/rmvpe.pt" -OutFile models\rmvpe.pt
```

huggingface.co 直连不可用时用 `hf-mirror.com` 镜像（把 URL 域名替换即可）。
下载后可用 `Get-FileHash <文件> -Algorithm SHA256` 比对上表。

### 4.3 替换为自己的音色

`config.yaml` 的 `speakers` 注册表驱动一切：把 `model`/`index` 指向你自有的
RVC 模型（或用 RVC 官方仓库自行训练），改 `display_name` 即可。流萤模型只是默认注册项。

## 5. Start

```powershell
powershell -ExecutionPolicy Bypass -File start.ps1
# 等价: .venv\Scripts\python.exe api\server.py
```

- 监听 `127.0.0.1:8300`（仅回环，见 `config.yaml` 的 `service.host/port`）
- 冷启动 20-50s（模型加载）；`GET /health` 返回 200 即就绪
- 首次运行若 `config.yaml` 不存在，从 `config.example.yaml` 复制一份（字段说明见该文件）

## 6. Health Check

```
GET http://127.0.0.1:8300/health
→ 200 {"status":"ok","device":"cuda:0","speakers":{"firefly":"流萤 (Firefly)"},"loaded":["firefly"]}
```

`device` 字段即当前推理设备（`cuda:0` / `privateuseone:0`(DirectML) / `cpu`）。

## 7. API

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/health` | 健康检查：设备 / 已注册说话人 / 已加载模型 |
| GET | `/voice/speakers` | 说话人列表 |
| POST | `/voice/speak` | **主接口**：文本 → 情绪解析 → 分句 → 逐句 TTS+RVC → 播放或返回 wav |
| POST | `/voice/convert` | 音频→音频转换（multipart：`file` + `speaker_id` + `pitch` + `index_rate`） |
| POST | `/voice/tts_convert` | 文本→wav 单跳（form：`text`，可选 `voice`/`speaker_id`/`pitch`） |
| GET | `/voice/queue` | 播放队列状态 `{playing, queued, dropped_total, device}` |
| POST | `/voice/queue/stop` | 打断：停当前播 + 清待播 + 取消活跃合成会话 |
| POST | `/voice/queue/clear` | 仅清空待播队列 |

### POST /voice/speak（JSON）

```json
{
  "text": "必填，LLM 回复文本",
  "emotion": "happy|sad|comfort|excited|neutral|worried|shy，省略则关键词自动推断",
  "intensity": 0.5,
  "speaking_style": "firefly|gentle",
  "speaker_id": "firefly",
  "play": false,
  "priority": 1,
  "voice": "zh-CN-XiaoxiaoNeural"
}
```

- `play=false`（默认）：返回 `audio/wav`（全句拼接），响应头含
  `X-Emotion / X-Emotion-Source / X-Segments / X-Total-Ms / X-Session-Id`
- `play=true`：边转边播，返回 JSON 分段元数据（含 `session_id`、`segments[]`、`queue`），
  供桌宠口型/表情联动
- `priority >= 10` 视为紧急：抢占当前播放并丢弃更低优先级待播项
- 未注册情绪自动回退 `neutral`；空文本 → 400；未注册说话人 → 404

### 与宿主 voice_client 的契约

宿主 `voice_client` 只使用两个接口：`POST /voice/speak`（`{text, play:true, priority, emotion?}`
→ 读 JSON 的 `emotion/segments/total_ms`）与 `POST /voice/queue/stop`。字段名、默认值与
状态码以本表为准，改动需双向同步。

## 8. Firefly Integration

1. 安装插件：把本仓库 `firefly_voice/` 复制到 Firefly 插件根（见顶层 README）
2. 在用户插件配置 `%LOCALAPPDATA%\FireflyAI\plugins\firefly_voice\config.yaml` 填服务路径：

```yaml
voice:
  service:
    root: "D:\\path\\to\\Firefly-AI-Pet-Plugins\\services\\firefly_voice_service"
    python: "D:\\path\\to\\Firefly-AI-Pet-Plugins\\services\\firefly_voice_service\\.venv\\Scripts\\python.exe"
    script: api/server.py
```

3. Voice Settings 面板 →「启动语音服务」（或手动 `start.ps1`）
4. 播放按钮 🔊 / Auto Play 即走完整链路

服务与宿主**完全解耦**：服务离线时聊天零影响（客户端永不抛异常），插件状态显示 OFFLINE。

## 9. CPU / GPU

`config.yaml` 的 `engine.device: auto` 按以下顺序自动选择（引擎内建逻辑）：

| 优先级 | 设备 | 条件 | 精度 | 安装方式 |
|---|---|---|---|---|
| 1 | CUDA | `torch.cuda.is_available()` | fp16（按显卡算力） | `setup.ps1 -Gpu nvidia` |
| 2 | **DirectML** | 装了 `torch-directml` 且探测到可用适配器 | fp32 | `setup.ps1 -Gpu amd`（**AMD 显卡如 RX 7600S 走此路径**） |
| 3 | CPU | 以上都不可用 | fp32 | 默认 |

- **不要**写死 `cuda` / `cuda:0`；公开配置统一 `device: auto`
- AMD 新卡（如 RX 7600S）装 `torch-directml` 后无需任何代码改动即走 GPU（fp32）
- CPU 路径可完成全部功能（PoC 级速度），无 GPU 也能跑通
- 显存不足时关闭其他占卡进程；仍 OOM 可改用 CPU 设备

## 10. Troubleshooting

| 症状 | 原因与处理 |
|---|---|
| `/health` 连接拒绝 | 服务未启动或还在加载模型（20-50s），看启动窗口日志 |
| `edge_tts.exceptions.NoAudioReceived` | 云端 TTS 网络问题：检查代理/防火墙；企业代理环境给进程设 `HTTPS_PROXY`。注意：**Git Bash 里用 `curl -d` 直接传中文会变成 `?`**（命令行编码坑），测试请用 `scripts/client.py` 或脚本内 UTF-8 编码 |
| `FileNotFoundError: ... firefly-chinese.pth` | 模型未放置，见 §4 |
| `RVC 引擎目录不存在` | vendor 目录不完整（重新 clone 完整仓库） |
| 8300 端口被占 | `config.yaml` 改 `service.port`，并同步插件配置 `server.url` |
| 播放无声但无报错 | 系统输出设备/音量；`/voice/queue` 的 `device` 字段显示 `simulated(no device)` 说明 sounddevice 不可用 |
| numpy 版本冲突 | 你共用了 Firefly 主工程环境——按 §3 建独立 venv |

## 11. Security & License

**Security**
- 服务只监听 `127.0.0.1` 回环，不对局域网开放；无鉴权（单用户本机场景），勿手动改 `host: 0.0.0.0`
- `speak` 的文本会经 **edge-TTS 发往微软云端合成**（这是唯一出网数据面）；RVC 转换与播放全部本机
- 不写任何 Secret；配置仅含端口与相对路径

**License**

| 组件 | License | 分发状态 |
|---|---|---|
| `api/ audio/ core/ config/ scripts/ tests/`（Firefly Voice Service 本体） | 与仓库根 LICENSE 一致 | ✅ 本仓库 |
| RVC 引擎快照 `vendor/Retrieval-based-Voice-Conversion-WebUI-main/` | **MIT**（含官方版权声明与第三方引用库协议文件） | ✅ 本仓库（剔除大二进制与未使用的 VST 子工程） |
| `edge-tts` | **LGPL-3.0**（`srt_composer.py` 为 MIT） | pip 依赖，不随仓库分发 |
| 流萤声线模型 `models/firefly/*` | **AGPL-3.0 + 训练数据为游戏语音** | ❌ **不在本仓库**，用户自行下载，仅限个人研究 |
| HuBERT / rmvpe 基础模型 | 随上游 HF 仓库分发条款 | ❌ 不在本仓库，见 §4.2 下载 |

> 流萤角色声音版权归属米哈游（HoYoverse）。本项目定位个人研究 Demo；
> 公开演示请自行评估并标注声音模型来源。商用或公开分发产品前，
> 请替换为自有训练/已授权的音色模型。
