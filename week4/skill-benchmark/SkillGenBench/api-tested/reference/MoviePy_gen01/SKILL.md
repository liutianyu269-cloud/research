---
name: letterbox-mp4-video
description: "等比缩放视频并生成居中的 640×480 H.264 MP4。"
---

# MoviePy_gen01

Run this workflow in the terminal as the first processing step.

```sh
python -B /workspace/skill/scripts/run_workflow.py MoviePy_gen01 video.py /workspace/input /workspace/output
```

When the command exits with code 0 and reports `"status": "validated"`, leave the artifact at `/workspace/output/resized_output.mp4` and finish. On failure, use the reported step to identify the input, dependency or output problem.

## Input and output

Read `MoviePy_gen01_input.webm`. Write `resized_output.mp4` at 640×480 with H.264. Preserve the full frame, duration, and any audio.

The workflow uses `moviepy==2.2.1` and the environment's FFmpeg/libx264.

## Procedure and checks

Scale uniformly to fit, center on a black canvas, keep the source frame rate and encode with libx264. Reopen the MP4 to check the 640×480 frame, padding and duration.

[Source notes](references/source-notes.md)
