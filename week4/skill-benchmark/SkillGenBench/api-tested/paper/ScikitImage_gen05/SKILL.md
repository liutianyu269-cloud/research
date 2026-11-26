---
name: color-connected-mask-components
description: "识别二值掩膜的前景连通区域，并为每一区域分配独立颜色。"
---

# ScikitImage_gen05

识别二值掩膜的前景连通区域，并为每一区域分配独立颜色。

读完本页后先执行这条命令。它会依次检查输入、生成产物并回读验收。

```sh
python -B /workspace/skill/scripts/run_workflow.py ScikitImage_gen05 masks.py /workspace/input /workspace/output
```

命令退出码为 0 且输出 `status: validated` 时，提交文件位于 `/workspace/output/labeled_components.png`。保留该文件并结束。失败时根据报错的步骤定位输入、依赖或格式问题。

## 输入和依赖

- 输入为 `/workspace/input` 中的 ScikitImage_gen05_input/ 下的二值 PNG。
- 依赖为 scikit-image 0.25.2，Pillow，NumPy 2.2.6。

## 处理步骤

1. 检查原题子目录中的 PNG。用可转成单通道、只有零与一个正值的条件确定二值掩膜。多个候选时报告歧义。
2. 取非零像素为前景，用 `skimage.measure.label(..., background=0, connectivity=1)` 标记。二维连接方式采用四邻域。
3. 给每个非零标签映射唯一非黑 RGB，标签 0 固定为黑。保存同尺寸的 RGB PNG。

## 验收与适用范围

回读 PNG 检查 RGB 模式、黑色背景和非空前景；处理步骤输出从输入算出的实际区域数与尺寸。

当输入只有一个实际连通区域时，输出保存一个前景颜色。

[公开题面](https://github.com/QuantaAlpha/SkillGenBench/blob/5a8bd61d8191e34fa1bbbffbff7f70db1d2a027d/skill_evaluation/code_repo/scikitimage/ScikitImage_gen05/instruction.md) · [上游接口资料](https://scikit-image.org/docs/0.25.x/api/skimage.measure.html#skimage.measure.label)
