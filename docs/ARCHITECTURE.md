# 架构与实现边界

## 运行结构

```text
浏览器：Vue 3 页面、Markdown/CodeMirror 编辑器、AI 助手
    │ HTTPS API
    ▼
FastAPI：会话认证、对象所有者校验、参数校验、业务路由
    ├─ Supabase Auth / PostgreSQL / 私有 Storage（正式环境）
    ├─ SQLite / 本地文件（独立开发与测试）
    ├─ LLM / STT / Vision / Embedding 兼容接口
    └─ 文件编译队列 → 隔离 PDF Worker → 产物校验 → 私有下载
```

Vercel 托管前端和 VitePress 手册，Docker 承载 API 与 Worker。前端也可由已构建的 FastAPI 本地服务提供。网络、数据库、模型与编译服务分别检查，不以容器启动或单个接口成功推断全流程可用。

## 功能模块

| 位置 | 职责 |
| --- | --- |
| `apps/web/src/features/ai/` | 引用链接、来源编号、AI 显示文本 |
| `apps/web/src/features/auth/` | 路由守卫与登录恢复 |
| `apps/web/src/features/knowledge/` | 资料卡片、合集、排序、分页、概览缓存 |
| `apps/web/src/features/notes/` | 笔记缓存、编辑操作、文件夹过滤和编号 |
| `apps/web/src/features/career/` | 简历与诊断显示文本处理 |
| `apps/web/src/pages/`、`components/` | 路由界面和共享阅读、输入、编辑、确认组件 |
| `apps/web/src/state.ts`、`preload.ts` | API、认证凭证、账号缓存、后台预加载和并发调度 |
| `services/api/` | 认证、DTO、对象权限、持久化、静态页面及文件下载 |
| `packages/agent_core/` | Provider、领域 Skill 与工具注册、状态检查点 |
| `packages/rag/` | 公共知识校验、分块、索引、检索；私有笔记和授权 JD 检索 |
| `packages/learning/` | 检索、模型问答、引用校验和对话保存 |
| `packages/mock/` | 面试规划、逐题反馈、追问和复盘 |
| `packages/career/` | 简历提取、结构与事实、授权改写、状态恢复 |
| `packages/document_renderer/` | 模板填充、TeX 转义、队列、编译结果和 PDF QA |
| `infra/`、`supabase/` | Worker、字体、容器、迁移、反向代理、SQL 与 RLS |

前端业务辅助模块按功能归位；页面和跨功能组件维持统一入口，避免复制共享组件。后端模块导入和根目录配置路径保持稳定。

## 统一 AI 流式输出

同一 AI POST 接口通过 `Accept: text/event-stream` 使用 SSE；原有 JSON 调用保留。`services/api/streaming.py` 复用原始路由的参数校验、权限、流程与事务；`packages/agent_core/streaming.py` 用请求级 ContextVar 传递进度，Provider 直接读取上游 OpenAI 兼容流，不在完整回答后模拟分段。

协议为 `start`、`sources`、`delta`／`replace`、最终 `result` 或 `error`。结构化任务只增量展示可读字符串，原始 JSON 仍由原有业务代码完整校验；只有成功的最终结果更新业务界面。引用以最终校验结果为准，预览不能绕过授权或直接应用到简历。

前端 `features/ai/streaming.ts` 共用 UTF-8 与 SSE 分包解析，`state.ts` 复用认证和缓存失效，`AIStreamPreview.vue` 展示结构化任务预览，ChatPanel 渲染聊天正文。页面离开时取消对应生成请求，账号变化后的旧流不更新新界面。连接中断不自动重放 POST；若业务已完成但最终响应未送达，刷新历史确认状态。

响应使用十秒心跳、禁用代理缓冲和压缩。模型无正文、连接非正常结束、结构化校验失败均不能作为成功结果；正常生成并完成业务事务后才发送 `result`。外部网关仍须正确转发流式响应。

## 内容与检索

`knowledge/` 保存公共 Markdown、HTML、JSON 与配图。前端构建静态页面和手册；API 启动增量检查知识源并构建索引。显示和检索遵循许可及标签，公共参考资料通过 `packages/rag/reference_sources.py` 提取。

未配置 Embedding 时使用词法检索；配置后结合向量和词法结果进行 RRF 融合。向量固定 1536 维，模型或维度变更需相应重建／迁移，不提供伪向量替代。

引用必须属于本次返回的证据。前端按文档统一来源编号，句内链接保留章节位置。研究资料、JD 和上传内容均作为不可信上下文，不授予模型任意代码执行能力。

个人笔记保存为 `business_records.kind=learning_note`，文件夹为 `note_folder`，通过 `folder_id` 关联。列表过滤和编号在当前目录内计算；后端校验文件夹所有者，更新笔记保留归属及版本冲突检查。笔记只供所有者和其授权请求使用，不进入公共 Markdown 或公共向量索引；实时私有关键词检索每次最多提供 6 个片段。

## 会话、缓存与数据

正式环境使用 Supabase 邮箱注册、验证、找回密码和会话刷新；独立开发兼容本地账号。浏览器保存认证凭证，私人正文缓存只在当前页面会话内按账号使用。退出和账号变化使旧缓存不可用，内容修改使相应缓存失效。

问答、Mock、简历事实和版本持久保存。每个私有对象在 API 中检查 owner，数据库配置 RLS，文件使用私有 Storage；服务端凭证不能替代对象权限检查。清空聊天上下文保留历史，但后续请求排除旧轮次。

PDF Worker 使用无网络、非 root、只读根目录与资源限制，通过共享目录消费任务；禁用 shell escape。编译结果须通过事实文本、页数与边界检查，完成后由 API 同步到私有存储。未运行 Worker 时任务等待，不伪造成功。

## 当前边界与验证

- 仍使用单 API 进程限流与单 Worker 文件队列，多副本需要共享限流和任务系统。
- OCR、模型服务、邮件及云端权限依赖实际提供方配置，离线替身不证明真实效果。
- 当前无多人笔记协作、收藏进度或企业 SSO。
- 知识去重与排序不是语义去重或 reranker；检索评测是小型回归集。
- 模板、字体和 PDF 内容调整应查看实际产物；接口成功不等于版式正确。

运行配置见 [部署指南](DEPLOYMENT.md)，回归和实际验收见 [验收清单](ACCEPTANCE.md)。文档不记录当前机器、容器或云账号的在线状态。
