# firefly_camera_vision — 相机视觉能力适配器（Managed capability gate）

> **这不是摄像头实现本体。** 真实的拍照 → 视觉理解实现在 Firefly 宿主
> （`core/screen_vision/screen/camera.py` 的 CameraCapture → ScreenVisionService →
> Vision Provider）。本插件是**能力开关与设备可用性适配器**：Quick Tools 面板的
> 状态卡、宿主 `camera_vision_enabled` 门控的判定来源。**不复制宿主实现、不持有
> 任何相机资源。**

## 它做什么 / 不做什么

| 做 | 不做 |
|---|---|
| 设备可用性查询（`QMediaDevices.videoInputs()`） | 打开相机 |
| 能力暴露开关（start/stop 只改标志位） | 后台常驻 / 周期采样 |
| 向 Quick Tools 发布状态（READY/UNAVAILABLE） | 保存任何画面（帧只在内存） |
| 独立于真实实现演进的薄壳 | 视觉推理（归宿主 Vision Provider） |

宿主侧隐私不变量（CameraCapture 契约，代码审计 Gate）：

- 只在**用户显式请求**的回合内捕获（聊天「看看我」触发）
- 一次一帧（one-shot），返回前停止相机
- 帧**只在内存**：零磁盘写入、零持久化、零后台循环

## 使用

1. Quick Tools 开启 **Camera Vision**；
2. 聊天输入「看看我」等显式请求 → 宿主链路拍一帧 → Vision Provider → AI 回答。

## 环境要求

| 需要 | 不需要 |
|---|---|
| 真实摄像头（内置或外接） | 独立 Camera Service 进程 |
| PySide6 Multimedia（宿主已含） | 后台常驻相机进程 |
| 可用的 Vision Provider 及其凭据（宿主配置） | 额外的模型下载 |
| 宿主正常运行（Windows Media Foundation） | |

一键设备自检（只查询设备，**不拍照**）：

```bash
python scripts/check_camera.py
```

真实端到端：在运行中的 Firefly 聊天里发送「看看我」，AI 的回答即真实相机帧的
视觉理解结果。
