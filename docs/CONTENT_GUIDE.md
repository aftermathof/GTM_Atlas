# 资料展览室与用户简历模板

## 当前接入资料（2026-10-24）

用户提供的 `GTM分类60篇/知识库.json` 指向60篇原创研究笔记，按其原始分类导入；另已从 BOSS直聘采集10份岗位 JD。当前规范化 Markdown 共70篇：

|栏目|导入数|说明|
|---|---:|---|
|面经|30|保留作者、原帖链接、个人自述与阅读边界|
|学习资料|30|保留方法、岗位经验、整理者建议与局限|
|岗位 JD|10|保留 BOSS 原始链接、完整 JD、J01–J10 编号及匹配边界，不从面经推测岗位要求|

三个目录统一为 `knowledge/jobs/research-notes/research-jNN.md`、`knowledge/interviews/research-notes/research-iNN.md` 和 `knowledge/learning/research-notes/research-lNN.md`。每篇包含 frontmatter、内容概述、实质正文和阅读边界；JD 保留完整原文一次，不重复摘录同一段。知识源中不保留汇总、合集或采集 manifest。原60篇研究笔记的导入记录见 `docs/archive/import-reports/research-notes.json`，它只记录当时的研究笔记导入，不是当前全部知识数量。岗位/行业标签属于检索辅助信息，不代表专家核定。

网页 `/learn` 默认打开GTM概览；栏目依次为GTM概览、岗位JD、在职经验、GTM专有名词库。面经仅在 `/interviews` 展示。资料栏目支持卡片、搜索与岗位/行业过滤。早期合成资料已移至测试夹具，不进入正式知识库。`/interviews` 使用同一资料底座，继续提供Mock入口。VitePress手册同步构建全部公开学习笔记。

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
- `preamble.tex`：保留原字体回退、紫色、页边距与组件命令；使用真正的 Font Awesome 图标，不以字母替代。
- `resume.tex.j2`：受控正文映射；个人信息与教育分栏、项目、实习/工作、技能、自我评价及其他经历。缺少项目经历、自我评价时保留空白编辑块，留空不导出空标题。
- `metadata.json`：模板标识、版本与原件哈希。
- `templates/latex/sections.tex.j2`：四套模板共用的经历抬头与正文分点。
- `packages/document_renderer/layout.py`：清理重复标题、合并识别续行、拆分技能类别，将正文映射到模板字段。
- `packages/career/photo.py`：从原件保留独立照片；照片随私有版本送入隔离编译目录。
- `infra/renderer-fonts/`：模板必需的 Font Awesome 字体与支持文件，包含来源和许可证，不是临时缓存。

Live模式调用文本模型提取姓名、邮箱、电话、求职意向及每条事实的栏目。提取值必须逐字对应给定事实，每个事实必须有且仅有一个归属；漏项、未知来源或新造值会被拦截。未配置模型时明确报错，不返回模拟归类。用户可校对关键字段与段落归属后确认。正文按来源事实完整填入相应栏目，不让模型直接改写TeX。

改写采用岗位导向的共同编辑：结合用户需求、目标 JD、当前草稿与历史对话，直接生成完整候选稿，可补充职责方向、方法、工具与交付物。原文不是内容上限；用户在对话中补充的内容与数字可直接采用，不再受原文数字集合限制。推演的新增方向在分析中简短提示核对，用户确认替换后再生成版本；锁定段落、修改范围和账号隔离检查保留。

## 模板维护与验证

修改模板正文后重新构建 API；修改字体、编译依赖或 Worker 代码后同步构建 renderer：

```powershell
docker compose -f infra/compose.production.yaml up -d --build api renderer
```

实际下载并查看 PDF，核对照片、图标、学校和经历抬头、工作分点与技能分类。验证空白模块不会导出空标题，段落不会被物理换行拆成碎片。测试入口及完整验收场景见 [功能验收](ACCEPTANCE.md)。

仅在本机 Python API 开发模式下使用 `infra/compose.renderer-local.yaml`。它挂载 `.data/artifacts` 与 `.data/render-queue`；不能和另一 Worker 同时消费同一队列。生产 Supabase 模式使用 `infra/compose.production.yaml`，部署方式见 [部署指南](DEPLOYMENT.md)。

## GTM 名词库与概览

知识中心 `/learn` 默认打开「GTM 概览」，依次提供岗位JD、在职经验和「GTM 专有名词库」。可直接访问 `/learn?kind=glossary`、`/learn?kind=overview`。

- 名词库为名词/解释两列，首批 18 项。编辑唯一数据源 `knowledge/glossary/gtm-glossary.json` 追加条目，每项包含 `term`、`fullName`、`explanation`、`example`；`apps/web/src/content/gtm-glossary.ts` 仅导出该数据，页面与 AI 共用原始内容。
- 概览使用用户提供的 `GTM_HTML学习资料/index.html`，连同四个章节维护于 `knowledge/site/gtm-overview/`，复制校验见 `docs/archive/import-reports/gtm-overview.json`。保留原内容、版式、章节与返回目录链接，不依赖用户电脑的绝对路径。
- 概览嵌入分类页面，也提供「打开完整页面」入口。HTML 将随 Vite 静态构建发布，Vercel 和本地预览都使用 `/gtm-overview/` 地址。

名词库在栏目内使用可滚动框预览，通过「打开完整页面」进入 `/glossary`。预览和完整页面复用同一份术语数据。

API 启动时从概览 `index.html` 和四个章节的 `<main>` 提取标题、段落、列表及图表文字，并从名词 JSON 提取解释与示例。样式、脚本、导航与页脚不入库，不执行 HTML。它们作为 `site_reference` 文档参与检索与引用，点击引用可阅读全文并打开对应原页面；不会出现在 JD、面经、在职经验卡片中。源文件内容哈希未变化时跳过重建；修改后下次入库更新，删除对应源文件后下次入库撤销索引。通用参考资料不受岗位、行业筛选排除，但仍受公共许可与文档范围约束。

维护概览只需改原 HTML，维护名词库只需改 JSON，不要另存一份手写 Markdown 副本。原有文章场景仍优先检索当前文章，面经场景保留面经范围；全局助手可跨全部公共资料检索。简历改写使用资料中的岗位职责、方法和交付物构思候选内容，新增方向的采用与修改由用户决定。

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


## 资料阅读与前端缓存

JD、面经和在职经验共用 `apps/web/src/components/ArticleBody.vue`，目录从正文实际渲染的二、三级标题生成。资料卡片不显示预计阅读时长。

列表与已打开的全文保存在当前网页会话的内存缓存中，返回页面会直接复用；普通 AI 请求不清空资料缓存。切换账号、退出登录和资料上传后按需失效，缓存不写入浏览器持久存储。更新知识文件并让 API 重新入库后，可点击列表中的「刷新资料」或刷新网页获取新内容。

在职经验与 JD 不再默认显示本次移除的开头提示；各资料的来源、质量标记和阅读边界仍按原内容保留。
