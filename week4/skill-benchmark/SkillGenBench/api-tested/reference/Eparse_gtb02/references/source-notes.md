# Eparse_gtb02 的参考依据

借鉴 `df_serialize_table` 怎样携带文件名和工作表信息。官方工具包成一个 JSON 对象且只取首表，本题遍历原工作簿并逐行写独立 JSON 对象。

产物检查。 逐行核对字段、坐标和原始单元格值。

[基线评估题面](https://github.com/QuantaAlpha/SkillGenBench/blob/5a8bd61d8191e34fa1bbbffbff7f70db1d2a027d/skill_evaluation/code_repo/eparse/Eparse_gtb02/instruction.md) · [公开素材中的同题说明](https://github.com/QuantaAlpha/SkillGenBench/blob/5a8bd61d8191e34fa1bbbffbff7f70db1d2a027d/data_source/code_repo/eparse/tasks/Eparse_gtb02/instruction.md) · [export_first_table.py](https://github.com/QuantaAlpha/SkillGenBench/blob/5a8bd61d8191e34fa1bbbffbff7f70db1d2a027d/data_source/code_repo/eparse/shared/materials/tools/export_first_table.py) · [_eparse_core_compat.py](https://github.com/QuantaAlpha/SkillGenBench/blob/5a8bd61d8191e34fa1bbbffbff7f70db1d2a027d/data_source/code_repo/eparse/shared/materials/tools/_eparse_core_compat.py)
