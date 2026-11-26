---
name: pillow-images
description: Produce HSV masks, transparency-preserving palette GIFs, and proportional downscales with Pillow.
---

# Pillow image transforms

Use Python 3 with Pillow and NumPy. Give the script the original input
directory and a separate output directory.

```sh
python scripts/images.py CASE_ID INPUT_DIR OUTPUT_DIR
```

| Case | Operation | Artifact |
| --- | --- | --- |
| `Pillow_gen01` | RGB → HSV, hue 20–40° with saturation ≥ 0.30 and value ≥ 0.40 | `color_mask.png` |
| `Pillow_gen02` | Indexed PNG → single-frame GIF, preserving the source transparent palette index | `output.gif` |
| `Pillow_gen04` | Proportionally downscale to width 512 using Lanczos and save as RGB PNG | `downscaled.png` |

Pillow's HSV channels are 8 bit. Convert the hue scale before applying
degree thresholds. For palette GIFs, keep the input palette and give the
encoder the source transparency index. For proportional sizing, compute the
height from the original dimensions before resizing the frame.

[Pillow image file formats](https://pillow.readthedocs.io/en/stable/handbook/image-file-formats.html)

## Workflow for this task

Identify input properties, then process, and validate the produced artifact. Run this bundled workflow directly. It checks the public inputs and reopens the output before finalizing it.

```sh
python -B /workspace/skill/scripts/run_workflow.py Pillow_gen01 images.py /workspace/input /workspace/output
```

The required artifact is `/workspace/output/color_mask.png`. Check the output is a same-size mode-L PNG and the pixel values are exactly 0 or 255. Check the hue degree-to-byte conversion before masking.
Report whether the workflow succeeded. If a step fails, use its error to diagnose the input or runtime.
