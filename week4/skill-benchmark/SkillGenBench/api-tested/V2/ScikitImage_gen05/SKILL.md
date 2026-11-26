---
name: scikitimage-masks
description: Compute Otsu foreground masks and color 8-connected foreground regions reproducibly with scikit-image.
---

# scikit-image masks

Use Python 3 with scikit-image, NumPy and Pillow.

```sh
python scripts/masks.py CASE_ID INPUT_DIR OUTPUT_DIR
```

| Case | Operation | Artifact |
| --- | --- | --- |
| `ScikitImage_gen04` or `ScikitImage_gen06` | Threshold the source grayscale image using Otsu | `mask.png` |
| `ScikitImage_gen05` | Identify and color foreground components in the supplied binary mask | `labeled_components.png` |

Calculate the Otsu threshold at source precision. Mark intensities strictly
above it as 255 and the remainder as 0. Save the mask as a single-channel
8-bit PNG at source dimensions.

For component labeling, inspect the input subdirectory for a binary mask
with zero-valued background. Use 8-neighbor connectivity, leave the output
background black, and assign each foreground label a distinct RGB color.

[scikit-image threshold and labeling API](https://scikit-image.org/docs/stable/api/api.html)

## Workflow for this task

Identify input properties, then process, and validate the produced artifact. Run this bundled workflow directly. It checks the public inputs and reopens the output before finalizing it.

```sh
python -B /workspace/skill/scripts/run_workflow.py ScikitImage_gen05 masks.py /workspace/input /workspace/output
```

The required artifact is `/workspace/output/labeled_components.png`. Inspect the original input images for a binary mask with foreground and background. Check the result preserves size, black background and one distinct RGB color per foreground component.
Report whether the workflow succeeded. If a step fails, use its error to diagnose the input or runtime.
