# 人工提取与编排 Skill · 第四周 4.2

本分支归档 GitTaskBench 的 14 道正式题和 SkillGenBench 原 10 题的研究对照。试次使用 DeepSeek Flash＋DSH。两个基准各自保留原题面与评分口径。

- [逐题报告与实验结果](report.md)列出输入、产物、失败原因、请求次数和评分。
- [GitTaskBench](GitTaskBench)提供 14 题 API 实测 Skill、请求数、工作流及节点运行记录。14 条平台产物经原评分器复评均通过。在线实验记录无 Skill 9/14 和有 Skill 27/28，其中 5 题从请求达限到至少一次通过。
- [SkillGenBench](SkillGenBench)保存原 10 题以及 4 个受过 API 测试的策略快照。V1 只有 6 道实际请求过 API。论文版与 GitHub 参考版各通过 3 道，PDF 元数据是原基线有效的 0→1。
- [课程平台](platform)保存前后端补丁和平台运行脚本。平台运行脚本用来复现节点实际执行，与 API 实验 Skill 的冻结快照各有用途。基准输入使用数据集官方文件，公开归档只包含代码、题目清单和去敏后的结果。

## 对照课程示例

已核对课程后端 `dev_examples` 提交 `90c9a04`。课程样例用 `type: flow` 子节点引用原子流程 ID，由 `routes` 决定推进顺序。当前实现把这 24 条选题流程独立注册到 rsi-flow，按组合 ID 一次调度。Java 8 实跑 24/24 条，72/72 个 Skill 节点成功。24 个预期产物的 SHA-256 均与上轮已评分产物一致。详见[原生编排与复现](platform/native-orchestration.md)。 [课程后端示例](https://github.com/ymxiong/rsi-skill-spring-boot/tree/90c9a0464098c349cb8d021b604a1ca8b2496d83/core-flow/src/main/resources/flow)

## 复查现有记录

将 `platform/runtime` 下两个数据集目录放在项目 `work/skill-lab-v2` 下，将相应样例输入按 `catalog.json` 的 `inputRoot` 放置。参照 `platform/patches` 合入课程前后端，页面路径为 `/liutianyu-skill-lab/workflow`。导入数据集目录下的 `*-workflow.json` 并注册节点。`*-run.json` 记录当时的 Skill ID、节点状态和产物 SHA-256。复评分与 API 分开计，查看报告即可复查已有实验结果。
