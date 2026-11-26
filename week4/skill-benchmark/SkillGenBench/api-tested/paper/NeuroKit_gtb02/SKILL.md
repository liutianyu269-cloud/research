---
name: extract-ecg-peak-indices
description: "在 150 Hz 的 ECG 信号中提取 R 峰与 P 峰的位置。"
---

# NeuroKit_gtb02

在 150 Hz 的 ECG 信号中提取 R 峰与 P 峰的位置。

读完本页后先执行这条命令。它会依次检查输入、生成产物并回读验收。

```sh
python -B /workspace/skill/scripts/run_workflow.py NeuroKit_gtb02 signals.py /workspace/input /workspace/output
```

命令退出码为 0 且输出 `status: validated` 时，提交文件位于 `/workspace/output/ecg_peaks.csv`。保留该文件并结束。失败时根据报错的步骤定位输入、依赖或格式问题。

## 输入和依赖

- 输入为 `/workspace/input` 中的 NeuroKit_gtb02_input.csv 中的 ECG 列。
- 依赖为 NeuroKit2 0.2.12，NumPy 2.2.6，pandas。

## 处理步骤

1. 读取 ECG 列并保留输入采样顺序。题目指定采样率为 150 Hz。
2. 用 `neurokit2.ecg_process(..., sampling_rate=150, method='neurokit')` 运行完整流程，从事件字典取 R/P 峰。
3. 丢弃标为缺失的检测值，将剩余位置写成整数列表。输出一行两列 CSV，两个字段各是一个 JSON 列表。

## 验收与适用范围

回读列表，确认位置是有序、不重复、在源采样数以内的整数。

列表元素的单位是采样点索引。每个通道的峰单独报告，保留模型实际检测到的事件数量。

[公开题面](https://github.com/QuantaAlpha/SkillGenBench/blob/5a8bd61d8191e34fa1bbbffbff7f70db1d2a027d/skill_evaluation/code_repo/neurokit/NeuroKit_gtb02/instruction.md) · [上游接口资料](https://neuropsychology.github.io/NeuroKit/_modules/neurokit2/ecg/ecg_process.html)
