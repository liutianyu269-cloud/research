---
name: faker-tabular-fixtures
description: 按指定列与行数生成合成 CSV，或保留原文的行结构并替换为合成文本。
---

# 用 Faker 生成合成 CSV

先从题面记录列名和顺序、行数、地区，以及需要唯一或相互关联的字段。用一个 `Faker(locale)` 实例绑定列名到 provider，每次构造一条记录。用户名使用 `user_name()`，占位邮件使用 `safe_email()`，公司记录可组合 `company()`、`address()`、`phone_number()`。题面指定字段之间有关联时，在单行生成函数中直接表达关联。

用 `csv.writer` 与 `encoding="utf-8", newline=""` 写盘。保留地址字段中的逗号和换行，交给 CSV 写入器处理引号。回读用 `csv.reader`，按记录计数。若需要可复现，固定 `seed_instance`、Faker 版本、地区和调用顺序。

`scripts/generate.py` 的 `generate_csv(destination, columns, count, locale=..., seed=...)` 接收按表头顺序排列的“列名 → provider 方法名”映射。课程命令 `python scripts/generate.py CASE_ID INPUT_DIR OUTPUT_DIR` 支持两道无输入的 CSV 生成题，以及 `Faker_03`。文本题按输入行计词，再用 `Faker.words()` 生成同等数量的合成词，并保留空行。

## 上游实现位置

- `faker/proxy.py` 的 `Faker.__getattr__` 和 `Faker.seed_instance` 负责代理 provider 调用和设置实例随机状态。[Faker 使用文档](https://faker.readthedocs.io/en/stable/)
- `faker/providers/internet/__init__.py` 的 `Provider.user_name` 和 `Provider.safe_email` 生成用户字段。[互联网 provider](https://faker.readthedocs.io/en/stable/providers/faker.providers.internet.html)
- `faker/providers/company/__init__.py`、`faker/providers/address/__init__.py`、`faker/providers/phone_number/__init__.py` 的 `Provider.company`、`Provider.address`、`Provider.phone_number` 提供公司字段。[公司](https://faker.readthedocs.io/en/stable/providers/faker.providers.company.html) · [地址](https://faker.readthedocs.io/en/stable/providers/faker.providers.address.html) · [电话](https://faker.readthedocs.io/en/stable/providers/faker.providers.phone_number.html)
