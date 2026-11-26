---
name: pillow-hsv-color-mask
description: "按 HSV 范围生成原尺寸的 8 位二值掩膜。"
---

# Pillow_gen01

Run this workflow in the terminal as the first processing step.

```sh
python -B /workspace/skill/scripts/run_workflow.py Pillow_gen01 images.py /workspace/input /workspace/output
```

When the command exits with code 0 and reports `"status": "validated"`, leave the artifact at `/workspace/output/color_mask.png` and finish. On failure, use the reported step to identify the input, dependency or output problem.

## Input and output

Read `Pillow_gen01_input.jpg`. Save `color_mask.png` as PNG mode L at original dimensions with pixel values 0 or 255.

The workflow uses `Pillow==11.3.0`, `numpy==2.2.6`.

## Procedure and checks

Convert RGB to HSV and account for Pillow's 8-bit channel encoding. Select hue 20°–40°, saturation 0.3–1 and value 0.4–1, inclusively. Check the PNG by recomputing the same selection from the input.

[Source notes](references/source-notes.md)
