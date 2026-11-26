---
name: rsp-breath-events
description: "从原题提供的呼吸波形计算平均呼吸频率、峰时刻和峰数。"
---

# NeuroKit_gtb03

从原题提供的呼吸波形计算平均呼吸频率、峰时刻和峰数。

读完本页后先执行这条命令。它会依次检查输入、生成产物并回读验收。

```sh
python -B /workspace/skill/scripts/run_workflow.py NeuroKit_gtb03 signals.py /workspace/input /workspace/output
```

命令退出码为 0 且输出 `status: validated` 时，提交文件位于 `/workspace/output/eog_metrics.csv`。保留该文件并结束。失败时根据报错的步骤定位输入、依赖或格式问题。

## 输入和依赖

- 输入为 `/workspace/input` 中的 NeuroKit_gtb03_input.csv 中的 RSP 列。
- 依赖为 NeuroKit2 0.2.12，NumPy 2.2.6，pandas。

## 处理步骤

1. 先看实际列名。原题称 EOG，本题 CSV 有 RSP 列且没有 EOG。用公开 NeuroKit 样例的匹配录制片段为这个案例选择 100 Hz。
2. 使用 `neurokit2.rsp_process` 取得有效的瞬时呼吸频率和峰采样位置。峰索引除以采样率得到秒，平均频率从有效值求均值。
3. 按题面保留 `eog_metrics.csv` 文件名，三列均用列表。峰数用只含总数的一项列表写出。

## 验收与适用范围

回读 CSV，检查三列列表形状、有限值、峰时刻顺序和峰数一致性。

此流程要求有呼吸通道。换录制时需要确定通道及采样率，不能直接把眼电列作为呼吸波形。

[公开题面](https://github.com/QuantaAlpha/SkillGenBench/blob/5a8bd61d8191e34fa1bbbffbff7f70db1d2a027d/skill_evaluation/code_repo/neurokit/NeuroKit_gtb03/instruction.md) · [上游接口资料](https://neuropsychology.github.io/NeuroKit/_modules/neurokit2/rsp/rsp_process.html)
