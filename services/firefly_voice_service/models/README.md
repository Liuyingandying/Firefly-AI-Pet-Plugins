# models/ — 模型资产目录（权重不入库）

本目录的权重文件**不进 Git**（License 边界见 [`../README.md` §11](../README.md#11-security--license)）。
按下面清单放置文件后服务即可运行。

```
models/
├─ firefly/
│  ├─ firefly-chinese.pth         # 说话人模型 (AGPL-3.0, 52.7MB)
│  └─ firefly-chinese_v2.index    # 检索索引   (AGPL-3.0, 30.1MB)
└─ rmvpe.pt                        # F0 提取模型 (181MB)
```

## 下载

| 文件 | URL（直连不可用把域名换 `hf-mirror.com`） | SHA256 |
|---|---|---|
| `firefly/firefly-chinese.pth` | `https://huggingface.co/Waterwzy/RVC-firefly-finetuning/resolve/main/weights/firefly-chinese.pth` | `f59e5cb51343c84a412bc9f82397563e9c33380c5372d1f0b4b1b84579ae8ca3` |
| `firefly/firefly-chinese_v2.index` | `https://huggingface.co/Waterwzy/RVC-firefly-finetuning/resolve/main/indices/firefly-chinese_added_IVF256_Flat_nprobe_1_firefly-chinese_v2.index` | `4b708b783ebbf1aae24a138e778387982fa02946c7460e0b7820079405c501fd` |
| `rmvpe.pt` | `https://huggingface.co/lj1995/VoiceConversionWebUI/resolve/main/rmvpe/rmvpe.pt` | `6d62215f4306e3ca278246188607209f09af3dc77ed4232efdd069798c4ec193` |

校验：`Get-FileHash <文件> -Algorithm SHA256`

## License 边界（务必阅读）

- `Waterwzy/RVC-firefly-finetuning`：**AGPL-3.0**；训练数据为《崩坏：星穹铁道》流萤游戏内
  中文语音语料。**仅限个人研究/学习，严禁商用**；以 API/网络服务形式对外提供需遵守 AGPL
  开源义务；不得用于伪造言论或侵犯角色版权。角色声音版权归属米哈游（HoYoverse）。
- `lj1995/VoiceConversionWebUI`（rmvpe 等）：随该 HF 仓库的发布条款，供 RVC 引擎研究使用。
- 若需公开发布产品，请替换为**自有训练或已授权**的音色模型，并同步修改 `config.yaml`
  的 `speakers` 注册表。

## 换自己的音色

用 RVC 官方工具自行训练模型后，改 `../config.yaml`：

```yaml
speakers:
  my_voice:
    display_name: "My Voice"
    model: models/my_voice/my.pth
    index: models/my_voice/my.index
    index_rate: 0.75
```

之后 `/voice/speak` 传 `"speaker_id": "my_voice"` 即可。
