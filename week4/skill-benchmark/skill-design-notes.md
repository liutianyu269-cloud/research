# 逐题提取、编排与版本依据

此处记录如何从公开仓库接口提取能力、怎样连接前后节点，以及每轮实际观察。原十题保留实际请求过 API 的版本。GitTaskBench 每题展示同输入对照。有效分为 0 或 1，达限为评分缺失。

## SkillGenBench 原十题

V1 先用显式脚本命令验证可执行性。V2 把识别、执行和校验收成同一入口。论文版把输出契约和确定性检查写细。GitHub 参考版利用公开接口和工具示例，按原基线题面交付。四批次实际 API 试次数为 6、20、10、10。

### PyPDF2_gtb03 · PDF 元数据

**提取**　跟踪 pypdf PdfReader.metadata 和 PDF 文档信息的 / 字段约定。作者、标题、日期从输入 PDF 实读，依赖 pypdf 5.5.0。

**编排**　识别 PDF → 投影 Author、Title、CreationDate 到 pdf_metadata.json → 读回 JSON，核对源键与原值。

节点顺序为 `parse-pdf → pdf-inspect → check-metadata-json`。

**改进依据与思路**　基线取值或日期表示不符。V2 固定字段与 JSON 交付。论文版明确源键前缀、缺失字段和原始日期。参考版借鉴公开写入示例的字段命名，将同一约定用于提取。三版有 Skill 均通过。

**实测**　历史无 Skill 0 ｜ V1 无 API 试次 ｜ V2 1、1 ｜ 论文版 1 ｜ GitHub参考版 1

### Eparse_gtb01 · 多工作簿报告

**提取**　从 Eparse 的 get_df_from_file 找到逻辑表读取接口，用 openpyxl 补全整张工作表网格。依赖 Eparse 0.9.2。

**编排**　盘点两份 XLSX 及各工作表 → 写完整 TXT → 校验文件名、表标题及数据覆盖。

节点顺序为 `parse-workbook → excel-eparse → check-text-report`。

**改进依据与思路**　V1 全文归一化仍与参考不同。V2 把全表覆盖纳入验收。论文版明确遍历全部工作表并保留零散内容。参考版从首表示例扩展到全量工作簿。另有离线修订保住首行和字面 NA，参考布局差异仍在。

**实测**　历史无 Skill 1† ｜ V1 0 ｜ V2 0、达限 ｜ 论文版 达限 ｜ GitHub参考版 0

### Eparse_gtb02 · 单元格 JSON Lines

**提取**　用 Eparse df_serialize_table 提取位置、值和表头上下文，从全表补齐未被逻辑表覆盖的非空单元格。

**编排**　读工作簿 → 按 sheet 与 Excel 坐标去重并逐行写 JSON 对象 → 逐行回读并核对字段和值。

节点顺序为 `parse-workbook → excel-eparse → check-cell-jsonl`。

**改进依据与思路**　V1 和 V2 多次达限。论文版收紧坐标、字段和覆盖规则。参考版借鉴文件与表字段，沿用题面的逐行 JSON。评分器把全文解析成单个 JSON，继续报 Extra data。

**实测**　历史无 Skill 0 ｜ V1 达限 ｜ V2 达限、达限 ｜ 论文版 0 ｜ GitHub参考版 0

### Pillow_gen01 · HSV 颜色掩膜

**提取**　从 Pillow 的 RGB→HSV 和 L 模式提取颜色筛选，依赖 Pillow、NumPy。

**编排**　检查 JPEG 和尺寸 → 按 H 20–40°、S 0.3–1、V 0.4–1 生成 0/255 单通道 PNG → 逐像素核对。

节点顺序为 `identify-color-image → pillow-images → check-png-mask`。

**改进依据与思路**　V1 已通过，V2 固定脚本入口与回读。论文版写明字节到角度、比例的转换与闭区间。参考素材同题号描述透明 GIF，本实验沿用原基线的 HSV 掩膜契约。

**实测**　历史无 Skill 1 ｜ V1 1 ｜ V2 1、1 ｜ 论文版 1 ｜ GitHub参考版 1

### ScikitImage_gen05 · 连通域着色

**提取**　从 skimage.measure.label 提取连通域标记，项目用四邻域。标签数由实际二值 PNG 决定。

**编排**　从子目录识别二值 PNG → 黑色背景、每个连通域独立 RGB → 回读核对像素和连通域。

节点顺序为 `identify-mask-input → scikitimage-masks → check-png-mask`。

**改进依据与思路**　V2 多次达限。论文版明确子目录和二值图筛选。参考素材是 NPY 八邻域，原任务沿用 PNG。离线进一步查明评分器漏扫子目录，正确子目录中的原图也只有一个连通域，评分规则却要求至少两种前景色。

**实测**　历史无 Skill 未评分 ｜ V1 无 API 试次 ｜ V2 达限、达限 ｜ 论文版 未评分 ｜ GitHub参考版 未评分

### ScikitImage_gen06 · Otsu 分割

**提取**　用 skimage.filters.threshold_otsu 计算阈值，保留灰度输入位深。

**编排**　识别灰度图 → 原值严格大于阈值置 255 → 回读掩膜并报告前景比例。

节点顺序为 `identify-mask-input → scikitimage-masks → check-png-mask`。

**改进依据与思路**　V2 已能产出掩膜。论文版明确原精度与严格比较，参考版沿用原题 Otsu 并增加逐像素核对。原图实际前景约 1.17%，评分器另设 5% 下限，几轮保持 0 分。

**实测**　历史无 Skill 0 ｜ V1 无 API 试次 ｜ V2 0、0 ｜ 论文版 0 ｜ GitHub参考版 0

### MoviePy_gen01 · 等比补黑边

**提取**　从 MoviePy 2.2.1 和 FFmpeg 提取读取、缩放、画布合成与 H.264 编码。

**编排**　读取 WebM、尺寸和时长 → 等比缩放并居中放入 640×480 黑底 → 回读尺寸、黑边、编码与时长。

节点顺序为 `identify-video → moviepy-video → check-letterbox-video`。

**改进依据与思路**　V2 两次已通过。论文版把缩放比例、音轨保留和时长检查写清。参考素材输出另有文件名，实验保留原评估约定 resized_output.mp4。

**实测**　历史无 Skill 1 ｜ V1 无 API 试次 ｜ V2 1、1 ｜ 论文版 1 ｜ GitHub参考版 1

### NeuroKit_gtb01 · EDA 汇总

**提取**　读 NeuroKit2 eda_process 的 SCR 峰、幅度和 tonic。采样率依据公开示例采用 250 Hz，作为显式假设。

**编排**　确认 EDA 数值列 → 计算平均幅度、峰数、tonic 总体标准差 → 核对一行三列 CSV。

节点顺序为 `identify-signal → neurokit-signals → check-signal-csv`。

**改进依据与思路**　V1、V2 已遵循汇总方向。论文版明确只从检测出的峰取幅度并说明 ddof=0。参考版读共享事件导出脚本后按题面做汇总。评分参考使用 SCR 事件数组，和题面三项统计口径不同。

**实测**　历史无 Skill 未评分 ｜ V1 0 ｜ V2 0、0 ｜ 论文版 0 ｜ GitHub参考版 达限

### NeuroKit_gtb02 · ECG 峰位置

**提取**　从 ecg_process 的事件字典提取 R/P 峰。使用题目给出的 150 Hz。

**编排**　检查 ECG 列和采样顺序 → 输出两组整数采样索引 → 核对两列列表和索引范围。

节点顺序为 `identify-signal → neurokit-signals → check-signal-csv`。

**改进依据与思路**　V1 显式区分峰标记与采样点位置。V2 固定事件位置输出。论文版过滤缺失值，参考版参考紧凑数组序列化。格式变得明确，实际计算索引仍与评分参考不同，因此未得分。

**实测**　历史无 Skill 0 ｜ V1 0 ｜ V2 0、0 ｜ 论文版 0 ｜ GitHub参考版 0

### NeuroKit_gtb03 · 呼吸指标

**提取**　从 rsp_process 提取呼吸速率和峰。实际文件有 RSP、无 EOG，公开匹配片段支持 100 Hz 的选择。

**编排**　根据实际列选择 RSP → 计算均值、峰时间和数量 → 验收秒数、峰数与三列列表。

节点顺序为 `identify-signal → neurokit-signals → check-signal-csv`。

**改进依据与思路**　早期版已处理信号缺列，论文版固定秒数换算和平均频率口径。参考版采用公开工具的峰时间思路，按原题写三列列表。原评分参考有标量，另有前期达限。

**实测**　历史无 Skill 未评分 ｜ V1 0 ｜ V2 0、0 ｜ 论文版 达限 ｜ GitHub参考版 0

† Eparse_gtb01 历史 1 分读取过评分参考，在干净增分统计中排除。

## GitTaskBench 14 道正式题

### Eparse_02 · 单元格 JSONL

**提取**　沿 Eparse 序列化接口找到存储行列、值和表头的方法。

**编排**　解析工作簿 → 写 eparse_cells.jsonl → 验收逐行 JSON、坐标与数据值。

节点顺序为 `parse-workbook → gtb-excel-eparse → check-cell-jsonl`。

**依据与取舍**　把文件名、字段、类型和完整覆盖写进脚本，减少临场试探。原评分离线复查字段匹配 420/480，通过阈值。

**实测**　无 Skill 达限 / 6 请求 → 有 Skill 1 / 4 请求、1 / 4 请求 ｜ 平台产物原评分 1

### Eparse_03 · 整份工作簿 JSON

**提取**　复用 Eparse 识别表格与 openpyxl 整表补读的思路。本题交付整份 JSON。

**编排**　识别工作表与网格 → 导出 workbook.json → 核对分页、行列坐标和值。

节点顺序为 `gtb-inspect-eparse-03 → gtb-excel-workbook-json → gtb-verify-eparse-03`。

**依据与取舍**　和 Eparse_02 共用读取思路，切换封装方式和验收。整份文件需要能一次被 JSON 解析器读取。

**实测**　无 Skill 达限 / 6 请求 → 有 Skill 1 / 4 请求、1 / 4 请求 ｜ 平台产物原评分 1

### NeuroKit_02 · ECG R/P 峰列表

**提取**　调用 NeuroKit2 的 ecg_process 与事件字典。题面固定 150 Hz。

**编排**　检查信号列 → 从事件索引写 ecg_peaks.csv → 核对两列和采样位置。

节点顺序为 `identify-signal → gtb-neurokit-signals → check-signal-csv`。

**依据与取舍**　脚本固定采样率与输出契约。相较临时搜索库接口，模型可直接调用。原评分复评两列均匹配。

**实测**　无 Skill 达限 / 6 请求 → 有 Skill 1 / 4 请求、1 / 4 请求 ｜ 平台产物原评分 1

### PDFPlumber_02 · 前两页全部表格

**提取**　用 pdfplumber 的 Page.extract_tables 枚举每页所有表格。

**编排**　识别 PDF → 遍历前两页、保序导出 tables.csv → 回读核对列和表间分隔。

节点顺序为 `gtb-inspect-pdfplumber-02 → gtb-pdfplumber-tables → gtb-verify-pdfplumber-02`。

**依据与取舍**　容易只提第一张表或漏第二页。明确多表与分页顺序。一次有 Skill 试次依旧达限，保留这条失败记录。

**实测**　无 Skill 达限 / 6 请求 → 有 Skill 达限 / 6 请求、1 / 4 请求 ｜ 平台产物原评分 1

### Trafilatura_01 · 固定网页正文

**提取**　从 Trafilatura 的正文提取接口抽取 HTML→正文，原页面固定成同一 HTML 快照。

**编排**　解析输入地址与 HTML → 输出 article.txt → 核验正文非空并复评相似度。

节点顺序为 `gtb-inspect-trafilatura-01 → gtb-web-article → gtb-verify-trafilatura-01`。

**依据与取舍**　首轮容器缺 lxml_html_clean，补为 0.4.6 后重做对照。成功证据对应修复后的同输入和依赖条件。

**实测**　无 Skill 达限 / 6 请求 → 有 Skill 1 / 3 请求、1 / 4 请求 ｜ 平台产物原评分 1

### Eparse_01 · 两份工作簿报告

**提取**　从 Eparse 读表接口抽取表区识别，读取原工作表来补足散落的内容。

**编排**　清点两份工作簿 → 写完整报告 eparse_report.txt → 核对名称、工作表与数据。

节点顺序为 `parse-workbook → gtb-excel-eparse → check-text-report`。

**依据与取舍**　提前交代目录遍历和完整输出。对照两组通过，有 Skill 平均请求下降。

**实测**　无 Skill 1 / 6 请求 → 有 Skill 1 / 4 请求、1 / 5 请求 ｜ 平台产物原评分 1

### PDFPlumber_01 · 首页文本

**提取**　使用 pdfplumber 的页对象和 extract_text。

**编排**　确认 PDF 可读取 → 只写第 1 页的 first_page.txt → 验收文本与首页一致。

节点顺序为 `gtb-inspect-pdfplumber-01 → gtb-pdfplumber-text → gtb-verify-pdfplumber-01`。

**依据与取舍**　页码作为参数约束。检查空文本层，避免把非法空文件算作成功。

**实测**　无 Skill 1 / 4 请求 → 有 Skill 1 / 3 请求、1 / 3 请求 ｜ 平台产物原评分 1

### PDFPlumber_03 · PDF 内邮箱

**提取**　复用页面文本提取，将匹配合法邮件地址和去重放进同一个处理脚本。

**编排**　识别 PDF → 遍历页并写 emails.txt → 对照原文核对地址、重复项。

节点顺序为 `gtb-inspect-pdfplumber-03 → gtb-pdfplumber-emails → gtb-verify-pdfplumber-03`。

**依据与取舍**　核验从文件中提取的地址。固定遍历和去重，减少漏页或重复。

**实测**　无 Skill 1 / 6 请求 → 有 Skill 1 / 4 请求、1 / 4 请求 ｜ 平台产物原评分 1

### PyPDF2_01 · 全文文字

**提取**　从 pypdf PdfReader.pages 与 PageObject.extract_text 抽取页读取能力。

**编排**　确认页数 → 按源页顺序写 document.txt → 比较内容和覆盖。

节点顺序为 `gtb-inspect-pdf-pages → pypdf-page-operations → gtb-verify-pypdf2-01`。

**依据与取舍**　同一页读取能力可被拆分任务复用。导出时明确全文范围和顺序。

**实测**　无 Skill 1 / 6 请求 → 有 Skill 1 / 4 请求、1 / 5 请求 ｜ 平台产物原评分 1

### PyPDF2_02 · 逐页拆分

**提取**　复用 PdfReader，并用 PdfWriter.add_page 保存单页 PDF。

**编排**　读取页数 → 每页写一个 PDF 到 pages → 回读份数、单页约束和原始顺序。

节点顺序为 `gtb-inspect-pdf-pages → pypdf-page-operations → gtb-verify-pypdf2-02`。

**依据与取舍**　输出由文本切换为目录，验收从文本准确度切换为文件与页面对应关系。

**实测**　无 Skill 1 / 6 请求 → 有 Skill 1 / 3 请求、1 / 3 请求 ｜ 平台产物原评分 1

### NeuroKit_01 · EDA 事件

**提取**　从 NeuroKit2 eda_process 取 SCR Onsets、Peaks、Height，采样率 250 Hz。

**编排**　确认 EDA 通道 → 写 eda_events.csv 三列事件数组 → 检查对齐与类型。

节点顺序为 `gtb-inspect-neurokit-01 → gtb-neurokit-scr-events → gtb-verify-neurokit-01`。

**依据与取舍**　这个 GitTaskBench 任务要求事件数组。SkillGenBench 同类题要求统计量，复用信号处理后按各自题面导出。

**实测**　无 Skill 1 / 6 请求 → 有 Skill 1 / 5 请求、1 / 3 请求 ｜ 平台产物原评分 1

### Faker_03 · 文本替换

**提取**　从 Faker 取合成文本能力，把行结构当作输入契约。

**编排**　读源文件行结构 → 生成并写 fake_text.txt → 核对行数和实际替换。

节点顺序为 `gtb-inspect-faker-03 → gtb-faker-text → gtb-verify-faker-03`。

**依据与取舍**　保留行的结构供评分器读取，避免把合成文本写成说明或代码。

**实测**　无 Skill 1 / 5 请求 → 有 Skill 1 / 3 请求、1 / 3 请求 ｜ 平台产物原评分 1

### Faker_01 · 用户数据合成

**提取**　借用 Faker 的用户名和邮箱 provider，任务无输入文件。

**编排**　确认 100 行以及 Username/Email 列 → 写 users.csv → 回读并校验行数和字段。

节点顺序为 `gtb-inspect-faker-schema → faker-tabular-fixtures → gtb-verify-faker-csv`。

**依据与取舍**　无 Skill 已通过，使用 Skill 的平均请求反而增加。能力适合跨任务复用，本题没有观察到收益。

**实测**　无 Skill 1 / 3 请求 → 有 Skill 1 / 5 请求、1 / 4 请求 ｜ 平台产物原评分 1

### Faker_02 · 公司数据合成

**提取**　复用 Faker 表格生成方法，切换到公司、地址、电话号码 provider。

**编排**　确认 5 行和字段规范 → 写 companies.csv → 回读检查表头、记录数和字段可用。

节点顺序为 `gtb-inspect-faker-schema → faker-tabular-fixtures → gtb-verify-faker-csv`。

**依据与取舍**　结构与 Faker_01 一致，主要换字段和行数。两组都通过，使用 Skill 的平均请求略增。

**实测**　无 Skill 1 / 3 请求 → 有 Skill 1 / 4 请求、1 / 3 请求 ｜ 平台产物原评分 1
