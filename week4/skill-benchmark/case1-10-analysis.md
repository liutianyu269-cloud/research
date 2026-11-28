# 10 条人工编排案例

本次平台提交选取 7 条 GitTaskBench、3 条 SkillGenBench。GitTaskBench 覆盖请求达限后的恢复、页面处理复用和开销反例。SkillGenBench 覆盖结果提升、持平与评分规则冲突。平台目录只保留这 10 条，各数据集沿用自己的题面和评分口径。

人工先确定流程分工。文档先解析，信号与图像先识别输入，生成任务先定字段和数量。第二个节点处理输入，第三个节点回读产物验收。前端 JSON 记录每个节点的先后顺序和输入发自哪里。后端收到该 JSON 后把具体 Skill ID 解析为已注册的 RSI Flow ID，登记组合流，再按组合 ID 调度。个人此前确定了上述编排结构，AI 协助整理节点文件、实现加载与核验过程。

| 案例 | 数据集与题号 | 前端人工编排 | 后端原生配置 | 实际运行记录 |
| --- | --- | --- | --- | --- |
| 1 | GitTaskBench · `Eparse_02` | [case1.json](https://github.com/liutianyu269-cloud/rsi-data-platform/blob/main/app/liutianyu-skill-lab/workflow/cases/case1.json) | [case1.json](https://github.com/liutianyu269-cloud/rsi-data-spring-boot/blob/main/work/skill-lab-v2/cases/case1.json) | [result1.json](https://github.com/liutianyu269-cloud/rsi-data-spring-boot/blob/main/work/skill-lab-v2/results/result1.json) |
| 2 | GitTaskBench · `Eparse_03` | [case2.json](https://github.com/liutianyu269-cloud/rsi-data-platform/blob/main/app/liutianyu-skill-lab/workflow/cases/case2.json) | [case2.json](https://github.com/liutianyu269-cloud/rsi-data-spring-boot/blob/main/work/skill-lab-v2/cases/case2.json) | [result2.json](https://github.com/liutianyu269-cloud/rsi-data-spring-boot/blob/main/work/skill-lab-v2/results/result2.json) |
| 3 | GitTaskBench · `NeuroKit_02` | [case3.json](https://github.com/liutianyu269-cloud/rsi-data-platform/blob/main/app/liutianyu-skill-lab/workflow/cases/case3.json) | [case3.json](https://github.com/liutianyu269-cloud/rsi-data-spring-boot/blob/main/work/skill-lab-v2/cases/case3.json) | [result3.json](https://github.com/liutianyu269-cloud/rsi-data-spring-boot/blob/main/work/skill-lab-v2/results/result3.json) |
| 4 | GitTaskBench · `PDFPlumber_02` | [case4.json](https://github.com/liutianyu269-cloud/rsi-data-platform/blob/main/app/liutianyu-skill-lab/workflow/cases/case4.json) | [case4.json](https://github.com/liutianyu269-cloud/rsi-data-spring-boot/blob/main/work/skill-lab-v2/cases/case4.json) | [result4.json](https://github.com/liutianyu269-cloud/rsi-data-spring-boot/blob/main/work/skill-lab-v2/results/result4.json) |
| 5 | GitTaskBench · `Trafilatura_01` | [case5.json](https://github.com/liutianyu269-cloud/rsi-data-platform/blob/main/app/liutianyu-skill-lab/workflow/cases/case5.json) | [case5.json](https://github.com/liutianyu269-cloud/rsi-data-spring-boot/blob/main/work/skill-lab-v2/cases/case5.json) | [result5.json](https://github.com/liutianyu269-cloud/rsi-data-spring-boot/blob/main/work/skill-lab-v2/results/result5.json) |
| 6 | GitTaskBench · `PyPDF2_02` | [case6.json](https://github.com/liutianyu269-cloud/rsi-data-platform/blob/main/app/liutianyu-skill-lab/workflow/cases/case6.json) | [case6.json](https://github.com/liutianyu269-cloud/rsi-data-spring-boot/blob/main/work/skill-lab-v2/cases/case6.json) | [result6.json](https://github.com/liutianyu269-cloud/rsi-data-spring-boot/blob/main/work/skill-lab-v2/results/result6.json) |
| 7 | GitTaskBench · `Faker_01` | [case7.json](https://github.com/liutianyu269-cloud/rsi-data-platform/blob/main/app/liutianyu-skill-lab/workflow/cases/case7.json) | [case7.json](https://github.com/liutianyu269-cloud/rsi-data-spring-boot/blob/main/work/skill-lab-v2/cases/case7.json) | [result7.json](https://github.com/liutianyu269-cloud/rsi-data-spring-boot/blob/main/work/skill-lab-v2/results/result7.json) |
| 8 | SkillGenBench · `PyPDF2_gtb03` | [case8.json](https://github.com/liutianyu269-cloud/rsi-data-platform/blob/main/app/liutianyu-skill-lab/workflow/cases/case8.json) | [case8.json](https://github.com/liutianyu269-cloud/rsi-data-spring-boot/blob/main/work/skill-lab-v2/cases/case8.json) | [result8.json](https://github.com/liutianyu269-cloud/rsi-data-spring-boot/blob/main/work/skill-lab-v2/results/result8.json) |
| 9 | SkillGenBench · `Pillow_gen01` | [case9.json](https://github.com/liutianyu269-cloud/rsi-data-platform/blob/main/app/liutianyu-skill-lab/workflow/cases/case9.json) | [case9.json](https://github.com/liutianyu269-cloud/rsi-data-spring-boot/blob/main/work/skill-lab-v2/cases/case9.json) | [result9.json](https://github.com/liutianyu269-cloud/rsi-data-spring-boot/blob/main/work/skill-lab-v2/results/result9.json) |
| 10 | SkillGenBench · `ScikitImage_gen06` | [case10.json](https://github.com/liutianyu269-cloud/rsi-data-platform/blob/main/app/liutianyu-skill-lab/workflow/cases/case10.json) | [case10.json](https://github.com/liutianyu269-cloud/rsi-data-spring-boot/blob/main/work/skill-lab-v2/cases/case10.json) | [result10.json](https://github.com/liutianyu269-cloud/rsi-data-spring-boot/blob/main/work/skill-lab-v2/results/result10.json) |

10 条案例从课程前端逐条载入并点击运行，后端按 RSI Flow 执行，30 个节点全部完成。结果 JSON 的 `run` 记录这次浏览器触发的后端调度，`validation` 记录末节点的验收指标，`expectedArtifacts` 记录关键产物的文件名、字节数和 SHA-256。仓库保存运行证据，实际产物由复跑生成在本机的 `work/skill-lab-v2/platform/runs/`。下文无 Skill／有 Skill 数据来自历史 DeepSeek Flash＋DSH 实验，本轮仅复跑本地编排。GitTaskBench 的「达限」表示耗尽 6 个请求预算，当次无有效分数。

## 案例 1 · Eparse_02 · 导出非空单元格

- **输入与目标**　读取 `Eparse_02_input.xlsx`，按单元格输出 `eparse_cells.jsonl`。
- **人工调整**　`parse-workbook → gtb-excel-eparse → check-cell-jsonl`。先认出工作表和网格，再把 Eparse 提取的表内记录与全表非空坐标对齐，末节点逐行读取 JSON 并检查坐标、表头和值。
- **结果和原因**　输出 60 条记录。JSON Lines 让每条单元格记录独立解析，全表对齐使零散非空单元格也能进入输出。历史无 Skill 达限，有 Skill 两次各用了 4 个请求且均得 1 分。

## 案例 2 · Eparse_03 · 按工作表导出 JSON

- **输入与目标**　读取 `Eparse_03_input.xlsx`，输出按工作表组织的 `workbook.json`。
- **人工调整**　`gtb-inspect-eparse-03 → gtb-excel-workbook-json → gtb-verify-eparse-03`。沿用读取工作簿的能力，第二步改为按工作表分组写一份 JSON，末节点读回检查原坐标和值。
- **结果和原因**　覆盖 39 个非空单元格。与案例 1 共用输入识别和单元格读取思路，输出契约决定第二、三节点的选择。历史无 Skill 达限，有 Skill 两次各用了 4 个请求且均得 1 分。

## 案例 3 · NeuroKit_02 · ECG 峰位置

- **输入与目标**　读取 `NeuroKit_02_input_01.csv` 中的 ECG 信号，输出 `ecg_peaks.csv`。
- **人工调整**　`identify-signal → gtb-neurokit-signals → check-signal-csv`。确认信号列，用题目给定的 150 Hz 运行 NeuroKit，过滤未定位的事件后输出峰的整数采样点，最后按相同信号输入核对。
- **结果和原因**　输出 9 个 R 峰和 9 个 P 峰。采样率和「事件索引」的字段语义直接决定峰位置与输出格式。历史无 Skill 达限，有 Skill 两次各用了 4 个请求且均得 1 分。

## 案例 4 · PDFPlumber_02 · 前两页的表格

- **输入与目标**　读取 `PDFPlumber_02_input.pdf`，把前两页的所有表格写进 `tables.csv`。
- **人工调整**　`gtb-inspect-pdfplumber-02 → gtb-pdfplumber-tables → gtb-verify-pdfplumber-02`。先确认 PDF 页范围，再按页与表格顺序提取，显式保留表间分隔，最后按原 PDF 核查输出行。
- **结果和原因**　产物含 82 条表格数据行。按页枚举全部表格可以核对覆盖范围，分隔行保住表格边界。历史无 Skill 达限，有 Skill 一次达限、一次在 4 个请求内得 1 分，仍有达限风险。

## 案例 5 · Trafilatura_01 · 网页正文

- **输入与目标**　读取 `Trafilatura_01_input.txt` 指定网页的固定 HTML 快照，输出 `article.txt`。
- **人工调整**　`gtb-inspect-trafilatura-01 → gtb-web-article → gtb-verify-trafilatura-01`。先核对快照，定向提取文章主体，末节点读取正文并核对产物。
- **结果和原因**　固定快照得到 4,671 个正文字符。先固定输入消除了网页更新对实验的影响。提取节点依赖 HTML 解析环境，早期试次曾缺依赖。修复环境后的历史记录中，无 Skill 达限，有 Skill 在 3、4 个请求内均得 1 分。复跑时传入同一快照才能比较哈希。

## 案例 6 · PyPDF2_02 · 按页拆分 PDF

- **输入与目标**　读取 `PyPDF2_02_input.pdf`，在 `pages/` 下按原页序写每页的 PDF。
- **人工调整**　`gtb-inspect-pdf-pages → pypdf-page-operations → gtb-verify-pypdf2-02`。先记录页数，再让每个输出文件只写入一个页面，最后逐一打开且按原页序检查。
- **结果和原因**　生成 19 个单页 PDF。每页使用独立写入器，验收能识别漏页、重页和多页输出。历史两组都得 1 分，请求从无 Skill 的 6 次降到有 Skill 两次各 3 次。

## 案例 7 · Faker_01 · 生成合成用户

- **输入与目标**　无输入文件。生成 `users.csv`，含 100 行合成用户，列为 `Username`、`Email`。
- **人工调整**　`gtb-inspect-faker-schema → faker-tabular-fixtures → gtb-verify-faker-csv`。首节点固定字段与行数，生成时设置随机种子，末节点逐行检查字段和数量。
- **结果和原因**　生成 100 行且表头匹配。固定种子便于复现。历史两组都得 1 分，无 Skill 用 3 个请求，有 Skill 用 5、4 个。这个简单任务里，加载与调用 Skill 的开销没有换来得分提升。

## 案例 8 · PyPDF2_gtb03 · PDF 元数据

- **输入与目标**　读取 `PyPDF2_gtb03_input.pdf`，输出含作者、标题、创建日期的 `pdf_metadata.json`。
- **人工调整**　`parse-pdf → pdf-inspect → check-metadata-json`。确认 PDF 可读后，从文档信息字典取源字段，映射到题面 JSON 键，保留日期原始表示，最后把字段值与输入 PDF 对照。
- **结果和原因**　生成 `Author`、`Title`、`CreationDate` 三个字段。直接用源字段和原日期表示解决了旧版取值及表示差异。历史无 Skill 得 0 分，论文版和 GitHub 参考版的有 Skill 试次均得 1 分。

## 案例 9 · Pillow_gen01 · HSV 掩膜

- **输入与目标**　读取 `Pillow_gen01_input.jpg`，输出原尺寸单通道二值图 `color_mask.png`。
- **人工调整**　`identify-color-image → pillow-images → check-png-mask`。先核对原图尺寸与模式，将 Pillow 的 HSV 数值转换到题面角度和比例，按 H 20–40°、S 0.3–1、V 0.4–1 选像素，最后逐像素核验。
- **结果和原因**　输出 1200 × 837 的掩膜，前景约 5.87%。颜色单位换算与输出的 0/255 约定保证像素和格式一致。历史无 Skill 与两种有 Skill 版本均得 1 分，可作为持平对照。

## 案例 10 · ScikitImage_gen06 · Otsu 掩膜

- **输入与目标**　读取 `ScikitImage_gen06_input.png`，按原灰度精度计算 Otsu 阈值并输出 `mask.png`。
- **人工调整**　`identify-mask-input → scikitimage-masks → check-png-mask`。先读取灰度图，用源像素值计算阈值，再以「严格大于阈值」写入前景并核对每个像素。
- **结果和原因**　输出 200 × 200 的掩膜，前景 1.17%，本地题面规则验收通过。历史原评分器额外要求至少 5% 前景，因此无 Skill 和两种有 Skill 版本均为 0 分。保留这个冲突，以便评审分别核对算法和评分口径。

历史试次来源和逐题原评分记录见[第四周实验报告](https://github.com/liutianyu269-cloud/research/tree/week4-skill-defense/week4/skill-benchmark)。
