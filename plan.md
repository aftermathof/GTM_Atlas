# GTM Atlas

> 状态：设计草案（可修改） 适用范围：单个网站的三个功能入口，不是三个互不关联的项目。 产品定位：面向 GTM/海外商业化方向的学习、面试练习和简历定制平台。**以可溯源的知识和可信的用户经历为核心，而不是仅仅封装一个聊天框。**

---

## 0. 版本决策与边界

### V 5.1 新增/调整

1. 首页统一为**三个一级入口**：① GTM 知识学习，② GTM 面经与 Mock 面试，③ GTM 简历诊断与修改。
    
2. 一个**全局 AI Assistant** 可从任何页面唤起；共享模型服务层、身份上下文与权限策略，但每个功能拥有自己的任务状态和检索工具。
    
3. 学习文档、面经、JD 和岗位画像采用统一知识底座，**逻辑分库/按类型检索**，不必建三个物理向量库。
    
4. 新增 **Mock Interview Agent**：按目标岗位、行业、难度、用户简历生成有计划的题目组合；逐题追问、评价、总结薄弱项。
    
5. 简历工作流继承 V 4：识别 → 诊断/评分 → 用户选择 → 基于证据改写 → 模板渲染 → PDF QA → 多轮微调。
    
6. 统一后端采用 FastAPI + LangGraph；Agent 编排逻辑、领域 Skills、RAG 策略、评分规则、版本管理自行实现。
    
7. **所有 AI 对话输入框统一支持语音输入**：全局 AI、学习问答、面经问答、Mock 面试回答、简历诊断/修改指令；语音先转文字，允许编辑确认后提交。
    
8. 新增独立的 **「前端设计（Prompt 占位）」章节**：只保留对接位置与技术接口约束，不重写现有前端 Prompt。
    

### 不在 V 5 MVP 范围

- 实时双向语音通话（低延迟边听边答）、摄像头模拟、视频自动转写；**MVP 必须支持录音 → 语音转文字 → 用户确认 → 文字提交**，Mock 面试也适用。
    
- 自动申请岗位、代投简历、替用户联络招聘方。
    
- 完整多 Agent 自治群体、复杂多租户企业 SaaS、收费系统。
    
- 未授权的内部讲座原片、付费课程或第三方面经公开分发。
    
- 声称通过面经推断真实面试通过概率或 ATS 官方评分。
    

---

## 1. 首页与前端信息架构

### 1.1 首页三栏目（一级功能卡片）

|入口|URL|用户目标|主要按钮|
|---|---|---|---|
|**GTM 知识学习**| `/learn` |查阅有组织的知识，并向 AI 提问|浏览知识体系、搜索、问答|
|**GTM 面经**| `/interviews` |阅读面经、按岗位筛选、Mock 面试|面经库、开始模拟面试|
|**GTM 简历修改**| `/career` |诊断、评分、改写与输出 PDF|上传简历、选择岗位、开始诊断|

**全局导航**：Logo / 三个一级入口 / 全局搜索 / AI Assistant / 我的历史 / 设置。 **首页视觉原则**：视觉细节以后由独立的前端设计 Prompt 决定；本文件仅规定信息架构、功能入口、语音交互接入和可访问性，不在此重写已有视觉 Prompt。

### 1.2 三栏目内部页面

**A. 知识学习**：`/learn` 知识图谱/目录，`/learn/:slug` 文章详情，`/learn/ask` 带证据 AI 问答。正文左侧目录、中央内容、右侧文章 TOC；AI 面板侧滑或固定右侧，手机端使用抽屉。

**B. 面经**：`/interviews` 列表与筛选，`/interviews/:id` 文章详情，`/interviews/mock/setup` 场景选择，`/interviews/mock/:sessionId` 逐题问答台，`/interviews/mock/:sessionId/report` 复盘报告。

**C. 简历**：`/career/setup` 岗位/行业选择，`/career/upload` 上传与识别确认，`/career/review/:sessionId` 诊断台，`/career/editor/:sessionId` 修改/模板/PDF 预览，`/career/history` 历史版本。

### 1.3 全局 AI Assistant 的行为

- 全局 AI 入口是**一个 UI 和一个模型服务网关**，不是所有功能共用一个无限增长的对话 Prompt。
    
- 用户在知识页询问当前文档：携带当前文章 `document_id`，优先检索学习集合。
    
- 用户在面经页询问当前面经：优先在合法可用的面经文档集合检索。
    
- 用户在简历页问“怎么改”：传入当前授权的简历版本、所选岗位画像和工作流状态；**不得自动执行写入/生成 PDF**。
    
- 跨页面提问须明确提示当前作用域：`当前文章` / `学习知识库` / `面经库` / `当前简历` / `全站可用知识`；可以切换。
    
- 模型配置支持后端环境变量/API Provider Adapter，API Key 仅保存在服务端。用户自带 Key 若未来支持，需单独安全设计。
    
- 所有生成结果提供来源引用、版本/模型信息和必要的不确定性声明。
    

---

## 1.4 全站统一语音输入组件

**覆盖范围**：所有允许向 AI 发送自然语言的输入窗口，至少包括 `/learn/ask`、全局 AI Drawer、面经页面问答、`/interviews/mock/:sessionId` 的逐题回答，以及 `/career/review/:sessionId`、`/career/editor/:sessionId` 的反馈与修改指令。统一复用 `VoiceInput`，不能只在全局聊天框加麦克风。

**交互流程（非实时语音通话）**：点击麦克风 → 请求浏览器麦克风权限 → 录制 → 停止 → 上传或本地识别 → STT（Speech-to-Text）→ 文本展示在当前输入框 → 用户可编辑/确认 → 调用原有文字业务接口。**不要将语音转写结果未经确认就自动交给 Agent 执行**，尤其是简历改写、批量修改和其他具有副作用的操作。

|状态|前端行为|约束|
|---|---|---|
|idle|展示麦克风按钮|与键盘输入并存|
|recording|明确录音提示、时长、停止/取消|需用户主动开始；权限拒绝时退回文字|
|transcribing|展示识别中、允许取消|超时、文件大小和录音长度限制|
|review|转写文字回填输入框，可修改再发送|不自动发送，不静默覆盖已输入文字|
|error|明确报错、重试或改用键盘|不丢失原草稿|

**实现选择**：前端优先使用浏览器 `MediaRecorder` 采集音频；后端通过独立 `SpeechToTextProvider` 调用支持中文/英文/中英混合的 STT 服务，具体供应商可配置（云端 API 或自托管 ASR）；**DeepSeek 文本聊天 API 不等于 STT 服务**。MVP 不要求 TTS 语音播报、WebRTC 流式双工语音或实时打断；这些留作后续扩展。

**音频与隐私**：用户需知晓是否向第三方 STT 服务传输音频；短时临时存储，默认转写后清除原音频，不加入公共 RAG、不用于训练；限 MIME、时长、大小、速率，所有用户文件按权限隔离。语音录入的最终文本沿用原模块的审计/会话权限策略。

**Mock 特别要求**：每题均可语音回答；保存**用户确认后的文字答案**作为评分输入，题目与追问沿用原 Mock Graph；可选记录 `input_mode=voice`、转写耗时和语言，不以 ASR 错字直接惩罚用户，复盘说明识别误差可能影响评价。

**建议 API**：`POST /api/v1/ai/transcriptions`（multipart 文件、language_hint 可选，返回 `transcript`、`detected_language`、`duration_ms`、`request_id`，不默认保存音频）；后续替换 STT Provider 不改变三个业务 Graph。全局模型 Provider 与 STT Provider 必须分离配置。

---

## 1.5 前端设计

> 前端 UI 设计及 UX 交互 主要参考 /C:/Users/64954/Documents/Codex/2026-10-22/new-chat-3/outputs/GTM 同款前端设计 Prompt.md，这个文件中已经详细说明了我的审美设计要求。

---

## 2. 用户角色、标签与岗位选择

### 2.1 统一选择器

三个模块都可复用一个可选的 `CareerContext`：

 role: overseas_channel_sales  # gtm / overseas_ops / kol_marketing / b 2 b_sales / imc / growth / pmm / ecommerce_ops / etc.  
 industry: consumer_electronics # ai_hardware / robotics / fmcg / consumer_electronics / software / etc.  
 business_model: B 2 C          # B 2 B / B 2 C / hybrid / unknown  
 region: north_america       # SEA / MENA / LATAM / Europe / etc.  
 seniority: intern            # intern / new_graduate / experienced  
 language: zh-CN

- `QB/QC` 等不同公司存在的非统一岗位简称，不应强制映射为标准岗位；提供别名解释与自定义选项，并保留原始名称。
    
- 默认可不填；筛选不充分时可以推荐邻近领域资料，但要标明“跨岗位参考”。
    
- JD 若由用户提供，其明确要求优先于泛化的岗位画像；行业画像提供补充，不覆盖实际 JD。
    

### 2.2 数据口径

岗位画像是**有版本、可追溯、可审核**的结构化业务配置。面经提供案例和问题分布，不能自动上升为行业通行的评分标准。

---

## 3. 知识资产：四种内容，三类检索场景

### 3.1 数据源与职能分工

|数据资产|示例|如何用|权威性/限制|
|---|---|---|---|
| `learning` 学习文档|S&OP、渠道策略、KOL ROI|学习问答、解释能力概念、补充分析|按作者/来源标注可信度|
| `interview` 面试经验|面试题、回答、反思、问题类型|面经检索、Mock 题目候选、追问角度|属于个例，不能代表标准|
| `jd` 岗位描述|海外销售/市场营销职位 JD|岗位能力抽取、简历匹配|记录企业、日期、市场与来源|
| `role_profile` 岗位画像|能力维度、解释、规则权重|诊断评分、题目蓝图、能力差距|需版本化与审核，非随意检索拼接|

另外保留 `skills/`（任务执行说明）和 `templates/latex/`（排版模板），**它们不是普通 RAG 内容**。用户简历另存私有文件/结构化事实表，默认不进公共知识库。

### 3.2 Markdown 原始文件作为 Single Source of Truth

 knowledge/  
   learning/  
     gtm-foundations/  
     channel-sales/  
     marketing/  
   interviews/  
     kol/  
     b 2 b-sales/  
     gtm/  
   jobs/  
     overseas-sales/  
   assets/   # 仅已获得许可的图表/图片  
 profiles/  
   roles/*.yaml  
   industries/*.yaml  
 skills/  
   learning-qa/SKILL.md  
   interview-planning/SKILL.md  
   interview-evaluation/SKILL.md  
   resume-diagnosis/SKILL.md  
   resume-rewriting/SKILL.md  
   resume-fact-check/SKILL.md  
   latex-render/SKILL.md  
 templates/latex/  
   classic-cn/  
   classic-en/  
   modern-onepage/

统一 Markdown frontmatter：

 ---  
 id: interview_000001  
 title: 海外渠道销售面试记录  
 kind: interview  
 role_tags: [overseas_channel_sales, b 2 b_sales]  
 industry_tags: [consumer_electronics]  
 region_tags: [north_america]  
 source_type: public_post  
 source_url: null  
 source_author: null  
 collected_at: 2026-10-23  
 published_at: null  
 permission: private_reference_only # public_display / internal_index / no_llm / not_usable  
 quality_status: unverified       # reviewed / unverified / deprecated  
 language: zh-CN  
 ---

`permission` 不仅影响前端展示，还必须约束入库、检索、模型传输、缓存和日志；不能在前端隐藏后仍允许后端发送全文。未经授权的内部/付费材料仅保留合规的自写摘要或合法链接，禁止通过 RAG 输出重构原文。

### 3.3 入库 Pipeline（离线/后台）

1. 文件扫描和校验：格式、大小、编码、路径安全、唯一 ID、访问许可。
    
2. 解析 Markdown：保留层级标题、原始路径、段落及问答边界；整理图片的说明（有许可才处理）。
    
3. 去重：文件 SHA-256 + 正文近重复检测；支持增量更新和删除传播。
    
4. 标签清洗：岗位别名映射、行业/地区多标签、资料类型、发布日期和可靠性。
    
5. 分类型 Chunk：学习资料按 H 2/H 3，面经按“题目+回答+上下文”，JD 按职责/要求，段落过长再拆。
    
6. Embedding + 全文索引：同一文档模型版本一致；升级 Embedding 时重建向量。
    
7. 写入 PostgreSQL + pgvector：documents、chunks、embeddings、source_metadata、ingestion_jobs 等。
    
8. 验证：抽样检查文档遗漏、Chunk 边界、来源回链、权限过滤和索引覆盖率。
    

起点建议：学习资料每 chunk 约 300–600 tokens；面经问答完整优先。只是实验默认值，后续通过评测调优。

### 3.4 检索策略

**统一 Retriever 底座，按业务使用三个逻辑工具**：

 search_learning(query, role=None, industry=None, top_k=5)  
 search_interviews(query, role=None, industry=None, top_k=5)  
 search_jobs(query, role=None, industry=None, top_k=5)

内部：`permission filter → role/industry/region metadata filter → lexical full-text + vector search → RRF 融合 → 可选 rerank → dedup → evidence pack`。

- 关键词检索对缩写、品牌、岗位名有效；语义检索用于同义表达。
    
- 初始 vector top 20、lexical top 20、最终 top 5–8；不是固定最优超参。
    
- 采用 PostgreSQL 原生全文索引做第一版 lexical search；要 BM 25 可后续评估插件/专用引擎，不要把 PostgreSQL 内置全文排序直接称为 BM 25。
    
- 所有检索结果包含 `chunk_id/doc_id/heading_path/source_url/quality_status/permission/score`；未经许可不可把正文发给外部 LLM。
    
- 检索不足时输出“知识库未发现足够证据”，不能编造引用。
    

### 3.5 引用与信任边界

模型读取的 Markdown 和网页均为**不可信数据**：其中可能包含提示词注入、错误事实、恶意链接。仅作为证据内容，不允许改变 System/Developer/Skill 指令或发起任意工具调用。

---

## 4. 模块 A：GTM 知识学习 + RAG Tutor

### 4.1 核心功能

- 按 GTM 知识全景目录和岗位主题浏览 Markdown 文档；面向长文的 TOC、链接交叉引用、Mermaid 导图。
    
- 全文搜索：先提供确定性搜索结果，必要时选择 AI 总结。
    
- AI 问答：选定资料域，检索并生成带 Chunk/文章级引用的回答。
    
- 学习模式：术语解释、概念比较、案例练习、学习路径建议（学习路径可基于用户选择岗位生成，但应标明建议性质）。
    
- 收藏、阅读进度（账号能力出现后）；对答案的引用、正确性进行反馈。
    

### 4.2 Learning QA Graph（可先做固定流程）

`user_question → scope/permission resolver → query rewrite(optional) → retriever → evidence quality check → answer composer → citation validator → response`

- 这条链路**首先是 RAG Workflow，不必包装成多 Agent**。
    
- 对知识库缺乏根据的问题，明确说明无法仅凭资料回答；可在用户允许下转外部 Web 工具，并区分外部证据。
    
- 引用必须对应真实返回的 chunk，不允许模型捏造 `source_id`。
    

### 4.3 输出格式

回答正文、引用资源、适用岗位/行业、信息局限、延伸阅读。前端 citation 点击跳到目标文章与标题段落。

---

## 5. 模块 B：GTM 面经库 + Mock Interview Agent

### 5.1 功能

1. **面经浏览**：筛选岗位、行业、企业（若有合法来源）、地区、面试轮次、难度和主题；全文展示需符合许可。
    
2. **问答练习**：从授权的题目库随机抽题；展示来源/题型与参考思路。
    
3. **Mock Interview**：配置岗位、行业、目标企业/JD（可选）、难度、题数、语言、用户简历（可选）。
    
4. **文字/语音回答**：每道 Mock 题均可键盘输入或录音转写；转写文本须可校对后提交，评分以确认文本为准。
    
5. **自适应追问**：根据用户上一题答案中的不足提出 0–2 个追问；限制追问深度避免无限循环。
    
6. **面试复盘**：对照能力维度和明确评分 rubric，指出论证漏洞、STAR 结构、业务逻辑、术语使用、表达清晰度、下一轮练习建议。
    
7. **持续练习**：保留题目、用户答案、反馈与版本；支持重试某一题。
    

### 5.2 题目生成不是“只靠随机”

建议**混合题目蓝图**：

- 固定能力维度覆盖：岗位认知、市场/用户分析、实际业务场景、行为经历、数据指标与英语/跨文化沟通（按角色调整）。
    
- 题源一：面经库中**已授权**的真实题目，尽可能保留来源。
    
- 题源二：根据职位 JD/岗位画像，LLM 生成新的模拟题，清楚标记 **AI 生成题**，不能冒充真实企业题。
    
- 题源三：由用户简历提取的可验证经历，生成针对性追问；不得直接以库中他人的经历当作用户事实。
    
- 同一场 Mock：按可配置比例控制来源、能力覆盖和难度，设随机种子以支持复现；避免重复题与语义近重复。
    

示例：用户选 `海外渠道销售 + 消费电子 + 实习生`，上传包含 AI 运营经历的简历：

|题型|示例（AI 生成）|依据|
|---|---|---|
|岗位认知|你如何理解海外渠道销售与海外运营的区别？|role_profile|
|业务案例|经销商销量不达标且库存积压，你如何排查？|learning + JD|
|简历追问|你提及用 AI 改善内部培训流程，具体如何衡量效率？|用户简历事实|
|行为面试|请举例说明一次跨团队沟通分歧及你的处理方式。|能力维度 rubric|
|基础指标|如果渠道返利提高，如何评估利润率与销量变化？|learning|

### 5.3 Mock Interview LangGraph

Syntax error in graphmermaid version 8.8.3

ERROR: [Mermaid] Lexical error on line 7. Unrecognized text.
...校验] F --> G[提出当前问题：文字显示] G --> H[等待用
----------------------^

**注意**：`interview_planner`、`interviewer`、`answer_evaluator` 在代码中可以先是同一个模型的不同受控节点/Prompt，不需要为了“多 Agent”强行创建三个自治智能体。

### 5.4 状态与记忆

 mock_session_id, user_id, career_context, resume_version_id?, jd_id?,  
 seed, blueprint_version, questions[], current_question_index,  
 answers[], followup_counts[], scores[], feedback[], status,  
 created_at, finished_at

- 工作状态通过 LangGraph checkpoint 恢复；持久业务记录保存在数据库。
    
- 每次提交答案写入幂等标识，避免刷新后重复推进下一题。
    
- 评价为“训练参考评分”，不推断企业招聘结果；支持查看评分依据和重新评估。
    

### 5.5 评价 Rubric（首版）

各维度 0–4 分并加解释性证据：相关性、结构性、专业准确性、可验证经历、商业逻辑、沟通表达。权重由岗位画像定义；如果题型不适用某一维度，标记 `N/A` 后重归一化，不能强行给低分。保留原回答、评价版本、引用依据。

---

## 6. 模块 C：GTM 简历诊断与 LaTeX 修改 Agent

### 6.1 用户两种主要意图

- **只诊断**：上传 PDF/图片 → 解析确认 → 选择岗位/行业或导入 JD → 诊断报告、评分、修改建议 → 停止，不生成新简历。
    
- **直接改写**：先诊断且确认解析事实 → 用户明确授权哪些段落可改 → 选择模板/语言 → Resume IR 结构化改写 → 事实校验 → 安全 LaTeX 编译 → PDF 预览 → 用户反馈迭代。
    

诊断后必须提供：`只查看建议`、`补充/纠正信息`、`允许生成新版`、`手动改写`。简历生成不得被默认勾选或自动触发。

### 6.2 简历工作流

### 6.3 RAG 的准确定位

- 通过 `search_jobs` 找当前目标岗位的能力要求；通过 `search_interviews` 补充面试关注点；通过 `search_learning` 提供术语和业务理解。
    
- RAG **绝不能为用户生成不存在的经历、指标、成果和资历**。事实仅来源于用户简历或用户明确补充。
    
- “岗位匹配评分”是内部 rubric 的解释性分数，不是客观录用概率，更不能冒充 ATS 官方分数。
    
- LaTeX Renderer 是确定性工具，不需要访问 GTM RAG；排版与事实校验可独立执行。
    

### 6.4 原始文档、IR 与渲染

- 原始上传文件不可变；先用 PyMuPDF 提取可选文字，扫描件走 OCR/VLM 并保留识别置信度与原页定位。
    
- `Resume IR` 是 JSON/Pydantic 结构；每段 bullet 映射到来源证据和可编辑锁定标志。
    
- Rewriter 输出 `patch`，而不是任意重写整份 LaTeX；先验证 patch，再用 Jinja 2 受控模板生成 `.tex`。
    
- 使用受限容器编译 XeLaTeX/Tectonic（需验证中文字体支持），禁止 shell-escape、出站网络、宿主机敏感目录挂载，并施加 CPU/内存/时间限制。
    
- PDF QA：可读取内容、教育经历未缺失、页数目标、边界溢出、中文字符和关键字段一致性；视觉审查可选。
    
- 每轮生成不可变 `ResumeVersion`，支持比较、回滚、重新编辑与导出 `.tex` + `.pdf`。
    

---

## 7. Agent Runtime / Workflow / Multi-Agent 架构决策（ADR-001）

### 7.1 选择

**FastAPI + LangGraph + PostgreSQL(+pgvector) + 原生 Python Tools + 自研领域 Skills / RAG / 业务规则。**

- Codex 是实现该工程代码的开发工具，不是线上产品的运行时。
    
- 不克隆 Codex / Claude Code / Dify 的整套产品。
    
- 不以“多 Agent”作为目标；优先使用有明确分支/约束的有状态工作流。
    
- LangGraph 提供状态图、条件路由、checkpoint、interrupt/resume；**业务图、节点、权限、错误恢复策略自行开发**。
    

### 7.2 三个业务 Graph，共用基础能力

|Graph|核心类型|需要 LLM 推理的部分|确定性工具/步骤|
|---|---|---|---|
| `learning_qa_graph` |检索-生成|Query Rewrite、Answer|权限过滤、混合检索、引用验证|
| `mock_interview_graph` |长会话状态机|题目规划、追问、评价|题数控制、去重、存储、分数合并|
| `career_resume_graph` |人工审批工作流|诊断、改写|简历解析、规则校验、模板/编译/QA|

统一 `LLMProvider` 支持 DeepSeek 和可替换模型；图像/扫描件识别使用具备视觉能力的独立 `VisionProvider`，**不要假设某个文本模型接口必定支持图像**。

### 7.3 Skills 机制

Skill 定义任务流程/验收条件/工具要求，不直接拥有所有工具权限。目录如：`skills/learning-qa/SKILL.md`、`skills/mock-interviewer/SKILL.md`、`skills/resume-diagnosis/SKILL.md`、`skills/resume-rewriter/SKILL.md`。实现 Skill Registry：元数据、适用场景、版本、Prompt 注入控制、依赖工具白名单、兼容性测试。用户上传的 MD 不能自动升级为可执行 Skill。

### 7.4 MCP

保留 `ToolRegistry` 与可插拔 `MCPAdapter`，首版内部 RAG/文件/模板使用原生 Python tools。只有外部搜索、招聘源、Drive/日历等真正需要共享工具协议时才接 MCP。MCP 不负责 RAG 质量和业务可靠性，工具必须经过授权、输入校验和资源限制。

### 7.5 Memory 分层

|层|存储|使用方式|
|---|---|---|
|Working State|LangGraph state|当前步骤、证据包、控制参数、待审批状态|
|Session Checkpoint|LangGraph checkpointer|暂停/恢复、面试逐题状态、异常续跑|
|Durable Business State|PostgreSQL|面试记录、简历版本、历史评分、审计信息|
|Opt-in User Preferences|PostgreSQL（用户可编辑/删除）|语言、岗位、常用模板；不擅自提取私人事实|
|Knowledge Store|Markdown + PG/pgvector|共享且授权的领域知识，非个人 Memory|

全局 AI 可以读取用户明确授予的当前任务上下文；跨模块调用需处理权限与陈旧状态，不能因为同账户就自动把完整简历注入所有问答。

### 7.6 任务执行与错误处理

- 简短知识问答：普通 API + 可选 SSE；文字输入与语音转写统一为文本业务请求。
    
- 语音识别采用独立 STT API/Provider；音频不进入普通 Chat Endpoint，只有确认后的转写文本进入相应 Graph。
    
- 简历 OCR、PDF 编译、较长面试总结：异步 Job API；MVP 可以单 Worker，之后按负载升级队列。
    
- 持久化 `job_id/run_id/idempotency_key`；限制超时、模型重试次数、最大 LLM/tool 调用次数、最大 Token/费用预算。
    
- 对用户补充事实和“是否生成 PDF”设置显式 `interrupt`；重启后通过 checkpoint 恢复。
    
- 外部 LLM、网页检索与 OCR 错误应有清晰退化路径，不可静默输出假结果。
    

---

## 8. API 契约建议

### 8.1 全局与知识

 GET    /api/v 1/catalog/roles  
 GET    /api/v 1/catalog/industries  
 POST   /api/v 1/ai/chat                  # scope: learning/interview/career/global  
 POST   /api/v 1/ai/transcriptions        # 语音转写：音频 -> 待确认文本  
 GET    /api/v 1/knowledge/documents  
 GET    /api/v 1/knowledge/documents/{id}  
 POST   /api/v 1/knowledge/search  
 POST   /api/v 1/admin/knowledge/reindex  # 管理员受权，异步

### 8.2 Mock

POST   /api/v 1/mock/sessions            # 新建，配置题数/岗位/难度/seed/简历引用
GET    /api/v 1/mock/sessions/{id}
POST   /api/v 1/mock/sessions/{id}/answers
POST   /api/v 1/mock/sessions/{id}/next
GET    /api/v 1/mock/sessions/{id}/report
GET    /api/v 1/mock/sessions/{id}/history

### 8.3 Career

POST   /api/v 1/career/resumes           # 私有上传并返回文件 id
POST   /api/v 1/career/sessions
GET    /api/v 1/career/sessions/{id}/diagnosis
POST   /api/v 1/career/sessions/{id}/confirm-facts
POST   /api/v 1/career/sessions/{id}/approve-rewrite
POST   /api/v 1/career/sessions/{id}/feedback
GET    /api/v 1/career/sessions/{id}/versions
GET    /api/v 1/career/versions/{id}/artifacts

共同约束：认证和对象级授权、Pydantic schema、幂等键、分页、请求限速、审计日志、统一错误码。下载地址短期有效且严格鉴权。

---

## 9. 数据模型（建议最小集合）

users
knowledge_documents
knowledge_chunks
knowledge_embeddings
knowledge_ingestion_jobs
role_profiles
industry_profiles
skills_registry
ai_conversations
ai_messages
voice_transcription_events  # 可选：仅元数据，不存音频正文
mock_sessions
mock_questions
mock_answers
mock_evaluations
resume_documents
resume_facts
resume_sessions
resume_diagnoses
resume_versions
resume_patches
artifact_files
agent_runs
agent_events

主键均为 UUID；业务数据按 `user_id` 或租户隔离。`source_doc_id` 和 `source_chunk_ids` 贯穿问答、面试题和诊断报告。原文/模型输出/诊断/版本各保留模型版本及时间戳；知识资料被删除时同步撤销索引与展示权。

---

## 10. 仓库结构：单仓多模块

gtm-atlas/
├── apps/
│   └── web/                    # VitePress/Vue，三个栏目 + AI Drawer + 全局 VoiceInput
├── services/
│   └── api/                    # FastAPI HTTP/SSE, auth, DTO
├── packages/
│   ├── agent_core/             # LLM provider, STT provider, tools, state, tracing
│   ├── rag/                    # ingestion, index, hybrid retriever, citations
│   ├── career/                 # career graph, IR, scorer, rewriter
│   ├── mock/                   # interview graph, planner, evaluation
│   ├── learning/               # learning QA graph
│   └── document_renderer/      # LaTeX, compilation, PDF QA
├── knowledge/
│   ├── learning/
│   ├── interviews/
│   └── jobs/
├── profiles/
│   ├── roles/
│   └── industries/
├── skills/
├── templates/latex/
├── infra/                      # compose, DB init, migrations, sandbox
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── evals/
│   └── fixtures/               # 合成测试简历、公开授权样例
├── docs/
│   ├── architecture/
│   └── adr/
├── .env.example
└── README.md

可先实现单 FastAPI 服务、模块化 Python 包；不需要一开始拆成微服务。数据库迁移使用 Alembic，开发环境固定依赖版本。

---

## 11. 开发路线图与验收

|阶段|交付物|不应提前引入|
|---|---|---|
|**M 0 基础**|三入口静态页面、Markdown 渲染、统一 CareerContext；所有 AI 输入位保留 VoiceInput 接口和权限退化态|多 Agent 和复杂 Memory|
|**M 1 知识**|MD 入库、类型/权限过滤、混合检索、带来源的学习问答|大规模重排服务|
|**M 2 面经**|面经列表、题目池、文字/语音转写 Mock 3–5 题、逐题反馈与报告；复用全局 STT 服务|实时双向语音视频通话|
|**M 3 简历**|PDF/图片解析、岗位诊断、显式确认、LaTeX PDF、迭代回滚|自动投递|
|**M 4 工程强化**|Checkpoint 恢复、并发/隐私测试、引用有效率、RAG 与 Agent 对照实验|为多 Agent 而多 Agent|

建议 M 1/M 2/M 3 的开发可并行，但**尽量先完成一条端到端使用闭环**。

### 11.1 验收场景

**语音输入为跨模块 MVP 验收项**：学习问答、面经/Mock、简历交互、全局 AI 四类输入均可录音、停止、转写、人工校对、提交；拒绝麦克风权限、转写失败或录音取消时，键盘输入始终可用；未经确认不得触发重写。

1. 从学习页问「海外渠道销售与 KOL 营销的区别」→ 获取带原文定位的学习知识回答，不把面经当权威定义。
    
2. 用户选 `KOL + 消费电子` → 生成 5 题 Mock；至少覆盖 3 个能力维度；随机种子可重现题型/已固定题池抽样。
    
3. 用户上传一份含真实 AI 运营经历的简历 → Mock 能针对已有经历追问；不能虚构指标。
    
4. 用户上传扫描版 PDF → 页面展示识别出的结构与低置信度字段，需用户确认再优化。
    
5. 用户只选择“诊断” → 绝不生成新版 PDF。
    
6. 用户允许优化两段经历并锁定教育背景 → 新 PDF 仅修改获授权内容，原始文件保留。
    
7. 用户说“回到上一版，只保留技能栏修改” → 可通过版本和 patch 明确实现，失败不破坏旧版。
    
8. 所有不合法授权文档不能进入外部模型请求，且无法被其他用户检索。
    
9. 面试过程中断/服务重启后能从上一题继续；重复答案提交不造成重复记录。
    
10. 知识库无足够证据时，回答明确表示不足，而不是虚构来源。
    
11. 四类交互入口的语音转写流程可用，支持中文、英文和中英混合测试样例；关闭权限后回退文本输入。
    
12. Mock 使用转写校对后的答案进行评价；简历页面语音指令在用户确认前不会触发 PDF 重建。
    

### 11.2 评测体系

- **RAG**： Recall@K 、 MRR@K 、citation support、岗位过滤准确度、权限泄漏率。
    
- **Mock**：题目多样性、能力覆盖、岗位相关性、追问针对性、反馈可操作性和人工评分一致性。
    
- **Career**：原始事实保真率、诊断依据覆盖率、模板编译成功率、关键字段一致率、用户授权遵循率。
    
- **系统**：端到端成功率、P 50/P 95 延迟、Token/工具成本、任务恢复成功率、重复请求幂等性。
    
- **语音**：STT 成功率、中文/英文/混合语音词错率（WER/CER 依语言选择）、转写延迟、用户纠错率、录音数据清理验证。
    
- 先构建约 30–50 条人工标注的检索 Query、10–20 个合成简历/JD 测试组合以及一组 Mock 标准答案，不声称这些样本量可给出统计显著的结论。
    

---

## 12. 内容安全、版权与隐私约束

1. **内部讲座/付费资料/平台面经**：拥有访问权不代表拥有再发布、向第三方 API 传输或用于公开 RAG 的权限。记录来源和许可；没授权则不发布全文，也不通过模型输出改写重构受限内容。
    
2. **语音包含个人信息**：用户主动授权录音与第三方 STT 传输，原音频默认短暂处理后删除；严禁把语音音频或转写资料混入公共知识索引。
    
3. **简历包含个人信息**：默认私有、访问隔离、明确删除入口、控制日志和备份保留周期。上线前确认模型服务对输入数据的政策。
    
4. **用户可控**：模型不能编造实习成果、认证、指标；任何实际改写均需用户确认；最终报告和 PDF 作为草稿供用户审阅。
    
5. **Prompt Injection**：检索材料是低信任内容；不能指挥 Agent 修改工具权限、窃取个人资料或执行代码。
    
6. **LaTeX**：禁止任意外部 shell 命令、越权文件访问、未经控制的模板宏注入；编译必须沙箱化。
    
7. **模型输出评估**：Mock 评分、岗位评分只作学习辅助，不将其宣称为真实招聘过程的量化预测。
    

---

## 13. 给 Codex 的实施 Prompt

> 你是一名资深 Python/TypeScript Agent 系统工程师。请在现有 `gtm-atlas` 仓库中实现本文定义的 V 5 产品架构。先审查已有 V 4 Career Agent 与 `前端.md` 的设计约束，不破坏现有功能；先读取用户单独提供的前端设计 Prompt（本文 1.5 节只作占位）；再生成 `IMPLEMENTATION_PLAN.md` 列出分阶段任务与实际文件变更，再按 M 0→M 1→M 2→M 3→M 4 逐步实现。
> 
> **必需功能**：三入口首页、全局 AI Assistant、**所有 AI 输入窗口统一支持录音 STT 并可编辑确认**、GTM 学习 RAG 问答、GTM 面经检索、可引用题源的 Mock Interview、针对简历的自适应追问、岗位定制简历诊断、用户授权后 LaTeX/PDF 改写和多轮版本回滚。
> 
> **硬性架构**：FastAPI + LangGraph + PostgreSQL/pgvector，VitePress/Vue；共用检索基础设施和模型适配层，分开实现 learning、mock、career 三条业务 Graph。不要克隆 Dify、Codex、Claude Code 等完整 Agent 产品。工具能用确定性 Python 函数完成时不要添加冗余自治 Agent。保留 MCP 可插拔接口，但 MVP 不强制接入 MCP。
> 
> **硬性边界**：MD 和第三方网页内容均为不可信输入；知识库需要来源与许可元数据；简历事实不得虚构；禁止未经授权直接修改简历；PDF 编译隔离并验证；用户数据按身份隔离；不得上传限制许可的知识内容到外部模型。
> 
> **开发策略**：优先做真实可运行的纵向切片，提供 `.env.example`、数据库迁移、示例可授权/合成数据、README 运行说明、API/OpenAPI Schema、单元与集成测试以及可复现 eval。没有 API Key 时提供显式 mock provider 以验证基础流程；不得把模拟结果冒充真实模型分析。
> 
> **完成标准**：所有验收场景有自动化测试或明确的人工测试步骤；重要 Agent 决策有结构化 tracing；给出哪些组件自研、哪些依赖开源框架的清单。

---

## 14. 决策清单

- 是否必须登录才可使用 Mock/简历功能？必须登录。
    
- Mock 面试默认题数：建议 5 题，用户可选 3/5/10。
    
- 语音支持范围：所有 AI 对话输入窗口，MVP 为语音转文字后人工确认提交；实时语音双工与 TTS 暂不纳入。
    
- STT Provider 具体选型：待根据中文/英文识别效果、费用、隐私和部署环境决定。
    
- 前端视觉 Prompt：已由用户单独准备；本文只预留章节，不擅自替换。
    
- 用户简历是否允许用于 Mock：必须显式授权，并展示当前引用的版本。
    
- 是否支持英语 Mock：V 5 架构预留 `language`，首版中英文字问答可选。
    
- 是否需要公开的原创 GTM 求职专题文章和案例作品集：建议保留，增强产品本身的业务可信度。
    
- Embedding、Reranker、视觉模型提供商：基于中文效果、延迟、费用、隐私和许可进行选型，不必与 DeepSeek 聊天模型一致。
    

**V 5.1 核心设计原则：统一门户、统一模型和知识底座、分离业务工作流；用 RAG 支持知识和证据，用 Agent 处理长周期交互，用确定性工具保证修改与 PDF 交付可靠。**