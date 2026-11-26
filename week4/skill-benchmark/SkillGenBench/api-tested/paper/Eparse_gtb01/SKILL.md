---
name: eparse-workbook-report
description: "将目录里的多个工作簿整理为一份可读的工作表报告。"
---

# Eparse_gtb01

将目录里的多个工作簿整理为一份可读的工作表报告。

读完本页后先执行这条命令。它会依次检查输入、生成产物并回读验收。

```sh
python -B /workspace/skill/scripts/run_workflow.py Eparse_gtb01 excel.py /workspace/input /workspace/output
```

命令退出码为 0 且输出 `status: validated` 时，提交文件位于 `/workspace/output/eparse_report.txt`。保留该文件并结束。失败时根据报错的步骤定位输入、依赖或格式问题。

## 输入和依赖

- 输入为 `/workspace/input` 中的 Eparse_gtb01_input/ 下的 XLSX 工作簿。
- 依赖为 eparse 0.9.2，及其 pandas 和 openpyxl 依赖。

## 处理步骤

1. 跳过 Excel 的锁文件，按文件名稳定排序。逐个读取工作簿的工作表顺序。
2. 复用 Eparse 的 `get_df_from_file` 定位表格。当检测只覆盖工作表的一部分，或同一工作表有多个逻辑表，读取完整工作表网格，保留零散内容。
3. 每个文件用题面要求的 `File name:` 开头，每个工作表有自己的标题。用不截断行列的 DataFrame 文本写出完整报告。

## 验收与适用范围

回读报告标题，逐项核对文件与工作表名称以及顺序。工作表为空时保留该工作表的条目。

保持真实文件名、表名和原工作表顺序。处理结构相似的新文件时，仍以输入文件的实际内容生成报告。

[公开题面](https://github.com/QuantaAlpha/SkillGenBench/blob/5a8bd61d8191e34fa1bbbffbff7f70db1d2a027d/skill_evaluation/code_repo/eparse/Eparse_gtb01/instruction.md) · [上游接口资料](https://github.com/ChrisPappalardo/Eparse)
