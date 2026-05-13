# 审计报告

## 概览

- questions.json 总题数: **746**
- 源 complete 识别题段: **626** (MC 带答案 + 空答案 + Q&A)
- 源 mistakes 识别题段: **123**

| 项 | 数量 |
|---|---|
| 漏题（源里有 / 我们没对应） | 3 |
| 多提（我们有 / 源里无对应题段） | 0 |
| 答案字母不一致（MC） | 0 |
| 源里就是空答案（()） | 2 |
| Q&A 答案文本不一致 | 0 |
| complete 内部重复 | 5 |

## 漏题清单（3）

- complete/pi=36 `C-list70.8` kind=mc  text=`The minimum age for a basic driver license is: 获取驾照最小年龄为：(B) A. 16B. 17C. 18D. 1`
- complete/pi=527 `C-list83.63` kind=mc  text=`The written test pass grade is:  笔试的合格分数线是：(D) A. 65B. 70C. 85D. 80`
- mistakes/pi=7 `M2` kind=mc  text=`The minimum age for a basic driver license is: 获取驾照最小年龄为：(B) A. 16B. 17C. 18D. 1`

## 多提清单（0）

_无_

## 答案字母不一致（0）

_无_

## 源里空答案（2）

- Q623 `C-list36.195` 我们=None  stem=`没有让在人行道上通过的行人，你将受到的惩罚是`
- Q746 `M127` 我们=None  stem=`没有让在人行道上通过的行人，你将受到的惩罚是`

## Q&A 答案文本不一致（0）

_无_

## complete 内部重复（5）

- Q117 `C-list83.68` (img=None) 重复于 Q94 `C-list83.44` (img=None)
  stem=`A single, solid white line across a road at an intersection means: 白线横过交通路口表示`

- Q148 `C-list83.99` (img=None) 重复于 Q141 `C-list83.92` (img=None)
  stem=`What does this sign mean?  这个标志什么意思？`
  ⚠️ 附近源段有不同图片 → 应该是漏绑图导致的假重复
    dup 应绑: `media/image133.jpg`
    orig 应绑: `media/image9.jpg`
- Q154 `C-list83.105` (img=None) 重复于 Q141 `C-list83.92` (img=None)
  stem=`What does this sign mean?  这个标志什么意思？`
  ⚠️ 附近源段有不同图片 → 应该是漏绑图导致的假重复
    dup 应绑: `media/image10.png`
    orig 应绑: `media/image9.jpg`
- Q156 `C-list83.107` (img=None) 重复于 Q141 `C-list83.92` (img=None)
  stem=`What does this sign mean?  这个标志什么意思？`
  ⚠️ 附近源段有不同图片 → 应该是漏绑图导致的假重复
    dup 应绑: `media/image129.jpg`
    orig 应绑: `media/image9.jpg`
- Q567 `C-list36.136` (img=None) 重复于 Q566 `C-list36.135` (img=None)
  stem=`持 GDL 驾照者首次违规的罚款是多少？`

