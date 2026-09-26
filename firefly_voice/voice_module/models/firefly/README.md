---
language:
- zh
license: agpl-3.0
pipeline_tag: audio-to-audio
tags:
- RVC
- honkai-star-rail
- game-character
- Voice Conversion
- firefly
---

# 流萤 (Firefly) - 崩坏：星穹铁道 RVC 模型

本仓库是基于 [RVC](https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI) 框架微调的《崩坏：星穹铁道》角色 **流萤（Firefly）** 语音转换模型。

## 🎵 音频样例

本项目提供一个个推理音频样例，位于 `tests` 目录下。

## 🚀 如何使用（推理）

请确保已安装 [RVC](https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI) 环境。

### 1. 克隆本仓库并将文件放入对应目录

```bash
# 假设你的 RVC 项目根目录为 /path/to/RVC
git clone https://huggingface.co/Waterwzy/RVC-firefly-finetuning
cd RVC-firefly-finetuning
cp ./indices/firefly-chinese_added_IVF256_Flat_nprobe_1_firefly-chinese_v2.index /path/to/RVC/assets/indices//
cp ./weights/firefly-chinese.pth /path/to/RVC/assets/weights/
```

### 2.开始推理

使用 RVC 的 `webui.py` 即可打开 webui 进行推理。

## 📊训练细节

- **训练数据**：基于流萤游戏内中文语音语料（截至3.8版本）

- **训练平台**：NVIDIA GeForce RTX 5070 LapTop GPU（8GB VRAM）

- **测试结果**：中文歌曲表现良好，英文歌曲泛化能力符合预期；其他语言歌曲泛化能力未测试。

## ⚠️ 已知局限与免责声明

1. **语言限制**：仅测试过中文、英文歌曲，对韩文、日文等泛化能力未知。

2. **风险提示**：请勿将该模型用于制作虚假内容、欺诈或侵犯角色版权的用途。

3. 本模型基于 AGPL-3.0 协议开源。**若通过 API/Web 等方式提供服务，或修改权重分发，必须开源修改后的代码与权重**。

## 🔗 致谢

- 上游框架：[RVC-Project/Retrieval-based-Voice-Conversion-WebUI](https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI)

- 角色版权归属：米哈游（HoYoverse）
