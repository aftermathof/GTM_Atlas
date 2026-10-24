# 资料展览室与用户简历模板

## 当前接入资料（2026-10-24）

用户提供的 `GTM分类60篇/知识库.json` 指向60篇原创研究笔记，按其原始分类导入；另已从 BOSS直聘采集10份岗位 JD。当前规范化 Markdown 共70篇：

|栏目|导入数|说明|
|---|---:|---|
|面经|30|保留作者、原帖链接、个人自述与阅读边界|
|学习资料|30|保留方法、岗位经验、整理者建议与局限|
|岗位 JD|10|保留 BOSS 原始链接、完整 JD、J01–J10 编号及匹配边界，不从面经推测岗位要求|

三个目录统一为 `knowledge/jobs/research-notes/research-jNN.md`、`knowledge/interviews/research-notes/research-iNN.md` 和 `knowledge/learning/research-notes/research-lNN.md`。每篇包含 frontmatter、内容概述、实质正文和阅读边界；JD 保留完整原文一次，不重复摘录同一段。知识源中不保留汇总、合集或采集 manifest。原60篇研究笔记的导入记录见 `docs/IMPORT_REPORT.json`，它只记录当时的研究笔记导入，不是当前全部知识数量。岗位/行业标签属于检索辅助信息，不代表专家核定。

网页 `/learn` 默认打开GTM概览；栏目依次为GTM概览、岗位JD、面经、在职经验、GTM专有名词库。资料栏目支持卡片、搜索与岗位/行业过滤。早期合成资料已移至测试夹具，不进入正式知识库。`/interviews` 使用同一资料底座，继续提供Mock入口。VitePress手册同步构建全部公开学习笔记。

## 后续补充

相同格式研究笔记更新后重新导入：

```powershell
.venv/Scripts/python -m packages.rag.import_notes --source 'C:\Users\64954\Documents\Codex\2026-10-22\new-chat-2\outputs\GTM分类60篇'
```

相同来源ID覆盖其规范化版本，不产生重复条目；不改动外部原始目录。删除来源后若需要撤销展示，应同时移除 `knowledge/` 中对应规范化文件，再重建索引与网页。新增正式JD或其他资料，可在相应目录添加带合法frontmatter的Markdown，`kind` 分别为 `jd`、`interview`、`learning`。未明确可展示/传给模型的资料不要标记为 `public_display`。

本地直接运行 Python API 时，重启 API 即可执行索引增量更新。生产 Docker 把资料打包在镜像中，修改资料后需从项目根目录执行 `docker compose -f infra/compose.production.yaml up -d --build api`；只重启旧容器不会复制新文件。构建前端与手册：

```powershell
cd apps/web
npm run build
```

## 用户上传目标JD

简历页支持UTF-8 TXT、Markdown、可读文本PDF，最大2MB、10页、10–8000字。文件保持私有，上传后可校对正文。校对后的JD优先用于本次诊断/检索/改写；原始JD保留为来源，不写入公共知识索引。登录用户可在JD栏目阅读自己的上传内容，并通过「以此JD定制简历」建立新的简历会话。

私有JD的详情、问答与简历引用均按所有者检查。未登录或其他用户不能读取，公共知识搜索不会返回它。RAG合并当前用户JD、实际岗位文档、学习框架与面经参考；合成示例不参与简历RAG。

## 模板与关键字段

- `templates/latex/gtm-original/source.tex`：用户原件，SHA256 `f621d00d5a943f05384b5394d1754ce777250e55a539ef2e478ee547a8889faf`。
- `preamble.tex`：保留原字体回退、紫色、页边距与组件命令；仅增加缺少fontawesome5包时的图标回退。
- `resume.tex.j2`：受控正文映射；个人信息与教育分栏、项目、实习/工作、技能、自我评价及其他经历。未识别内容保留，不补全空字段。
- `metadata.json`：模板标识、版本与原件哈希。

Live模式调用文本模型提取姓名、邮箱、电话、求职意向及每条事实的栏目。提取值必须逐字对应给定事实，每个事实必须有且仅有一个归属；漏项、未知来源或新造值会被拦截。未配置模型时明确报错，不返回模拟归类。用户可校对关键字段与段落归属后确认。正文按来源事实完整填入相应栏目，不让模型直接改写TeX。

改写重点是项目与实际经历：明确已有用户洞察、市场分析、产品/内容、数据和协作行动如何对应目标岗位。JD和他人面经不能变成候选人的经历。锁定段落、授权检查和禁止新增数字规则持续生效；复杂语义仍须人工复核。

## 本轮验证

- 60份笔记导入数、幂等、正文与哈希核对。
- 原件TeX哈希一致；合成简历生成的用户模板通过桌面编译器实际编译。
- 字段完整映射、未知/虚构提取拒绝、用户JD隔离与RAG证据测试。
- 浏览器实测：卡片打开全文；登录、JD上传、简历上传、字段与段落校对、选择项目/实习、生成建议、授权生成用户模板版本。
- 当前23项后端测试通过；前端类型、Vite与VitePress构建通过，最新运行结果以终端为准。

尚未配置真实LLM/STT/Vision/Embedding密钥，真实模型效果需配置后复测。合成样例的模板已实编译，不等于Docker隔离PDF Worker集成已验收；网页PDF按钮仍在Worker完成QA后才可用。

若继续使用当前本机SQLite API，Docker启动后可仅运行隔离Renderer，沿用已有版本与任务：

```powershell
docker compose -f infra/compose.renderer-local.yaml up --build
```

该配置只挂载本项目 `.data/artifacts` 与 `.data/render-queue`，不切换数据库、不挂载原始上传目录。它仍需要Docker并待实际集成验证。完整PostgreSQL栈另用 `infra/compose.yaml`，两者请选择一种Renderer运行方式，避免同时消费同一任务队列。

## GTM 名词库与概览

知识中心 `/learn` 默认打开「GTM 概览」，依次提供岗位JD、面经、在职经验和「GTM 专有名词库」。可直接访问 `/learn?kind=glossary`、`/learn?kind=overview`。

- 名词库为名词/解释两列，首批 18 项。编辑唯一数据源 `apps/web/src/content/gtm-glossary.json` 追加条目，每项包含 `term`、`fullName`、`explanation`、`example`；`gtm-glossary.ts` 仅导出该数据，页面与 AI 共用原始内容。
- 概览使用用户提供的 `GTM_HTML学习资料/index.html`，连同四个章节原样复制到 `apps/web/public/gtm-overview/`，复制校验见 `docs/GTM_OVERVIEW_IMPORT.json`。保留原内容、版式、章节与返回目录链接，不依赖用户电脑的绝对路径。
- 概览嵌入分类页面，也提供「打开完整页面」入口。HTML 将随 Vite 静态构建发布，Vercel 和本地预览都使用 `/gtm-overview/` 地址。

名词库在栏目内使用可滚动框预览，通过「打开完整页面」进入 `/glossary`。预览和完整页面复用同一份术语数据。

API 启动时从概览 `index.html` 和四个章节的 `<main>` 提取标题、段落、列表及图表文字，并从名词 JSON 提取解释与示例。样式、脚本、导航与页脚不入库，不执行 HTML。它们作为 `site_reference` 文档参与检索与引用，点击引用可阅读全文并打开对应原页面；不会出现在 JD、面经、在职经验卡片中。源文件内容哈希未变化时跳过重建；修改后下次入库更新，删除对应源文件后下次入库撤销索引。通用参考资料不受岗位、行业筛选排除，但仍受公共许可与文档范围约束。

维护概览只需改原 HTML，维护名词库只需改 JSON，不要另存一份手写 Markdown 副本。原有文章场景仍优先检索当前文章，面经场景保留面经范围；全局助手可跨全部公共资料检索。简历上下文中的资料只是参考，不能成为用户的真实经历。

## 后续 Markdown CRUD 统一规范

两个可单独引用的采集 Skill：

- [BOSS 岗位 JD 采集与维护](collector-skills/boss-jd-collector/SKILL.md)
- [小红书面经与在职经验研究笔记](collector-skills/xiaohongshu-research-collector/SKILL.md)

它们是项目维护用的工作流文档，不加入应用根目录 `skills/` 的受控注册表。原始参考 Skill 保持不变，后续采集使用这两个修订版。

### 目录、编号与稳定身份

|类别|kind|显示编号|新增文件默认位置|
|---|---|---|---|
|岗位 JD|`jd`|J01、J02…|`knowledge/jobs/research-notes/research-jNN.md`|
|面经|`interview`|I01、I02…|`knowledge/interviews/research-notes/research-iNN.md`|
|学习／在职经验|`learning`|L01、L02…|`knowledge/learning/research-notes/research-lNN.md`|

每个前缀独立续号，数字至少两位；超过99后自然增长，界面按数字而非文本顺序排列。先扫描已有资料和删除记录，再从已使用最大值加一分配；删除保留空号、不复用、不重排。`id` 是稳定记录身份，`source_note_id` 是卡片编号，二者不能混用。更新保留原 id 和编号，已规范化的文件原位更新；目录整理不改变文档身份、不保留重复副本。明确授权的跨类调整需记录旧编号停用与新编号，确保同一来源只保留一个主笔记。

按平台稳定来源 ID 去重：BOSS 使用 `source_job_id`，小红书使用 `source_id`；旧笔记可从规范 `source_url` 提取。小红书同时跨 `learning/` 和 `interviews/` 排查重复。链接保留规范来源，不含 securityId、xsec_token、Cookie 等会话信息。

### 单篇 YAML 契约

|字段|要求|
|---|---|
|`id`、`title`|全库唯一稳定 ID、真实中文或原文标题；ID 仅字母、数字、短横线、下划线，最长100字符|
|`kind`|只使用 `jd`、`interview`、`learning`|
|`source_note_id`|与 kind 对应的 J/I/L 显示编号，全库唯一|
|`permission`|已授权进入项目公共资料的单篇使用 `public_display`；私人材料不进入公共目录|
|`quality_status`|已核对 JD 详情用 `source_verified`；小红书人物经验仍用 `unverified`，不把来源可读当作主张已核实|
|`source_type`|JD 使用 `job_posting`；小红书原创整理使用 `original_research_note`|
|`source_url`、`source_author`|可溯源链接、公司或页面作者昵称，不记录招聘者私人联系方式|
|`collected_at`、`displayed_date`|真实采集时间、页面原样日期；缺失日期为 YAML null，不猜年份|
|`role_tags`、`industry_tags`|项目词表中的字符串列表，未知行业用空列表|
|`tags`、`excerpt`|字符串标签列表、能说明内容与边界的实质摘要|
|`limitations`、`content_notice`|来源局限列表与阅读提示，区分自述、推断及整理者建议|

正文使用一个一级标题和清晰的二级标题，保持 UTF-8。JD 将完整原文保存一次，职责／要求等来源小标题在原文中保留，避免再次全文复制导致检索重复。小红书沿用现有研究笔记的内容概述、来源内容整理、问题方向／方法经验、整理者建议、阅读边界；不把 OCR 全文拼成第三方原帖镜像。图片确有文字信息时核对，不读取评论，不以标题和链接替代正文。

### 校验、修改、删除与服务同步

1. 新增或更新先在 `outputs/collections/<批次>/` 暂存，核对来源、去重、编号和元数据。更新保留可恢复旧版；只在用户指定范围内删除，保留来源 ID 与停用编号的审计记录。
2. 校验后原子落盘至单篇目录。汇总、合集、报告、OCR、图片和 manifest 留在 `outputs/collections/`，不进入 `knowledge/`。三个知识分类均只保留规范化单篇 Markdown。
3. 在项目根目录运行 `.venv/Scripts/python -m scripts.validate_knowledge`。它检查全部现有 Markdown 的 YAML、必需字段、编号、类别、来源去重与会话参数；不代替人工核实来源和事实。
4. 需要同步运行服务时重建 API 镜像；启动成功后检查接口中的资料数量、编号顺序和引用。初始化 SQL 不重复执行。前端源码修改按前端构建/部署流程另行处理，`git push` 与本机 Docker 更新分别记录。

删除文件或撤销公共许可只会在下一次成功入库后从知识索引撤销，不会自动删除用户已保存的历史问答。文件交付、索引成功、服务可用和代码已推送是不同状态，交付报告分别说明。

扫描简历可使用支持图像输入的多模态聊天模型，无需单独采购 OCR 产品。现有 `VISION_BASE_URL`、`VISION_API_KEY`、`VISION_MODEL` 用来指定图像识别模型；可与文本模型使用同一服务商及 Key，但被选中的模型必须支持 `image_url` 图片输入。未配置时仍可使用可读 PDF/TXT，或手动录入。
