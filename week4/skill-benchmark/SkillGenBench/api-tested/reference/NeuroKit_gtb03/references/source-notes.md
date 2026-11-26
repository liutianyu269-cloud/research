# NeuroKit_gtb03 的参考依据

参考 `rsp_process` 和峰索引换算为秒的做法。共享脚本默认按首列与 250 Hz 处理，使用峰数除以总时长估计平均频率。本题选择实际 RSP 通道和对应采样率，按处理后的有效 BPM 序列取均值，三列按题面写列表。

产物检查。 峰时刻为非负、递增的秒数。峰次数与列表长度一致。

[基线评估题面](https://github.com/QuantaAlpha/SkillGenBench/blob/5a8bd61d8191e34fa1bbbffbff7f70db1d2a027d/skill_evaluation/code_repo/neurokit/NeuroKit_gtb03/instruction.md) · [公开素材中的同题说明](https://github.com/QuantaAlpha/SkillGenBench/blob/5a8bd61d8191e34fa1bbbffbff7f70db1d2a027d/data_source/code_repo/neurokit/tasks/NeuroKit_gtb03/instruction.md) · [extract_rsp.py](https://github.com/QuantaAlpha/SkillGenBench/blob/5a8bd61d8191e34fa1bbbffbff7f70db1d2a027d/data_source/code_repo/neurokit/shared/materials/tools/extract_rsp.py) · [README.rst](https://github.com/QuantaAlpha/SkillGenBench/blob/5a8bd61d8191e34fa1bbbffbff7f70db1d2a027d/data_source/code_repo/neurokit/tasks/NeuroKit_gtb03/materials/docs/README.rst)
