---
name: export-pdf-document-info
description: "读取 PDF 的 Document Info 并导出作者、标题和创建日期。"
---

# PyPDF2_gtb03

读取 PDF 的 Document Info 并导出作者、标题和创建日期。

读完本页后先执行这条命令。它会依次检查输入、生成产物并回读验收。

```sh
python -B /workspace/skill/scripts/run_workflow.py PyPDF2_gtb03 pdf.py /workspace/input /workspace/output
```

命令退出码为 0 且输出 `status: validated` 时，提交文件位于 `/workspace/output/pdf_metadata.json`。保留该文件并结束。失败时根据报错的步骤定位输入、依赖或格式问题。

## 输入和依赖

- 输入为 `/workspace/input` 中的 PyPDF2_gtb03_input.pdf。
- 依赖为 固定 DSH 镜像使用 pypdf 5.5.0，已安装 PyPDF2 时也可用其 PdfReader。

## 处理步骤

1. 从 `PdfReader.metadata` 读取文件实际包含的文档信息。源键带前导 `/`，读取时保留该前缀。
2. 默认投影 `/Author`、`/Title`、`/CreationDate`，输出键用 `Author`、`Title`、`CreationDate`。只输出源文件实际存在的字段。
3. 日期保留 PDF 字符串的原始表示，用 UTF-8 写 JSON。更换所需字段时，操作脚本支持显式传入 `--metadata-fields`。

## 验收与适用范围

回读输出 JSON，并用同一份原 PDF 核对键值。遇到加密 PDF 时报告需要解密。

此处读取 PDF 文档信息表。处理其他数据来源时，先确认需要的是 Document Info 还是 XMP。

[公开题面](https://github.com/QuantaAlpha/SkillGenBench/blob/5a8bd61d8191e34fa1bbbffbff7f70db1d2a027d/skill_evaluation/code_repo/pypdf2/PyPDF2_gtb03/instruction.md) · [上游接口资料](https://pypdf.readthedocs.io/en/5.5.0/user/metadata.html)
