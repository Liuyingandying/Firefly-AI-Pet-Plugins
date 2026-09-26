# firefly_video_extension — 本地视频文件分析

本插件只做**本地视频文件**的分析：时长 / 场景检测 / 关键帧 / 字幕提取
（调用宿主的 VideoProcessor 管线，不访问网络视频平台）。

## 它不是 B站 URL 阅读器

Firefly 的视频能力有**两条互不相同的执行链**：

| | 本地视频分析（本插件） | B站 URL / BV号 阅读 |
|---|---|---|
| 输入 | 本地视频文件路径 | `https://www.bilibili.com/video/BV...` 或 BV 号 |
| 执行者 | 宿主 VideoProcessor 管线（插件适配器） | **[`../firefly_bili_insight_service/`](../firefly_bili_insight_service/README.md)**（同仓库 GPL-3.0 目录） |
| 联网下载 | 否 | 是（bilibili-api 取流 + ffmpeg 切片） |
| 转写引擎 | 宿主管线字幕/Whisper | **本地 faster-whisper ASR**（服务端独立环境） |
| 需要安装 | 随宿主即可 | 另需 Python 3.10+ / ffmpeg / 上游 BiliInsight 克隆 |

## B站 URL 阅读服务（同仓库，另一条链）

源码与安装说明：**[`../firefly_bili_insight_service/`](../firefly_bili_insight_service/README.md)**

- 能力：`health` / `metadata` / `transcribe`（本地 ASR，**非 B站官方字幕**）/ `frame`
- **不需要安装 B站桌面客户端**；**公开视频匿名即可用，登录 OPTIONAL**
  （Cookie 只经环境变量或本地 `.env` 注入，永不入库、永不入示例）
- 许可证：**GPL-3.0-or-later**（上游 [Shanoa2/BiliInsight](https://github.com/Shanoa2/BiliInsight)
  services 层的封装）——本仓库为 multi-license：该目录及其衍生代码不受根 MIT LICENSE
  覆盖，经 subprocess JSONL 与宿主保持许可证边界（详见根
  [`THIRD_PARTY_NOTICES.md`](../THIRD_PARTY_NOTICES.md)）
- 环境变量 `FIREFLY_BILI_INSIGHT_ROOT` 指向
  `<Firefly-AI-Pet-Plugins>/firefly_bili_insight_service` 即可让 Firefly 使用


## 安装与部署（本地视频分析）

插件本体随宿主即用；**引擎依赖**决定六项能力是否全绿：

```bash
# 1) FFmpeg / ffprobe（系统依赖，必须在 PATH）
winget install ffmpeg          # 或 https://www.gyan.dev/ffmpeg/builds/
ffmpeg -version && ffprobe -version

# 2) 引擎依赖（宿主 requirements 已含 rapidocr>=3.9,<4；缺哪项装哪项）
pip install faster-whisper scenedetect
```

一键自检与真实冒烟（测试视频自备，**不要提交到仓库**）：

```bash
python scripts/check_environment.py               # 逐项 PASS/FAIL + 安装提示
python scripts/smoke_test.py --video <你的.mp4>    # DURATION/AUDIO/ASR/SCENE/KEYFRAME/OCR
```

| 依赖 | 提供的能力 | 缺失时 |
|---|---|---|
| FFmpeg / ffprobe | 时长、音频提取、关键帧、抽帧 | 管线不可用 |
| faster-whisper | 本地 ASR 字幕 | 字幕段为空（降级） |
| PySceneDetect | 场景检测 | 跳过场景分段（降级） |
| rapidocr + onnxruntime | 关键帧 OCR | OCR 为空（降级） |

能力边界：本插件**不调用视觉大模型**——「AI 理解视频画面」由宿主视觉链路
（B站 URL 阅读见 [`../firefly_bili_insight_service/`](../firefly_bili_insight_service/README.md)）
提供，不在此插件的承诺范围内。
