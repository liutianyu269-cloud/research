---
name: scikit-image-otsu-binary-mask
description: "在源图精度上求 Otsu 阈值，导出原尺寸的 8 位二值 PNG。"
---

# ScikitImage_gen06

Run this workflow in the terminal as the first processing step.

```sh
python -B /workspace/skill/scripts/run_workflow.py ScikitImage_gen06 masks.py /workspace/input /workspace/output
```

When the command exits with code 0 and reports `"status": "validated"`, leave the artifact at `/workspace/output/mask.png` and finish. On failure, use the reported step to identify the input, dependency or output problem.

## Input and output

Read `ScikitImage_gen06_input.png` at its source precision. Save `mask.png` as equally sized 8-bit grayscale PNG.

The workflow uses `scikit-image==0.25.2`, `numpy==2.2.6`, Pillow.

## Procedure and checks

Apply `threshold_otsu` before any conversion to 8-bit. Set foreground only where source values are strictly greater than the threshold. Recompute the rule against the source when checking the output.

[Source notes](references/source-notes.md)
