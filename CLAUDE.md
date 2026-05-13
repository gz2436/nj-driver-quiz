# NJ Driver Quiz · Agent Notes

新泽西州（NJ）驾照笔试中英对照练习站。静态 HTML/CSS/JS，部署在 Vercel。

## 仓库结构

代码和数据分两个仓维护：

| 仓库 | 内容 |
|---|---|
| [`gz2436/nj-driver-quiz`](https://github.com/gz2436/nj-driver-quiz)（本仓） | 站点代码、工具脚本、10 题样例 |
| `gz2436/nj-driver-quiz-data` | 完整题库 + 解析 + 配图 |

本地工作目录里，`data/` 是独立 git 仓库，远程指向数据仓。

```
/Users/gavincheung/NYU/Driver/        ← 本仓 nj-driver-quiz
├── site/                             ← 静态站点
├── tools/                            ← 数据处理脚本
├── docs/                             ← 项目文档
├── sources/                          ← 源 docx/pdf（本地保留）
├── data/                             ← 嵌套：nj-driver-quiz-data
│   ├── .git/
│   ├── questions.json                   ← 完整题库
│   ├── explanations.json
│   ├── images/
│   ├── topics.json
│   ├── questions.sample.json            ← 10 题样例
│   ├── explanations.sample.json
│   └── README.md
├── .gitignore                        ← 排除 questions.json 等大文件
├── .vercelignore                     ← 部署时反过来包含完整数据
├── vercel.json
├── LICENSE                           ← MIT + CC-BY-NC
└── README.md
```

## 部署

- 平台：Vercel
- 项目：`njq` → 线上 [njq.vercel.app](https://njq.vercel.app)
- 方式：手动 CLI `vercel --prod` 从本地推
- 注意：不接 GitHub 自动部署（自动部署只能拉本仓内容，不含 `data/` 完整文件）

## 数据加载策略

1. `.gitignore` 排除 `data/questions.json` 和 `data/explanations.json`
2. `.vercelignore` 不排除它们 → 上传到线上
3. 本仓附带 `data/questions.sample.json`（10 题）作为 fallback
4. 前端 `fetchData()`（在 app.js）：先试真实文件，404 时回退到 sample，并在 `<html data-sample-mode="1">` 设标记触发顶部横条
5. `?sample=1` URL 参数可手动强制样例模式（自测用）

## 常见任务

### 改题库
```bash
cd data
# 编辑
git add . && git commit -m "..." && git push
cd ..
vercel --prod
```

### 改代码
```bash
# 编辑 site/
git add . && git commit -m "..." && git push
vercel --prod
```

### 测样例模式
浏览器访问 `/site/index.html?sample=1`，或本地把 `data/questions.json` 临时改名后刷新。

### 找回 data/
```bash
cd /Users/gavincheung/NYU/Driver
git clone git@github.com:gz2436/nj-driver-quiz-data.git data
```

## 协议

- 代码（site/、tools/）：MIT
- 内容（data/、docs/canonical_facts.md）：CC BY-NC 4.0

详见 `LICENSE`。
