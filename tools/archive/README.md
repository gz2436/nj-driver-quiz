# tools/archive · 一次性脚本归档

这些脚本是 2026-05 题库初次构建期间用过的一次性数据清洗/审计工具。
现在 `data/questions.json` 已经稳定，这些不再需要运行。

保留它们的目的：万一以后要回溯**当时数据 lineage**（"这一条为什么被改/删？"），
或重跑当时的审计来对照新数据，能立刻找到原脚本。

如果未来确认不再需要回溯，可以整个目录删除。

## 当前管道（仍在用）

在父目录 `tools/`：

| 脚本 | 作用 |
|---|---|
| `parse_docx.py` | 从 docx 源解析题目 |
| `parse_pdf.py` | 解析交叉验证用 PDF |
| `verify_facts.py` | 对照 `docs/canonical_facts.md` 校验答案 |
| `extract_images.py` | 抽题目配图 + 渲染手册标志页 |
| `cluster.py` | 给题目打 topic 分类标签 |
| `reconcile.py` | 合并三路数据为最终 questions.json |

## 归档分类（13 个）

### 手工清洗工作流（7 个）

题库初版导出 xlsx 人工编辑，再导回 JSON。这个工作流已结束。

- `export_for_cleaning.py` — questions.json → xlsx 供人工编辑
- `autoclean_remaining.py` — 自动修复 xlsx 第 225 行后的常见问题
- `fix_systemic_issues.py` — 检测陈述句式卡片、跨行选项渗漏
- `fix_missing_stem_en.py` — 反查 docx 补缺失的英文译文
- `add_source_text_column.py` — 给 xlsx 加来源原文列方便对照
- `fix_fuzzy_duplicates.py` — 同步重复/常错标记
- `import_cleaned.py` — 清洗完的 xlsx 合并回 questions.json

### 历史审计（2 个）

跑出来的报告在 `docs/build_audit_2026-05-12.md`。

- `audit_completeness.py` — 对比解析结果 vs 源 docx，找漏题
- `audit_questions.py` — 检测已知解析问题（文字渗漏、选项被截断等）

### 已被合并/取代（4 个）

逻辑已并入当前管道，独立文件保留作参考。

- `full_extract.py` — 替代版整套解析器，最终未启用
- `fix_questions.py` — 解析后正则修复，逻辑已并入 `parse_docx.py`
- `recover_bilingual.py` — 中译文恢复，已并入 `parse_docx.py`
- `drop_broken.py` — 删除不可恢复条目，已并入 `reconcile.py`
