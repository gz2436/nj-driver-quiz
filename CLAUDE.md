# NJ Driver Quiz · Agent Notes

新泽西州（NJ）驾照笔试中英对照练习站。静态 HTML/CSS/JS，部署在 Vercel。

## 仓库结构

单仓自包含：代码、完整题库、配图、参考源文件全在 [`gz2436/nj-driver-quiz`](https://github.com/gz2436/nj-driver-quiz) 一个公开仓里，clone 即可完整复现。

```
/Users/gavincheung/NYU/Driver/        ← nj-driver-quiz（单仓）
├── site/                             ← 静态站点（HTML/CSS/JS）
├── tools/                            ← 数据处理脚本
├── docs/                             ← 项目文档
├── sources/                          ← 第三方参考源文件（office 文档；官方大 PDF 不入库）
├── data/                             ← 完整题库
│   ├── questions.json                   ← 完整 567 题
│   ├── explanations.json                ← 解析
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
```bash
# 直接编辑 data/ 下的文件
git add data && git commit -m "..." && git push   # push 即自动部署
```

### 改代码
```bash
# 编辑 site/
git add site && git commit -m "..." && git push
```

### sources/ 里的官方大 PDF
`drivermanual.pdf`、`nj-chinese-manual-2025.pdf` 体积过大、不入库（`.gitignore` 已忽略）。需要时从 [NJ MVC](https://www.nj.gov/mvc/pdf/license/drivermanual.pdf) 重新下载到 `sources/`。

## 协议

- 代码（`site/`、`tools/`）：MIT
- 内容（`data/`、`docs/canonical_facts.md`）：CC BY-NC 4.0
- `sources/`：第三方材料，版权归各自原作者，仅作参考收录，不在本项目自有许可范围内。

详见 `LICENSE`。
