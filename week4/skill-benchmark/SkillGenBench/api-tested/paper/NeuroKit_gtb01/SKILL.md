---
name: eda-scr-summary
description: "从 EDA 记录导出 SCR 幅度均值、SCR 次数和 tonic 标准差。"
---

# NeuroKit_gtb01

从 EDA 记录导出 SCR 幅度均值、SCR 次数和 tonic 标准差。

读完本页后先执行这条命令。它会依次检查输入、生成产物并回读验收。

```sh
python -B /workspace/skill/scripts/run_workflow.py NeuroKit_gtb01 signals.py /workspace/input /workspace/output
```

命令退出码为 0 且输出 `status: validated` 时，提交文件位于 `/workspace/output/eda_scr_metrics.csv`。保留该文件并结束。失败时根据报错的步骤定位输入、依赖或格式问题。

## 输入和依赖

- 输入为 `/workspace/input` 中的 NeuroKit_gtb01_input.csv 中的 EDA 列。
- 依赖为 NeuroKit2 0.2.12，NumPy 2.2.6，pandas。

## 处理步骤

1. 读取 `EDA` 数值列并检查有限值。原题没提供采样率，本案沿用相关公开 GitTaskBench EDA 示例的 250 Hz，作为计算假设。
2. 通过 `neurokit2.eda_process` 获取峰标记、幅度和 tonic 序列。只在检测到 SCR 的位置取有效幅度，计数用峰标记总数。
3. 用总体标准差 `ddof=0` 描述 tonic 横跨本段记录的波动。输出单行 CSV，幅度缺失用空字段表达。

## 验收与适用范围

检查 CSV 恰有一条记录，峰数为非负整数，标准差为有限非负数。无检测峰时允许幅度为空。

换录制文件时，应从该录制的文档或采集配置确认采样率。

[公开题面](https://github.com/QuantaAlpha/SkillGenBench/blob/5a8bd61d8191e34fa1bbbffbff7f70db1d2a027d/skill_evaluation/code_repo/neurokit/NeuroKit_gtb01/instruction.md) · [上游接口资料](https://neuropsychology.github.io/NeuroKit/_modules/neurokit2/eda/eda_process.html)
