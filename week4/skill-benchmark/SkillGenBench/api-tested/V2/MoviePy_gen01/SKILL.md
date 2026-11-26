---
name: moviepy-video
description: Resize video with centered black padding, add synchronized audiovisual fades, or overlay a persistent watermark with MoviePy.
---

# MoviePy video transforms

Use Python 3 with MoviePy 2.2, Pillow and an FFmpeg binary supplied by
`imageio-ffmpeg` or configured in MoviePy.

```sh
python scripts/video.py CASE_ID INPUT_DIR OUTPUT_DIR
```

| Case | Operation | Artifact |
| --- | --- | --- |
| `MoviePy_gen01` | Fit inside a black 640×480 canvas, preserving aspect ratio | `resized_output.mp4` |
| `MoviePy_gen02` | Fade picture and audio over the first and final two seconds | `faded_output.mp4` |
| `MoviePy_gen03` | Full-duration white text at font size 24, inset 10 px from the bottom-right | `watermarked_output.mp4` |

MoviePy 2.x uses `resized`, `with_effects` and `with_position`. Retain
the source frame rate and use H.264/AAC. Match the audio and visual fade
windows and keep the source clip open until encoding completes. Verify
frame dimensions and duration by reopening the encoded MP4.

[MoviePy reference](https://zulko.github.io/moviepy/reference/reference/moviepy.html)

## Workflow for this task

Identify input properties, then process, and validate the produced artifact. Run this bundled workflow directly. It checks the public inputs and reopens the output before finalizing it.

```sh
python -B /workspace/skill/scripts/run_workflow.py MoviePy_gen01 video.py /workspace/input /workspace/output
```

The required artifact is `/workspace/output/resized_output.mp4`. Open the encoded file; check its 640x480 frame size, original duration, centered black padding, and H.264 encoding.
Report whether the workflow succeeded. If a step fails, use its error to diagnose the input or runtime.
