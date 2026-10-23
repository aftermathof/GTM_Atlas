# 资料展览室与用户简历模板

## 本次接入

用户提供的 `GTM分类60篇/知识库.json` 指向60篇原创研究笔记，按其原始分类导入：

|栏目|导入数|说明|
|---|---:|---|
|面经|30|保留作者、原帖链接、个人自述与阅读边界|
|学习资料|30|保留方法、岗位经验、整理者建议与局限|
|JD|0|本目录无独立JD，不从面经推测并伪造正式JD|

`knowledge/learning/research-notes/` 与 `knowledge/interviews/research-notes/` 存储规范化源文件。只添加frontmatter，完整笔记正文保留；未把两份合集重复导入。导入报告与源文件哈希见 `docs/IMPORT_REPORT.json`。岗位/行业标签采用标题、摘要、标签的关键词规则，属于检索辅助标签，不代表专家核定。

网页 `/learn` 默认打开GTM概览；栏目依次为GTM概览、岗位JD、面经、在职经验、GTM专有名词库。资料栏目支持卡片、搜索与岗位/行业过滤。早期合成资料已移至测试夹具，不进入正式知识库。`/interviews` 使用同一资料底座，继续提供Mock入口。VitePress手册同步构建全部公开学习笔记。

## 后续补充

相同格式研究笔记更新后重新导入：

```powershell
.venv/Scripts/python -m packages.rag.import_notes --source 'C:\Users\64954\Documents\Codex\2026-10-22\new-chat-2\outputs\GTM分类60篇'
```

相同来源ID覆盖其规范化版本，不产生重复条目；不改动外部原始目录。删除来源后若需要撤销展示，应同时移除 `knowledge/` 中对应规范化文件，再重建索引与网页。新增正式JD或其他资料，可在相应目录添加带合法frontmatter的Markdown，`kind` 分别为 `jd`、`interview`、`learning`。未明确可展示/传给模型的资料不要标记为 `public_display`。

重启API即可执行索引增量更新。构建前端与手册：

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

- 名词库为名词/解释两列，首批 18 项。编辑 `apps/web/src/content/gtm-glossary.ts` 追加条目，每项包含名词、全称、解释和例子，重新构建后展示。
- 概览使用用户提供的 `GTM_HTML学习资料/index.html`，连同四个章节原样复制到 `apps/web/public/gtm-overview/`，复制校验见 `docs/GTM_OVERVIEW_IMPORT.json`。保留原内容、版式、章节与返回目录链接，不依赖用户电脑的绝对路径。
- 概览嵌入分类页面，也提供「打开完整页面」入口。HTML 将随 Vite 静态构建发布，Vercel 和本地预览都使用 `/gtm-overview/` 地址。

名词库在栏目内使用可滚动框预览，通过「打开完整页面」进入 `/glossary`。预览和完整页面复用同一份术语数据。

扫描简历可使用支持图像输入的多模态聊天模型，无需单独采购 OCR 产品。现有 `VISION_BASE_URL`、`VISION_API_KEY`、`VISION_MODEL` 用来指定图像识别模型；可与文本模型使用同一服务商及 Key，但被选中的模型必须支持 `image_url` 图片输入。未配置时仍可使用可读 PDF/TXT，或手动录入。
