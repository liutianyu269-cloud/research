---
name: pillow-hsv-color-mask
description: "按 HSV 范围生成原尺寸的 8 位二值掩膜。"
---

# Pillow_gen01

按 HSV 范围生成原尺寸的 8 位二值掩膜。

读完本页后先执行这条命令。它会依次检查输入、生成产物并回读验收。

```sh
python -B /workspace/skill/scripts/run_workflow.py Pillow_gen01 images.py /workspace/input /workspace/output
```

命令退出码为 0 且输出 `status: validated` 时，提交文件位于 `/workspace/output/color_mask.png`。保留该文件并结束。失败时根据报错的步骤定位输入、依赖或格式问题。

## 输入和依赖

- 输入为 `/workspace/input` 中的 Pillow_gen01_input.jpg。
- 依赖为 Pillow 11.3.0，NumPy 2.2.6。

## 处理步骤

1. 先把原 JPEG 转成 RGB，再转 Pillow 的 HSV。Pillow 的 HSV 三个通道用 0–255 的整数表示。
2. 把 H 换算到角度，把 S 和 V 归一化。筛选 H 20°–40°、S 0.3–1.0、V 0.4–1.0，边界包含在内。
3. 匹配像素置 255，其余置 0。用 `L` 模式写 PNG，保持原图尺寸。

## 验收与适用范围

回读结果检查模式、尺寸和像素范围。按对应的 Pillow 字节阈值（H 为 15 到 28，S 至少 77，V 至少 102）逐像素复核。

不改变图像尺寸，也不使用去噪或形态学步骤填补颜色分割结果。

[公开题面](https://github.com/QuantaAlpha/SkillGenBench/blob/5a8bd61d8191e34fa1bbbffbff7f70db1d2a027d/skill_evaluation/code_repo/pillow/Pillow_gen01/instruction.md) · [上游接口资料](https://pillow.readthedocs.io/en/stable/handbook/concepts.html#modes)
