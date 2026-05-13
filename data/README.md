# NJ Driver Quiz · Question Bank (Private)

> 此仓库是 [gz2436/nj-driver-quiz](https://github.com/gz2436/nj-driver-quiz)（公开代码仓）的**私有数据仓**。

## 仓库定位

- **公开仓 `nj-driver-quiz`**：HTML/CSS/JS 站点代码 + 10 题样例 + 工具脚本，MIT 协议
- **本仓 `nj-driver-quiz-data`（私有）**：完整 567 题中英对照题库 + 解析 + 配图

两仓配合使用：
- 公开仓负责站点 UI / 模式逻辑 / sample fallback
- 本仓负责实际题目内容，仅用于作者本地开发 + Vercel 线上部署
- 线上访客能做完整 567 题，但 GitHub 公开仓只能看到 10 题样例

## 文件清单

```
data/
├── questions.json          # 567 题，主数据
├── explanations.json       # 解析 + 知识卡 + 法条引用
├── topics.json             # 分类元数据（也在公开仓里有同份）
├── images/                 # 题目配图
│   ├── img_complete_*.jpg/png       # NJ Driver Manual 截图
│   ├── img_mistakes_*.jpeg/png      # 易错题独有图
│   └── manual_signs/                # 手册第 213-224 页交通标志
└── README.md               # 本文件
```

## 数据结构

每道题（`questions.json` 一条记录）：
```json
{
  "id": 123,
  "stem": "If the road is wet, you should: 在湿滑路面上你应该",
  "type": "multi",
  "options": [
    "Speed up 加速",
    "Slow down 减速",
    "..."
  ],
  "answer": "B",
  "topics": ["skid_blowout", "stopping_distance"],
  "explanation_key": "skid_recovery",
  "is_common_mistake": false,
  "stem_img": "img_complete_042.jpg",
  "is_duplicate_of": null
}
```

字段说明：
- `id`：1..567 连续编号，与"第 N 题"显示一致
- `type`：`multi`（四选一）/ `tf`（判断题，options 只用前 2 个）
- `topics`：分类 key，对应 topics.json
- `explanation_key`：可空，对应 explanations.json
- `is_common_mistake`：标记易错题（用于易错题模式）
- `stem_img`：可空，题目配图文件名
- `is_duplicate_of`：可空，重复题指向另一条 id，前端会自动 dedup

## 维护

```bash
# 拉最新
git pull

# 改完之后
git add .
git commit -m "Fix Q123 explanation"
git push
```

## 协议

题库内容采用 CC BY-NC 4.0 协议（详见公开仓 LICENSE）。整理者：[@gz2436](https://github.com/gz2436)。
