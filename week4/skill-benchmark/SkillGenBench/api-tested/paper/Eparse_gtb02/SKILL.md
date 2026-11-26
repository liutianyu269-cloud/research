---
name: eparse-cells-jsonl
description: "把 Excel 工作簿中有内容的单元格导出为逐行 JSON。"
---

# Eparse_gtb02

把 Excel 工作簿中有内容的单元格导出为逐行 JSON。

读完本页后先执行这条命令。它会依次检查输入、生成产物并回读验收。

```sh
python -B /workspace/skill/scripts/run_workflow.py Eparse_gtb02 excel.py /workspace/input /workspace/output
```

命令退出码为 0 且输出 `status: validated` 时，提交文件位于 `/workspace/output/eparse_cells.jsonl`。保留该文件并结束。失败时根据报错的步骤定位输入、依赖或格式问题。

## 输入和依赖

- 输入为 `/workspace/input` 中的 Eparse_gtb02_input.xlsx。
- 依赖为 eparse 0.9.2，及其 pandas 和 openpyxl 依赖。

## 处理步骤

1. 按工作表读取 Eparse 发现的逻辑表。用 `df_serialize_table` 把值、类型、行列位置和表头上下文转换为单元格记录。
2. 记录以 `(sheet, excel_RC)` 为唯一键。用原工作表网格检查遗漏的非空单元格，孤立单元的行列标题填空值。
3. 按工作表和 Excel 坐标顺序输出。每一行单独是一个 JSON 对象，保留 `row`、`column`、`value`、`type`、`c_header`、`r_header`、`excel_RC`、`sheet` 和 `f_name`。

## 验收与适用范围

逐行解析 JSON，检查字段、坐标唯一、工作簿文件名与原值。将实际非空单元格覆盖情况计入输出日志。

用题目要求的 JSON Lines 写盘。日期和数值通过 Eparse 的现有归一化规则编码。

[公开题面](https://github.com/QuantaAlpha/SkillGenBench/blob/5a8bd61d8191e34fa1bbbffbff7f70db1d2a027d/skill_evaluation/code_repo/eparse/Eparse_gtb02/instruction.md) · [上游接口资料](https://github.com/ChrisPappalardo/Eparse)
