<p align="center">
  <strong>NJ Driver Quiz</strong>
  <br />
  <samp>新泽西驾照笔试 · 中英对照练习</samp>
</p>

<p align="center">
  <a href="https://njq.vercel.app/"><img src="https://img.shields.io/badge/Live_Site-njq.vercel.app-000000?style=for-the-badge&logo=vercel&logoColor=white" alt="Live Site" /></a>
</p>

<p align="center">
  <a href="https://developer.mozilla.org/docs/Web/HTML"><img src="https://img.shields.io/badge/HTML5-000000?style=for-the-badge&logo=html5&logoColor=white" alt="HTML5" /></a>
  <a href="https://developer.mozilla.org/docs/Web/CSS"><img src="https://img.shields.io/badge/CSS-000000?style=for-the-badge&logo=css&logoColor=white" alt="CSS" /></a>
  <a href="https://developer.mozilla.org/docs/Web/JavaScript"><img src="https://img.shields.io/badge/JavaScript-000000?style=for-the-badge&logo=javascript&logoColor=white" alt="JavaScript" /></a>
  <a href="https://vercel.com/"><img src="https://img.shields.io/badge/Vercel-000000?style=for-the-badge&logo=vercel&logoColor=white" alt="Vercel" /></a>
</p>

<br />

## About

中英对照的新泽西州（NJ）驾照笔试练习站，收录 567 题，部分题目配解析，另有官方标志参考页。纯前端静态站点，做题进度只存在你的浏览器；站点用 Vercel Analytics 统计匿名访问量，不使用 cookie。

> _A bilingual (中 / EN) practice site for the New Jersey driver knowledge test — 567 questions, some with explanations. Static and content-first; progress stays in your browser, and anonymous page views are counted with Vercel Analytics (no cookies)._

<br />

## Features

| | |
|---|---|
| **5 种练习模式** | 完整练习 · 易错题 · 按分类 · 模拟考试（50 题）· 错题本 |
| **中英对照解析** | 部分题目有双语说明，引用官方手册或 N.J.S.A. 法条（逐题核对进行中，进度见 `data/version.json`） |
| **同主题练习** | 答完一题，再看 2–3 道同主题相关题 |
| **官方标志参考页** | 收录 NJ 手册 p213–224 的交通标志页 |
| **本地进度持久化** | 错题本、模考历史存浏览器 `localStorage`，不上传 |
| **键盘快捷键** | A–D / 1–4 / T–F / ← → / Enter |
| **加权出题** | 之前答错的题再次出现概率 ×2 |
| **TTS 朗读** | 浏览器自带语音 API |

<br />

## Data Sources

| Source | Reference |
|--------|-----------|
| **题库整理** | [aiqiang.org 律师博客](https://www.aiqiang.org/post/nj-driverlicense-written-exam-practice) |
| **答案校对** | [NJ Driver Manual](https://www.nj.gov/mvc/pdf/license/drivermanual.pdf)（官方，2026 版）；更正记录见 `data/corrections.json` |
| **法条引用** | [N.J.S.A.](https://www.njleg.state.nj.us/) · [DUI Penalty Table](https://www.nj.gov/mvc/license/duitable.html) |

<br />

## Structure

```
.
├── site/                # 静态网站（HTML / CSS / JS）
│   ├── index.html · quiz.html · signs.html · cheatsheet.html
│   ├── style.css
│   └── app.js · index.js · quiz.js · ...
├── data/                # 完整题库（567 题 + 解析 + 配图）
│   ├── questions.json · explanations.json
│   ├── topics.json · images.json
│   └── images/
├── docs/                # 校验基线、变更日志、交叉验证报告
├── tools/               # 数据处理脚本（parse / verify / cluster ...）
├── sources/             # 第三方参考源文件（见 License）
├── vercel.json
└── LICENSE
```

<br />

## Local Dev

```bash
# 任意静态服务器（仓库根目录）
npx live-server --port=8000 --no-browser --quiet
```

打开 [localhost:8000/site/](http://localhost:8000/site/)。完整题库已随仓库开源，clone 后即可直接运行。

> `fetch('../data/questions.json')` 需在 HTTP 协议下访问，不能用 `file://` 直接打开 `index.html`。

<br />

## Question bank

`data/questions.json` is the source of truth and question ids are frozen. Hand corrections are logged in `data/corrections.json` (id, field, old value, new value, source page). Before committing a data change:

```bash
python3 tools/check_corrections.py
```

It fails if the bank has drifted from the log and refreshes `data/version.json`, which the site reads for its "N of 567 checked" line.

The parsing scripts in `tools/` (`parse_docx.py` … `reconcile.py`) built the first version of the bank from the source documents in May 2026. They renumber questions and would discard every later correction, so they are kept for reference only.

<br />

## Deploy

线上版托管在 Vercel：[njq.vercel.app](https://njq.vercel.app/)。仓库已自包含全部数据，接 Vercel GitHub 自动部署即可——连接本仓、生产分支设 `main`，push 即上线。`.vercelignore` 保证只部署 `site/` + `data/`。

```bash
# 手动部署（可选）
npm i -g vercel && vercel --prod
```

<br />

## License

| Scope | License |
|-------|---------|
| **代码** `site/` `tools/` | [MIT](LICENSE) |
| **内容** `data/` `docs/canonical_facts.md` | [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/) — 非商业、署名 |
| **`sources/`** | 第三方材料，版权归各自原作者，不在本项目自有许可范围内 |

如需将题库用于商业用途请先联系。

<br />

## Disclaimer

> 本站为个人学习工具，**非新泽西州 MVC 官方网站**，不隶属于任何政府机构、律师事务所或培训机构。题目仅供学习参考，不保证与实际考试相同，答案以现行 NJ Driver Manual 及 NJ 州法规为准。通过本练习不保证通过实际考试。
>
> This is a personal study tool, not affiliated with the NJ Motor Vehicle Commission or any agency. For educational reference only; passing this practice does NOT guarantee passing the actual exam.

<br />

## Known Limitations

- 部分交通标志题在源文档中仅有 3 个选项（A/B/C），D 选项实际不存在 —— 源数据限制，非解析 bug。
- 制动距离题和「打滑/爆胎」应对题在现行手册中未直接列出（属驾考社区通用题），保留但不以手册页码作权威引用。
- 个别原文档的合并问答未能完全拆分（已在 `docs/CHANGELOG.md` 记录）。
- DUI 题答案已统一更新为 2019/12/01 后的现行法规。
