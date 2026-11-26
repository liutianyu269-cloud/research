---
name: scikit-image-otsu-binary-mask
description: "在源图精度上求 Otsu 阈值，导出原尺寸的 8 位二值 PNG。"
---

# ScikitImage_gen06

在源图精度上求 Otsu 阈值，导出原尺寸的 8 位二值 PNG。

读完本页后先执行这条命令。它会依次检查输入、生成产物并回读验收。

```sh
python -B /workspace/skill/scripts/run_workflow.py ScikitImage_gen06 masks.py /workspace/input /workspace/output
```

命令退出码为 0 且输出 `status: validated` 时，提交文件位于 `/workspace/output/mask.png`。保留该文件并结束。失败时根据报错的步骤定位输入、依赖或格式问题。

## 输入和依赖

- 输入为 `/workspace/input` 中的 ScikitImage_gen06_input.png。
- 依赖为 scikit-image 0.25.2，Pillow，NumPy 2.2.6。

## 处理步骤

1. 读取灰度像素并保留位深，计算阈值前避免转换为 8 位。
2. 调用 `skimage.filters.threshold_otsu`。用 `灰度 > 阈值` 判断前景，等于阈值的像素属于背景。
3. 在写盘时把布尔掩膜转成 8 位 0 和 255。记录阈值和源图计算出的前景比例。

## 验收与适用范围

回读 PNG 检查尺寸、通道与像素范围，并从原图重算阈值验证逐像素一致。

以原图直方图计算阈值。面积比例只用于诊断。

[公开题面](https://github.com/QuantaAlpha/SkillGenBench/blob/5a8bd61d8191e34fa1bbbffbff7f70db1d2a027d/skill_evaluation/code_repo/scikitimage/ScikitImage_gen06/instruction.md) · [上游接口资料](https://scikit-image.org/docs/0.25.x/api/skimage.filters.html#skimage.filters.threshold_otsu)
