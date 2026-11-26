"""Threshold and annotate benchmark masks with scikit-image."""

import argparse
import json
import os
from pathlib import Path
import sys
from tempfile import TemporaryDirectory


def grayscale_pixels(image):
    import numpy as np

    if image.mode == "P":
        image = image.convert("RGBA")
    values = np.asarray(image)
    if values.ndim == 2:
        return values
    if image.mode in {"RGB", "RGBA"}:
        if image.mode == "RGBA" and not (values[..., 3] == 255).all():
            return None
        if (values[..., :3] == values[..., :1]).all():
            return values[..., 0]
    return None


def color_connected_components(input_root, output_path):
    import numpy as np
    from PIL import Image
    from skimage.measure import label

    input_directory = input_root / "ScikitImage_gen05_input"
    candidates = []
    for candidate in sorted(input_directory.iterdir()):
        if not candidate.is_file() or candidate.suffix.lower() != ".png":
            continue
        with Image.open(candidate) as image:
            gray = grayscale_pixels(image)
            if gray is not None:
                values = np.unique(gray)
                # A binary mask has a zero background and a nonzero foreground.
                if len(values) == 2 and values[0] == 0 and values[1] > 0:
                    candidates.append((candidate, gray != 0))
    if len(candidates) != 1:
        raise ValueError(f"Expected one binary PNG mask with background and foreground, found {len(candidates)}")

    source, foreground = candidates[0]
    labels, count = label(foreground, background=0, connectivity=1, return_num=True)
    if count > 0xFFFFFF:
        raise ValueError("There are more foreground regions than distinct nonblack RGB colors")
    component_ids = np.arange(count + 1, dtype=np.uint32)
    # An odd multiplier is one-to-one modulo 2**24, leaving label zero black.
    colors = (component_ids * 0x9E3779) & 0xFFFFFF
    palette = np.column_stack((colors >> 16, (colors >> 8) & 255, colors & 255)).astype(np.uint8)
    rendered = palette[labels]
    Image.fromarray(rendered).save(output_path, format="PNG")
    with Image.open(output_path) as saved:
        if saved.mode != "RGB" or not np.array_equal(np.asarray(saved), rendered):
            raise ValueError("The saved RGB mask differs from the component colors computed from the input")
    return {"input": source.name, "components": int(count), "size": list(foreground.shape[::-1])}


def make_otsu_mask(input_root, output_path, case_id):
    import numpy as np
    from PIL import Image
    from skimage.filters import threshold_otsu

    with Image.open(input_root / f"{case_id}_input.png") as source:
        gray = grayscale_pixels(source)
    if gray is None:
        raise ValueError("Otsu input must be a grayscale image")
    # Estimate the threshold before converting to 8-bit output.
    threshold = threshold_otsu(gray)
    foreground = gray > threshold
    Image.fromarray(foreground.astype(np.uint8) * 255).save(output_path, format="PNG")
    return {
        "size": list(foreground.shape[::-1]),
        "threshold": float(threshold),
        "foreground_fraction": float(foreground.mean()),
    }


TASKS = {
    "ScikitImage_gen05": "labeled_components.png",
    "ScikitImage_gen04": "mask.png",
    "ScikitImage_gen06": "mask.png",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task_id", choices=TASKS)
    parser.add_argument("input_root", type=Path)
    parser.add_argument("output_root", type=Path)
    args = parser.parse_args()

    filename = TASKS[args.task_id]
    args.output_root.mkdir(parents=True, exist_ok=True)
    try:
        with TemporaryDirectory(dir=args.output_root) as temporary:
            pending_output = Path(temporary) / filename
            if args.task_id == "ScikitImage_gen05":
                summary = color_connected_components(args.input_root, pending_output)
            else:
                summary = make_otsu_mask(args.input_root, pending_output, args.task_id)
            os.replace(pending_output, args.output_root / filename)
    except (OSError, ValueError, ImportError) as error:
        print(f"{args.task_id}: {error}", file=sys.stderr)
        return 1

    print(json.dumps({"task_id": args.task_id, "output": filename, **summary}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
