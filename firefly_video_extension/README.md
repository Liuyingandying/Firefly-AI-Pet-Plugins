# firefly_video_extension — 本地视频文件分析

本插件只做**本地视频文件**的分析：时长 / 场景检测 / 关键帧 / 字幕提取
（调用宿主的 VideoProcessor 管线，不访问网络视频平台）。

## 它不是 B站 URL 阅读器

Firefly 的视频能力有**两条互不相同的执行链**：

| | 本地视频分析（本插件） | B站 URL / BV号 阅读 |
|---|---|---|
| 输入 | 本地视频文件路径 | `https://www.bilibili.com/video/BV...` 或 BV 号 |
| 执行者 | 宿主 VideoProcessor 管线（插件适配器） | **Firefly-BiliInsight-Service**（独立 GPL-3.0 服务仓） |
| 联网下载 | 否 | 是（bilibili-api 取流 + ffmpeg 切片） |
| 转写引擎 | 宿主管线字幕/Whisper | **本地 faster-whisper ASR**（服务端独立环境） |
| 需要安装 | 随宿主即可 | 另需 Python 3.10+ / ffmpeg / 克隆服务仓 |

## B站 URL 阅读服务（独立仓库）

源码与安装说明：
**https://github.com/Liuyingandying/Firefly-BiliInsight-Service**

- 能力：`health` / `metadata` / `transcribe`（本地 ASR，非 B站官方字幕）/ `frame`
- **不需要安装 B站桌面客户端**；**公开视频匿名即可用，登录可选**
  （Cookie 只经环境变量或本地 `.env` 注入，永不入库、永不入示例）
- 许可证：GPL-3.0（上游 [Shanoa2/BiliInsight](https://github.com/Shanoa2/BiliInsight)
  services 层的封装）——因此不并入本 MIT 插件仓，经 subprocess JSONL 保持边界
- 环境变量 `FIREFLY_BILI_INSIGHT_ROOT` 指向服务仓根目录即可让 Firefly 使用
