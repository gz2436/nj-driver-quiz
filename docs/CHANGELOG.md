# 题库变更日志 / Question Bank Changelog

## 2026-11-25 — 对照 2026 版手册的更正

依据：NJ Driver Manual 2026（2026 年 4 月修订，英文版和中文版）；手册没收的标志依据联邦 MUTCD 第 11 版（2023 年 12 月）；题目原文依据 `sources/` 里的源 docx。每一处改动（题号、字段、原值、新值、出处页码或 MUTCD 条目）记在 `data/corrections.json`，`python3 tools/check_corrections.py` 校验题库没有偏离这份记录。

- 题号从这一版起冻结。本文件下面 2026-05-12 各条里的题号是当时的编号，和现在的不一一对应。
- 60 道题有用户看得到的改动：
  - 11 道改答案：Q9、12、21、45、205、490、491、562、563、564 按手册改，Q281 恢复源文件的选项顺序。其中 Q9、490、491 在 2026-05-12 已经改过一次，重建题库时丢了，这次补回；Q563、564 是同样内容的重复题。
  - 11 道换配图或去掉配图：Q153、169、193、246、249、252、263、269、538、544 换回源文件里这道题的原图；Q543 在源文件里没有配图，原来那张属于 Q544。
  - 其余是选项和题干修复：解析时错位、合并、混进相邻题文字、丢了填空位的，按源文件重建。
- 162 道题加了核对状态 `review`：109 道对照手册（带页码），53 道手册没收、注了 MUTCD 条目。还有 405 道未核。进度写在 `data/version.json`，站内免责声明读这个文件。
- 21 条用户报错（Tally 表单，2026-05-23 到 11-10）涉及 12 道题，11 道确实有错，已改；Q240 答案没错，补了解析。
- 修正 `gdl_age_summary` 解析的用词（改用中文手册的说法），新增 W1-7 双向大箭头标志解析。

## 2026-05-12

Initial release. 573 questions. Below: answer corrections vs. source docx.

- **Q9** B → **C** — Manual p16: basic license age is 18; "17" is probationary
  > The minimum age for a basic driver license is: 获取驾照最小年龄为：
- **Q431** B → **C** — Manual p86 / N.J.S.A. 39:4-138: 25 ft from crosswalk
  > You may not park with feet of a crosswalk or intersection.
- **Q509** D → **C** — Manual p117: under-21 BAC limit is 0.01% (zero-tolerance)
  > What is the legal BAC limit for New Jersey drivers who are under the age of twenty-one? 21 岁以下的新泽西司机
- **Q510** C → **B** — Manual p117: adult BAC limit is 0.08%
  > What is the legal BAC limit for individuals who are 21 years of age or older in the state of New Jer

## 2026-05-12 — automated parsing fixes

- Cat A: dropped Chinese stem leak from optA, shifted options, on 86 questions.
  Of these, 19 had answer=D which referenced an option lost during initial parsing; marked `_needs_review`.
- Cat B: merged 4-line bilingual option pairs into 2 bilingual options, on 29 questions.
- Total auto-fixed: 115 questions.

## 2026-05-12 — dropped 21 broken questions

- Q205 (no_options): Which of the following signs represents two-way traffic?
- Q304 (cat_a_answer_d_lost): If a NJ driver is convicted of a DUI charge, his or her license may be lost for up to:
如果新泽西州的司机被判定犯有酒后驾车罪，他或她的驾照可能会被吊销，
- Q314 (cat_a_answer_d_lost): Heavy trucks on the ramp 坡道上的重型卡车
No need to yield the right-of-way 不需要让出路权
While driving a motor vehicle on a public ro
- Q315 (cat_a_answer_d_lost): In normal driving, a driver should place his/her hands on the steering wheel at the:
在正常驾驶中，驾驶员应将双手放在方向盘上，在
- Q335 (cat_a_answer_d_lost): When a traffic signal turns green at an intersection and you are going straight through, you must:
当十字路口的交通信号灯变成绿色，而你要直行
- Q346 (cat_a_answer_d_lost): Car drivers should never move into the same lane with a motorcycle side by side, even if the lane is wide and the cyclis
- Q364 (cat_a_answer_d_lost): Passing on the right is permitted in all of the following situations, EXCEPT:
在下列所有情况下都允许右侧超车，但以下情况除外。
- Q367 (cat_a_answer_d_lost): If you see a pedestrian using a guide dog or other service animal and/or carrying a white cane at an intersection, you m
- Q386 (cat_a_answer_d_lost): If a vehicle stalls on the tracks and the motorist sees a train coming, the motorist must:
如果车辆停在铁轨上，而驾车者看到有火车驶来，驾车者必须
- Q390 (cat_a_answer_d_lost): Before pulling out from a right-side parallel parking space, you must:
在从右侧平行停车位驶出之前，你必须。
- Q413 (cat_a_answer_d_lost): When a stopped school bus has red lights flashing on a divided highway, you must:
当一辆停在路边的校车在分车道公路上闪烁着红灯时，你必须。
- Q418 (cat_a_answer_d_lost): When being approached from the rear by an ambulance with a siren, you should:
当有救护车鸣笛从后方接近时，你应该。
- Q446 (cat_a_answer_d_lost): If you are driving at a slower speed than other traffic on a highway or freeway, stay in the lane:
如果你在高速路或高速公路上以比其他车辆更慢
- Q455 (cat_a_answer_d_lost): In preparing to leave a parallel parking spot, a driver should:
在准备离开平行停车位时，司机应该
- Q457 (cat_a_answer_d_lost): When approaching or driving through a work zone, you must not:
当接近或驶过工作区时，你不得
- Q458 (cat_a_answer_d_lost): If you are signaled by a flag person at/near a railroad crossing or construction site, you must:
如果你在铁路道口或建筑工地上/附近得到旗手的信
- Q461 (cat_a_answer_d_lost): The likelihood of an accident increases if a driver is under the influence of:
如果一个司机受到以下因素的影响，发生事故的可能性就会增加
- Q463 (cat_a_answer_d_lost): When it looks like a collision may happen, drivers must take an immediate step to:
当看起来可能发生碰撞时，司机必须立即采取措施，以
- Q470 (cat_a_answer_d_lost): Drivers must maintain a constant speed when passing and reentering the lane in front of trucks or buses, since trucks/bu
- Q477 (no_options): 向你计划移动的方向看肩膀，以检查盲点
Look in your rearview and side mirrors 看看你的后视镜和侧视镜
Do not take your eyes off the road ahead for more 
- Q485 (cat_a_answer_d_lost): When you are turning from a one-way street onto a two-way or divided street, always turn from:
当你从单行道转入双行道或分叉道时，总是从
