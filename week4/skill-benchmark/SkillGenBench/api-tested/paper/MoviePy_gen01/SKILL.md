---
name: letterbox-mp4-video
description: "等比缩放视频并生成居中的 640×480 H.264 MP4。"
---

# MoviePy_gen01

等比缩放视频并生成居中的 640×480 H.264 MP4。

读完本页后先执行这条命令。它会依次检查输入、生成产物并回读验收。

```sh
python -B /workspace/skill/scripts/run_workflow.py MoviePy_gen01 video.py /workspace/input /workspace/output
```

命令退出码为 0 且输出 `status: validated` 时，提交文件位于 `/workspace/output/resized_output.mp4`。保留该文件并结束。失败时根据报错的步骤定位输入、依赖或格式问题。

## 输入和依赖

- 输入为 `/workspace/input` 中的 MoviePy_gen01_input.webm。
- 依赖为 MoviePy 2.2.1，运行环境中的 FFmpeg/libx264。

## 处理步骤

1. 从 `VideoFileClip` 读取实际帧尺寸、FPS、时长和音轨状态。
2. 按 `min(640 / 宽, 480 / 高)` 计算缩放比例。先缩放画面，再把结果居中放入黑色画布。对于 16:9 的题目素材，画面为 640×360，上下补黑。
3. 用 `libx264` 编码 MP4，沿用源 FPS。源视频有音轨时写入 AAC。完成编码后才替换输出。

## 验收与适用范围

重新打开 MP4，检查输出尺寸、上下黑边以及和源视频的时长差。用题目的原评分器进一步检查编码。

保留完整画幅。缺少编解码器或无法打开素材时，按报错处理。

[公开题面](https://github.com/QuantaAlpha/SkillGenBench/blob/5a8bd61d8191e34fa1bbbffbff7f70db1d2a027d/skill_evaluation/code_repo/moviepy/MoviePy_gen01/instruction.md) · [上游接口资料](https://zulko.github.io/moviepy/reference/reference/moviepy.video.VideoClip.VideoClip.html)
