# vendor/Retrieval-based-Voice-Conversion-WebUI-main

[RVC-Project/Retrieval-based-Voice-Conversion-WebUI](https://github.com/RVC-Project/Retrieval-based-Voice-Conversion-WebUI)
的**官方引擎代码快照**（MIT License，快照取自 2026-09-16 上游 main 分支 codeload zip，
未做任何修改；版权与许可见目录内 `LICENSE` 与 `MIT协议暨相关引用库协议`）。

Firefly Voice Service 通过 `core/converter.py` 以**进程内**方式复用该引擎的推理链
（`configs.config.Config` + `infer.vc.modules.VC`），不修改引擎代码。

## 本快照相对上游的裁剪

| 裁剪项 | 原因 |
|---|---|
| `assets/hubert_base/pytorch_model.bin`（189MB） | 模型权重不入库；从 [lj1995/VoiceConversionWebUI](https://hf-mirror.com/lj1995/VoiceConversionWebUI) `hubert_base/` 下载后放回原位（SHA256 `cc8c20f4...938442ef5`，完整值见 `../README.md` §4.2）。`config.json` 与 `preprocessor_config.json` 已保留 |
| `assets/rmvpe/`（173MB） | 与 `models/rmvpe.pt` 同源冗余；服务只读 `rmvpe_root`（即 `../../models/`） |
| `RVCRealtimeVST/` | 实时变声 VST 子工程，本服务未使用（其 iPlug2/vst3sdk 子模块随目录一并剔除） |
| `.gitmodules` | 上项的子模块声明 |

其余代码、i18n、训练目录、文档均保持原样。

## 需要下载补齐的文件（共 2 个）

1. `assets/hubert_base/pytorch_model.bin` — HuBERT 权重（transformers 格式，引擎
   `local_files_only` 加载，必须放回本目录）
2. `models/rmvpe.pt` — 见 `../../models/README.md`

## 上游更新

引擎以"零修改快照"方式集成。升级时：下载新版 codeload zip → 替换本目录 →
重跑 `../../tests/`（引擎 API 变化会在此暴露）。
