# 插件生态完整性审计（Capability Matrix）

> 2026-09-26「非 Learning 功能全量补齐」轮的 Phase 1 产出。
> 判定全部来自本轮真实执行证据，不是代码存在性推断。

## 矩阵

| Capability | Public source | Runtime dependency | Install doc | Unit test | Real E2E | Default clone | Gap |
|---|---|---|---|---|---|---|---|
| **Voice**（firefly_voice + voice_module） | ✅ 完整源码 | edge-tts/RVC/声卡；模型权重外置 | ✅ 其 README + 宿主 VOICE_SETUP | ✅ 插件内 + 仓库级 | ✅ 本轮前已 COMPLETE（本轮仅回归保护） | ✅ | 无（模型按其 README 自取） |
| **BiliInsight**（firefly_bili_insight_service） | ✅ 完整源码（GPL-3.0 子树） | Python venv + ffmpeg + 上游 BiliInsight 克隆 + whisper 模型自动下载 | ✅ 其 README（插件仓 clone 起点） | ✅ smoke_test 四 action | ✅ 匿名四 action 全 PASS（同日两轮） | ✅ 零 env 友人仿真 4/4 | 无 |
| **Local Video**（firefly_video_extension） | ✅ 完整源码 | ffmpeg/ffprobe + faster-whisper + scenedetect + rapidocr（本轮补齐文档与自检） | ✅ README 部署节 + check_environment.py | ✅ 宿主 22 测试 + 真实冒烟 6/6 | ✅ 真实 MP4：ASR 18 段/OCR 477 字/19 场景 | ✅（宿主在位即用） | GUI 文件对话框为人工步骤（生命周期经宿主 seam 测试验证） |
| **Camera Vision**（firefly_camera_vision） | ✅ 适配器（真实实现在宿主，架构如此设计） | 真实摄像头 + 宿主 Vision Provider | ✅ README + check_camera.py | ✅ 宿主相机回归 53 过/1 基线失败 | ✅ 真实「看看我」链路：USB webcam 抓帧 → tju-qwen 真实回答 | ✅（宿主在位即用） | 无（回答依赖 Vision Provider 凭据） |
| **TJU Info Retrieval**（tju_info_retrieval） | ✅ 本轮补齐（adapter/plugin/tests/README，此前仅 INTERFACE.md） | 外部工程 tju-research-assistant 克隆 + playwright + Edge | ✅ README + TJU_BRIDGE_CONTRACT.md | ✅ 12 单测 | ⚠️ LOAD/HEALTH/AUTH 流/open_ui 全 PASS；真实检索=AUTH_REQUIRED（门户会话过期，需人工重登） | ✅（设 env 即用） | 校园登录态（用户动作） |
| **Learning Focus**（learning_focus） | ✅（未触碰） | — | — | — | — | — | **WIP / OUT_OF_SCOPE**：开发中，本轮禁改 |

## 本轮修正动作

1. TJU 插件从「仅接口文档」补齐为完整适配器（源码移植自已验证的私有实现，
   唯一差异=去机器化：`TJU_INFO_RETRIEVAL_ROOT` env-only，无内置路径）。
2. Video 补部署闭环：requirements/README 部署节/check_environment.py/smoke_test.py。
3. Camera 补 README（适配器语义澄清）+ check_camera.py。
4. 根 README / INTERFACE.md 按真实状态重写（Phase 19-22）。
5. tju-research-assistant 仓补 .gitignore（保护用户克隆不提交 data//runtime/ 登录产物）。

## 已知基线失败（非本轮引入）

- 宿主 `tests/test_camera_vision_plugin_integration.py::test_real_managed_catalog_renders_only_managed_product_tools`：
  Voice 插件化后 Quick Tools 目录多出 Voice 项，断言未更新。宿主与私有插件根本轮零改动。
