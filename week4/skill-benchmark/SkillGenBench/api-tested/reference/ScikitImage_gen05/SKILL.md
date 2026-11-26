---
name: color-connected-mask-components
description: "识别二值掩膜的前景连通区域，并为每一区域分配独立颜色。"
---

# ScikitImage_gen05

Run this workflow in the terminal as the first processing step.

```sh
python -B /workspace/skill/scripts/run_workflow.py ScikitImage_gen05 masks.py /workspace/input /workspace/output
```

When the command exits with code 0 and reports `"status": "validated"`, leave the artifact at `/workspace/output/labeled_components.png` and finish. On failure, use the reported step to identify the input, dependency or output problem.

## Input and output

Locate the binary PNG in `ScikitImage_gen05_input/`. Write `labeled_components.png` as an equally sized RGB PNG, with black background and a distinct color for each component.

The workflow uses `scikit-image==0.25.2`, `numpy==2.2.6`, Pillow.

## Procedure and checks

Use the PNG with zero background and one nonzero class. Label connected foreground via `skimage.measure.label` with four-neighbor connectivity, this package's choice for the original PNG task. Give each nonzero label a unique nonblack color. Keep the actual number of components.

[Source notes](references/source-notes.md)
