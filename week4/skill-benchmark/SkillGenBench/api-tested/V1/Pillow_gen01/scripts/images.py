"""Transform benchmark images with Pillow."""

import argparse
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
from PIL import Image


def hsv_mask(source, output):
    hsv = np.asarray(source.convert("RGB").convert("HSV"), dtype=np.float64)
    hue_degrees = hsv[..., 0] * (360 / 255)
    saturation = hsv[..., 1] / 255
    brightness = hsv[..., 2] / 255
    selected = (hue_degrees >= 20) & (hue_degrees <= 40) & (saturation >= 0.3) & (brightness >= 0.4)
    Image.fromarray(selected.astype(np.uint8) * 255).save(output, format="PNG")


def palette_gif(source, output):
    transparent_index = source.info.get("transparency")
    if source.mode != "P" or not isinstance(transparent_index, int):
        raise ValueError("Expected a palette PNG with one transparent index")
    source.save(output, format="GIF", save_all=False, transparency=transparent_index, optimize=False)


def downscale_png(source, output):
    target_width = 512
    target_height = max(1, round(source.height * target_width / source.width))
    resized = source.convert("RGB").resize((target_width, target_height), Image.Resampling.LANCZOS)
    resized.save(output, format="PNG")


TASKS = {
    "Pillow_gen01": (".jpg", "color_mask.png", hsv_mask),
    "Pillow_gen02": (".png", "output.gif", palette_gif),
    "Pillow_gen04": (".jpg", "downscaled.png", downscale_png),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case_id", choices=TASKS)
    parser.add_argument("input_dir", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()

    extension, output_name, transform = TASKS[args.case_id]
    input_path = args.input_dir / f"{args.case_id}_input{extension}"
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with Image.open(input_path) as source, TemporaryDirectory(dir=args.output_dir) as temporary:
        staged_artifact = Path(temporary) / output_name
        transform(source, staged_artifact)
        staged_artifact.replace(args.output_dir / output_name)


if __name__ == "__main__":
    main()
