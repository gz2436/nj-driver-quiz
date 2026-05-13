# NJ Driver Quiz · 新泽西驾照笔试练习

一个中英对照的新泽西州（NJ）驾照笔试练习站。题库整理自社区流传材料，已与官方
[NJ Driver Manual](https://www.nj.gov/mvc/pdf/license/drivermanual.pdf) 交叉校验。

## 功能 / Features

- **5 种练习模式**：完整练习、易错题、按分类、模拟考试（50 题）、错题本
- **题目解析**：参考官方手册或 N.J.S.A. 法条，含中英对照说明
- **同主题练习**：答完一题，看 2-3 道同主题的相关题
- **官方标志参考页**：直接收录 NJ 手册 p213-224 的标志页
- **本地进度持久化**：错题本、模考历史保存在浏览器 localStorage
- **键盘快捷键**：A-D / 1-4 / T-F / ← → / Enter
- **加权出题**：之前答错的题再次出现概率 ×2
- **TTS 朗读**：浏览器自带语音 API

## 免责声明 / Disclaimer

本站为个人学习工具，**非新泽西州 MVC 官方网站**，也不隶属于任何政府机构、律师事务所或培训机构。题目仅供学习参考，**不保证与实际考试相同**。答案以现行 NJ Driver Manual 及 NJ 州法规为准。本站不对题目准确性作任何明示或暗示的担保。通过本练习不保证通过实际考试。本站不收集任何个人数据，进度仅保存在你的浏览器。

This is a personal study tool, not affiliated with the NJ Motor Vehicle Commission, any government agency, law firm, or training program. Questions are for educational reference only. Answers follow the current NJ Driver Manual and NJ state law. No warranty of any kind, express or implied. Passing this practice does NOT guarantee passing the actual exam.

## 数据来源 / Data Sources

- 题库初始整理：[aiqiang.org 律师博客](https://www.aiqiang.org/post/nj-driverlicense-written-exam-practice)
- 答案校对：[NJ Driver Manual](https://www.nj.gov/mvc/pdf/license/drivermanual.pdf)（官方）
- 法条引用：[N.J.S.A.](https://www.njleg.state.nj.us/) 及 NJ MVC [DUI Penalty Table](https://www.nj.gov/mvc/license/duitable.html)

## 项目结构

```
.
├── sources/                    # 源文件（本地保留；不入 git）
│   ├── drivermanual.pdf
│   └── 美国新泽西驾照笔试题-*.docx / .pdf / .doc
├── docs/                       # 文档
│   ├── canonical_facts.md      # 58 条手册抽出的事实表（校验基线）
│   ├── CHANGELOG.md            # 题库变更日志
│   └── web_findings.md         # 网络交叉验证报告
├── tools/                      # 数据处理脚本
│   ├── parse_docx.py
│   ├── parse_pdf.py
│   ├── verify_facts.py
│   ├── extract_images.py
│   ├── cluster.py
│   └── reconcile.py
├── data/                       # 题库
│   ├── topics.json             # 分类元数据（入 git）
│   ├── questions.sample.json   # 10 题样例，开源演示用（入 git）
│   ├── explanations.sample.json # 配套样例解析（入 git）
│   ├── questions.json          # 完整 567 题，本地保留（不入 git）
│   ├── explanations.json       # 完整解析（不入 git）
│   └── images/                 # 题目配图（不入 git）
├── site/                       # 静态网站
│   ├── index.html
│   ├── quiz.html
│   ├── signs.html
│   ├── style.css
│   └── app.js
├── vercel.json
└── LICENSE                     # MIT (代码) + CC BY-NC 4.0 (内容)
```

## 本地开发 / Local Dev

```bash
# 任意静态服务器（仓库根目录）
npx live-server --port=8000 --no-browser --quiet
# 打开 http://localhost:8000/site/
```

注意 `fetch('../data/questions.json')` 需要 HTTP 协议下访问，**不能**用 `file://` 直接打开 `index.html`。

### 关于数据

仓库附带 10 道样例题（`data/questions.sample.json`）用于跑通代码、看 UI、提 PR。本地 clone 后直接运行会加载样例，页面顶部会出现「样例模式」横条。

线上完整版：[njq.vercel.app](https://njq.vercel.app)

数据结构以 `data/questions.sample.json` 为参考，主要来源为 [aiqiang.org](https://www.aiqiang.org/post/nj-driverlicense-written-exam-practice) 与 [NJ Driver Manual](https://www.nj.gov/mvc/pdf/license/drivermanual.pdf)。

## 重建题库 / Rebuild Question Bank

如需从源文件重新生成（修复 bug、补题等）：

```bash
python3 tools/parse_docx.py
python3 tools/parse_pdf.py
python3 tools/verify_facts.py
python3 tools/extract_images.py
python3 tools/cluster.py
python3 tools/reconcile.py
```

中间产物在 `/tmp/nj_build/`。最终输出在 `data/`。

源 docx/PDF 文件不在此仓库（版权未明），需自行准备。

## 部署 / Deploy

### Vercel（推荐）

```bash
# 安装 Vercel CLI
npm i -g vercel

# 在仓库根目录运行
vercel
```

`vercel.json` 已配置：站点根目录指向 `site/`，并把 `../data/*` 重写到 `data/*` 以便 quiz 页面正确加载数据。

### 其他

任何能 host 静态文件的平台均可（GitHub Pages、Netlify、Cloudflare Pages 等）。需要把 `site/` 作为站点根目录，并保证 `data/` 在它的父目录可访问；或者修改 `quiz.html` 里的 fetch 路径。

## 报错反馈 / Report Errors

通过站点底部的"报错"链接（Tally 表单）。**请勿**直接给作者发邮件。

## License

- **代码**（`tools/`、`site/`）：MIT
- **内容**（`data/`、`docs/canonical_facts.md`）：[CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/) — 非商业用途，必须署名

如需将题库用于商业用途请先联系。

## 已知限制 / Known Limitations

- 部分交通标志题在源文档中仅有 3 个选项（A/B/C），D 选项实际不存在 — 这是源数据限制，非解析 bug。
- 制动距离题和"打滑/爆胎"应对题在现行手册中未直接列出（属于驾考社区通用题），保留但不能用手册页码做权威引用。
- 个别原文档的合并问答未能完全拆分（已在 CHANGELOG 记录）。
- DUI 题答案已统一更新为 2019/12/01 后的现行法规。
