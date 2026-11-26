---
name: pypdf-page-operations
description: 需要以 PDF 的原始页序提取现有文本层，或把多页 PDF 拆成多个单页 PDF 时使用。
---

# 逐页处理 PDF

将 PDF 以二进制打开，在读流有效期间用 `PdfReader(stream).pages` 按原文件顺序读取。

- 抽取文本时，对每页调用 `page.extract_text()`，保留页内换行并按顺序写成 UTF-8。内容完全是图片时，题目需要额外的 OCR 流程。要求阅读顺序或逐栏布局时，可用实际输入判断是否使用 `extraction_mode="layout"`。
- 拆页时，在每次循环新建 `PdfWriter()`，调用 `writer.add_page(page)` 和 `writer.write(path)`。目录中按 `page_1.pdf` 起算编号，处理时按编号排序。抽样回读输出确认每份一页，必要时逐页比对渲染和页面尺寸。

`scripts/process.py` 提供两个可独立导入的函数 `extract_text(reader, destination)` 与 `split_pages(reader, destination)`。课程使用 `python scripts/process.py CASE_ID INPUT_DIR OUTPUT_DIR`，输入目录放一个 PDF。抽取文件名为 `document.txt`，拆页写入新的 `pages/` 目录。

## 上游实现位置

- 官方 `pypdf` 仓库的 `pypdf/_reader.py` 中 `PdfReader` 读取文件。页列表通过 `pypdf/_doc_common.py` 的 `PdfDocCommon.pages` 暴露，`pypdf/_page.py` 的 `PageObject.extract_text` 解释页面文字操作。[抽取文本](https://pypdf.readthedocs.io/en/stable/user/extract-text.html)
- `pypdf/_writer.py` 的 `PdfWriter.add_page` 复制页及关联对象，`PdfWriter.write` 写出完整新文档。[复制与合并页面](https://pypdf.readthedocs.io/en/stable/user/merging-pdfs.html)
- GitTaskBench 的任务 ID 沿用 `PyPDF2`，它的仓库源码目录 `code_base/PyPDF2/` 内 Python 包已命名为 `pypdf`。[上游仓库](https://github.com/py-pdf/pypdf)
