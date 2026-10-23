---
name: resume-extraction
description: 用于将简历提取后的事实段落映射到个人信息与模块，不改写原文，不从目标 JD 推断候选人信息。
version: 1
tools: []
---
# 简历字段与段落提取

## 输入与职责

输入是 facts，每条包含 id、text，可能有 page、confidence、locked、section。这里只负责字段来源和模块映射，不负责图像 OCR、简历润色、诊断、排名或排版。扫描识别不确定性需保留给用户确认，不能凭常识补齐。

## 严格返回协议

仅返回 JSON：

```json
{"profile":{"name":{"value":"","source_fact_ids":[]},"email":{"value":"","source_fact_ids":[]},"phone":{"value":"","source_fact_ids":[]},"target_role":{"value":"","source_fact_ids":[]}},"assignments":{"f0":"other"}}
```

示例中的 f0 只是结构示意，实际必须覆盖输入的每个事实 ID。profile 固定四个键，每个有 value 和 source_fact_ids；assignments 的值只能是 personal、education、projects、experience、skills、summary、other。禁止 Markdown 围栏、TeX、解释文字和自定义模块。

## 来源与完整性规则

1. 字段值必须是来源事实文本中的原文连续片段；不纠错拼写、不标准化电话号码、不翻译姓名、不推测学历。
2. 找不到字段时使用空字符串和空数组，不填“未知”、示例邮箱或从 JD 提取的岗位。
3. source_fact_ids 必须实际存在，并足以支持字段原值；不引用旁边无关段落证明联系方式。
4. 每个输入事实 ID 唯一归类，不能遗漏、删除、合并 ID 或新增 ID；标题行也保留归属。
5. 用户已确认的 section 优先，不因模型偏好重新归类。locked 不代表该事实可以跳过。
6. 多个候选字段矛盾时不拼接为新值；无法明确选择时留空，等待用户校正。

## 分类口径

- personal：姓名、联系方式、求职意向等直接个人信息。
- education：学校、学历、专业、教育时间与对应成绩/课程事实。
- projects：课程、研究、个人、竞赛或业务项目，不自动当成工作。
- experience：明确的实习、工作、实际实践身份及对应职责，不虚构雇佣关系。
- skills：已有工具、语言和技能描述，不根据项目工具推导“精通”。
- summary：原稿已有自我评价或摘要，不自动新增。
- other：证据不足或无法归类的事实，保留原文等待校对。

模块标题可帮助理解相邻段落，但遇到新的明确标题应切换，不能把后续所有内容永久归到上一个模块。日期、公司和角色应结合原文所属经历，不将不同经历串联成新履历。

## 反例与自检

JD 写“海外增长运营”，简历没有求职意向：target_role 留空。原文学校名有疑似错字：保留原字，不改成相似名校。原文只有参与竞赛：归项目/其他，不变成全职岗位。

输出前检查所有 ID 集合完全相等、字段原文可追溯、类别合法、空值一致，且没有新个人信息或原文改写。
