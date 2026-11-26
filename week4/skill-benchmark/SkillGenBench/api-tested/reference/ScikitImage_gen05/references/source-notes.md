# ScikitImage_gen05 的参考依据

素材页针对 NumPy 数组并指定八邻域，基线题使用目录中的二值 PNG。沿用原实验 Skill 的四邻域选择，并明示这个参数；标签数由输入决定。

产物检查。 回读 RGB PNG，检查尺寸、黑底和前景颜色。

素材页以 `.npy` 为输入并要求八邻域，基线评估包以二值 PNG 为输入。

[基线评估题面](https://github.com/QuantaAlpha/SkillGenBench/blob/5a8bd61d8191e34fa1bbbffbff7f70db1d2a027d/skill_evaluation/code_repo/scikitimage/ScikitImage_gen05/instruction.md) · [公开素材中的同题说明](https://github.com/QuantaAlpha/SkillGenBench/blob/5a8bd61d8191e34fa1bbbffbff7f70db1d2a027d/data_source/code_repo/scikitimage/tasks/ScikitImage_gen05/instruction.md) · [source.toml](https://github.com/QuantaAlpha/SkillGenBench/blob/5a8bd61d8191e34fa1bbbffbff7f70db1d2a027d/data_source/code_repo/scikitimage/shared/source.toml) · [源库接口文档](https://scikit-image.org/docs/0.25.x/api/skimage.measure.html#skimage.measure.label)
