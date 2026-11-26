"""Transform benchmark WebM clips into MP4 using MoviePy 2."""

import argparse
from pathlib import Path
from tempfile import TemporaryDirectory

from moviepy import CompositeVideoClip, ImageClip, VideoFileClip, afx, vfx
import numpy as np
from PIL import Image, ImageDraw, ImageFont


def letterbox(source):
    target_width, target_height = 640, 480
    width, height = source.size
    scale = min(target_width / width, target_height / height)
    fitted_size = (round(width * scale), round(height * scale))
    return source.resized(new_size=fitted_size).with_background_color(
        size=(target_width, target_height), color=(0, 0, 0), pos="center"
    )


def fade_picture_and_sound(source):
    duration = 2
    if source.duration < 2 * duration:
        raise ValueError("The requested fade windows overlap")
    if source.audio is None:
        raise ValueError("The requested audiovisual fade requires a source audio track")
    return source.with_effects([
        vfx.FadeIn(duration), vfx.FadeOut(duration),
        afx.AudioFadeIn(duration), afx.AudioFadeOut(duration),
    ])


def watermark(source):
    text = "Sample Watermark"
    font = ImageFont.load_default(size=24)
    left, top, right, bottom = font.getbbox(text)
    overlay = Image.new("RGBA", (right - left, bottom - top))
    ImageDraw.Draw(overlay).text((-left, -top), text, fill="white", font=font)
    overlay = overlay.crop(overlay.getbbox())
    margin = 10
    position = (source.w - overlay.width - margin, source.h - overlay.height - margin)
    if min(position) < 0:
        raise ValueError("The source frame cannot fit the watermark")
    text_clip = ImageClip(np.asarray(overlay)).with_duration(source.duration).with_position(position)
    return CompositeVideoClip([source, text_clip], size=source.size)


TASKS = {
    "MoviePy_gen01": ("resized_output.mp4", letterbox),
    "MoviePy_gen02": ("faded_output.mp4", fade_picture_and_sound),
    "MoviePy_gen03": ("watermarked_output.mp4", watermark),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case_id", choices=TASKS)
    parser.add_argument("input_dir", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()

    filename, transform = TASKS[args.case_id]
    input_path = args.input_dir / f"{args.case_id}_input.webm"
    args.output_dir.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=args.output_dir) as temporary, VideoFileClip(str(input_path)) as source:
        staged_artifact = Path(temporary) / filename
        with transform(source) as result:
            result.write_videofile(
                str(staged_artifact), fps=source.fps, codec="libx264",
                audio=result.audio is not None, audio_codec="aac",
                temp_audiofile=str(Path(temporary) / "audio.m4a"),
                preset="veryfast", threads=2, logger=None,
            )
        staged_artifact.replace(args.output_dir / filename)


if __name__ == "__main__":
    main()
