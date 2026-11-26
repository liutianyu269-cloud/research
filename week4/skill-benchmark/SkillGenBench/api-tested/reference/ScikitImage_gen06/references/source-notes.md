# ScikitImage_gen06 的参考依据

素材页要求去除二值掩膜的小斑点，基线原题要求 Otsu。沿用原图精度计算阈值，写盘时转换成 8 位二值掩膜。

产物检查。 逐像素复核 `原值 > Otsu 阈值`，记录实际前景比例。

素材页要求去斑，基线评估包要求对灰度图做 Otsu 分割。

[基线评估题面](https://github.com/QuantaAlpha/SkillGenBench/blob/5a8bd61d8191e34fa1bbbffbff7f70db1d2a027d/skill_evaluation/code_repo/scikitimage/ScikitImage_gen06/instruction.md) · [公开素材中的同题说明](https://github.com/QuantaAlpha/SkillGenBench/blob/5a8bd61d8191e34fa1bbbffbff7f70db1d2a027d/data_source/code_repo/scikitimage/tasks/ScikitImage_gen06/instruction.md) · [source.toml](https://github.com/QuantaAlpha/SkillGenBench/blob/5a8bd61d8191e34fa1bbbffbff7f70db1d2a027d/data_source/code_repo/scikitimage/shared/source.toml) · [源库接口文档](https://scikit-image.org/docs/0.25.x/api/skimage.filters.html#skimage.filters.threshold_otsu)
