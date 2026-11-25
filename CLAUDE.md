# NJ Driver Quiz · Agent Notes

新泽西州（NJ）驾照笔试中英对照练习站。静态 HTML/CSS/JS，部署在 Vercel。

## 仓库结构

单仓自包含：代码、完整题库、配图、参考源文件全在 [`gz2436/nj-driver-quiz`](https://github.com/gz2436/nj-driver-quiz) 一个公开仓里，clone 即可完整复现。

```
~/NYU/nj-driver-quiz/                 ← nj-driver-quiz（单仓）
├── site/                             ← 静态站点（HTML/CSS/JS）
├── tools/                            ← 数据处理脚本
├── docs/                             ← 项目文档
├── sources/                          ← 第三方参考源文件（office 文档；官方大 PDF 不入库）
├── data/                             ← 完整题库
│   ├── questions.json                   ← 完整 567 题
│   ├── explanations.json                ← 解析
│   ├── corrections.json                 ← 手工更正记录（题号、原值、新值、出处）
│   ├── version.json                     ← 题库版本和核对进度（脚本生成）
│   ├── images.json                      ← 配图索引
│   ├── images/                          ← 题目配图
│   └── topics.json                      ← 分类元数据
├── .gitignore
├── .vercelignore                     ← 控制 CDN 只部署 site/ + data/
├── vercel.json
├── LICENSE                           ← MIT (代码) + CC-BY-NC (内容)
└── README.md
```

> 历史：题库曾单独放在私有仓 `nj-driver-quiz-data`，并配有一套 sample 回退机制；现已全部合并进本仓，那套机制已移除。

## 部署

- 平台：Vercel，项目 `njq` → 线上 [njq.vercel.app](https://njq.vercel.app)
- 方式：**GitHub 自动部署**。数据已在仓内，push 到 `main` 即自动上线。
- `.vercelignore` 保证 `sources/`、`docs/`、`tools/`、office 文档不进 CDN，只部署 `site/` + `data/`。
- 也可手动：根目录 `vercel --prod`。

## 数据加载

前端 `fetchData()`（`site/app.js`）就是一个普通 `fetch` JSON 的封装；`site/{index,quiz,cheatsheet}.js` 直接 fetch `../data/*.json`。无 sample / fallback / 样例横条逻辑。

## 常见任务

### 改题库
`data/questions.json` 是题库的唯一真源，题号（`id`）已冻结：用户的错题本和报错表单都按题号存。

1. 改题：直接改 `data/questions.json`，同一题的 `stem_en`/`stem_zh`、`options_en`/`options_zh` 和合并字段 `stem`/`options` 一起改（站点渲染分开的中英字段）。
2. 留记录：每处改动在 `data/corrections.json` 追加一条（题号、字段、原值、新值、出处页码或 MUTCD 条目）。题目核对过就写 `review` 字段：`verified`（带手册页码）、`not_in_manual`（另注出处）。
3. 提交前跑 `python3 tools/check_corrections.py`：它核对题库没有偏离更正记录，并刷新 `data/version.json`（免责声明里的“已核对 N / 567”读这个文件）。
4. 手册页码写“PDF 页 / 印刷页”，两者差 2；对照的是 2026 版（2026 年 4 月修订）。

`tools/` 里其余脚本（`parse_docx.py` 到 `reconcile.py`）是 2026-05 从源 docx 首次建库用的，路径写死、会重新编号并丢掉所有手工更正，只作历史参考。

### 改代码
编辑 `site/`。本地预览：仓库根目录起静态服务器，打开 `/site/index.html`。push 到 `main` 和正式部署先问 Gavin。

### sources/ 里的官方大 PDF
`drivermanual.pdf`、`nj-chinese-manual-2025.pdf` 体积过大、不入库（`.gitignore` 已忽略）。需要时从 [NJ MVC](https://www.nj.gov/mvc/pdf/license/drivermanual.pdf) 重新下载到 `sources/`。

## 协议

- 代码（`site/`、`tools/`）：MIT
- 内容（`data/`、`docs/canonical_facts.md`）：CC BY-NC 4.0
- `sources/`：第三方材料，版权归各自原作者，仅作参考收录，不在本项目自有许可范围内。

详见 `LICENSE`。
