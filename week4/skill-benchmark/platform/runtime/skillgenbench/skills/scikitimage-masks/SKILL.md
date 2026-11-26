---
name: scikitimage-masks
description: Use when a grayscale image needs an Otsu foreground mask or a binary mask needs distinct colors for connected regions.
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
with zero-valued background. Use four-neighbor connectivity (`connectivity=1`)
so diagonal contact does not merge separate regions. Leave the output background
black and assign each foreground label a distinct RGB color. An input with one
foreground component requires one foreground color.

[scikit-image threshold and labeling API](https://scikit-image.org/docs/stable/api/api.html)
