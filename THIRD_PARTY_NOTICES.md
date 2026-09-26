# Third-Party Notices / 第三方许可清单

本仓库为 multi-license repository。默认插件代码按仓库根 [`LICENSE`](LICENSE)（MIT）分发；
**例外**：[`firefly_bili_insight_service/`](firefly_bili_insight_service/) 为
GPL-3.0-or-later，不受根 MIT LICENSE 覆盖。

## firefly_bili_insight_service/（GPL-3.0-or-later）

该目录内的封装代码（`service.py`、`bili_compat.py`）以 **GPL-3.0-or-later** 发布，
因为它进程内 import 以下 GPL 上游：

| 组件 | 许可证 | 说明 |
|---|---|---|
| [Shanoa2/BiliInsight](https://github.com/Shanoa2/BiliInsight)（`bilichat` services 层） | GPL-3.0 | 运行时按目录约定/`BILIINSIGHT_SRC` 定位，不 vendor 进本仓库 |
| [Nemo2011/bilibili-api](https://github.com/Nemo2011/bilibili-api)（bilibili-api-python 17.4.2） | GPL-3.0-or-later | B站 HTTP API 封装（pip 依赖） |

其余 Python 依赖（随 `firefly_bili_insight_service/requirements.txt` 安装）：

| 组件 | 许可证 |
|---|---|
| faster-whisper | MIT |
| ctranslate2 | MIT |
| httpx | BSD-3-Clause |
| pydantic / pydantic-settings | MIT |
| PyYAML | MIT |
| python-dotenv | BSD-3-Clause |

ASR 模型权重：[Systran/faster-whisper-small](https://huggingface.co/Systran/faster-whisper-small)
（MIT），首次 `transcribe` 由 HuggingFace Hub 自动下载，不入库。

## 其余插件目录（MIT）

`firefly_video_extension/`、`firefly_camera_vision/`、`learning_focus/`、
`firefly_voice/`（含 `voice_module/` 的 vendor 引擎快照，MIT）均按仓库根 MIT LICENSE
分发；运行期依赖的宿主模块（PySide6 等）许可归各自上游。

## 商标与内容

Bilibili 及相关名称归属上海幻电信息科技有限公司；本项目与其无隶属关系，
仅通过公开 HTTP API 读取用户指定的公开视频内容。
