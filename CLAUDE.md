# NJ Driver Quiz · Agent Notes

## 项目概览

新泽西州（NJ）驾照笔试中英对照练习站，静态 HTML/CSS/JS，部署在 Vercel。

## 仓库分布（重要）

| 角色 | 仓库 | 可见性 | 内容 |
|---|---|---|---|
| 代码 | [`gz2436/nj-driver-quiz`](https://github.com/gz2436/nj-driver-quiz) | **公开** | 站点代码、工具脚本、10 题样例 |
| 数据 | [`gz2436/nj-driver-quiz-data`](https://github.com/gz2436/nj-driver-quiz-data) | **私有** | 完整 567 题 + 解析 + 配图 |

**本地工作目录结构**：两仓嵌套——`data/` 是公开仓内一个独立的 git 仓库，远程指向私有数据仓。

```
/Users/gavincheung/NYU/Driver/        ← 公开仓 nj-driver-quiz
├── site/                             ← 静态站点
├── tools/                            ← 数据处理 Python 脚本
├── docs/                             ← 项目文档
├── sources/                          ← 源 docx/pdf（gitignored，本地保留）
├── data/                             ← 嵌套：私有仓 nj-driver-quiz-data
│   ├── .git/                            ← 独立 git
│   ├── questions.json                   ← 567 题（公开仓 .gitignore 排除）
│   ├── explanations.json
│   ├── images/
│   ├── topics.json                      ← 公开仓也有同份
│   ├── questions.sample.json            ← 10 题，公开仓里也有
│   ├── explanations.sample.json
│   └── README.md
├── .gitignore                        ← 公开仓忽略 questions.json 等
├── .vercelignore                     ← 部署时反过来包含完整数据
├── vercel.json
├── LICENSE                           ← MIT + CC-BY-NC
└── README.md
```

## 部署

- **平台**：Vercel
- **项目名**：`njq` → 线上 URL `njq.vercel.app`
- **方式**：手动 CLI（`vercel --prod` 从本地推），**不接 GitHub 自动部署**
- **原因**：自动部署会拉公开仓代码（无完整数据），导致线上变样例模式

## 数据私密化策略

1. `data/questions.json` 和 `data/explanations.json` 在 `.gitignore` → 不上 GitHub 公开仓
2. `.vercelignore` 不排除它们 → 上 Vercel 线上
3. 公开仓附带 `data/questions.sample.json`（10 题）作为 fallback
4. 前端 `fetchData()` 在 app.js 实现：先试真实文件，404 时回退到 sample，并在 `<html data-sample-mode="1">` 设标记触发顶部横条提示
5. `?sample=1` URL 参数可手动强制样例模式（自测用）
6. `vercel.json` 给 `/data/*.json` 加了 `X-Robots-Tag: noindex, nofollow, noarchive`，避免被搜索引擎索引

## 常见任务

### 我要改题库
```bash
cd data
# 编辑 questions.json
git add . && git commit -m "..." && git push  # 推到私有仓
cd ..
vercel --prod  # 重新部署
```

### 我要改代码
```bash
# 编辑 site/ 下的文件
git add . && git commit -m "..." && git push  # 推到公开仓
vercel --prod  # 重新部署
```

### 我要测样例模式（看 GitHub clone 用户的视角）
- 浏览器访问 `/site/index.html?sample=1`
- 或本地临时把 `data/questions.json` 改名 → 刷新 → 自动 fallback

### 我要找回丢失的题库
```bash
# 不小心删了 data/ 或换电脑
cd /Users/gavincheung/NYU/Driver
git clone git@github.com:gz2436/nj-driver-quiz-data.git data
```

## 协议

- **代码**（site/, tools/）：MIT
- **数据**（data/, docs/explanations.json 等）：CC BY-NC 4.0

详见公开仓 `LICENSE` 文件。
