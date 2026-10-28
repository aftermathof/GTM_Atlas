# 网站前端

Vue 3、TypeScript、Vue Router、Vite 与 VitePress。以下命令在仓库根目录执行：

```powershell
npm --prefix apps/web ci
npm --prefix apps/web run dev
npm --prefix apps/web test
npm --prefix apps/web run build
```

开发服务器将 `/api` 代理至 `http://127.0.0.1:8000`。部署时通过 `VITE_API_BASE_URL` 指定公开的 HTTPS API 地址；不要把模型或数据库密钥放入前端变量。

## 功能与目录

| 路径 | 职责 |
| --- | --- |
| `src/features/ai/` | 句内引用与来源编号、AI 文本清理、统一 SSE 读取 |
| `src/features/auth/` | 登录恢复与路由守卫 |
| `src/features/career/` | 简历和诊断文本显示处理 |
| `src/features/knowledge/` | 资料卡片、合集、排序、分页与概览预加载 |
| `src/features/notes/` | 笔记缓存、编辑格式操作、文件夹过滤与独立编号 |
| `src/pages/` | 首页、学习、面试、简历、笔记、账号与辅助页面 |
| `src/components/` | 共享阅读器、笔记编辑器、资料管理、AI 助手、输入与确认弹窗 |
| `src/state.ts` | HTTP 请求、会话、账号状态、资料与历史缓存 |
| `src/preload.ts` | 登录后的跨功能预加载与并发调度 |
| `src/content/` | 从根目录知识源导入术语及 HTML 的入口 |
| `src/style.css`、`src/tokens.css` | 全站样式与设计变量 |
| `tests/` | 全部前端回归测试，统一用 `npm test` 执行 |
| `scripts/handbook.mjs` | 将公开学习资料生成手册文章与索引 |
| `handbook/.vitepress/config.ts` | 手册构建与输出配置 |
| `vite.config.ts` | 共享静态资料、构建与开发 API 代理 |

`npm test` 已包含 Node 22 的 `--experimental-strip-types` 与 `--experimental-vm-modules` 参数；不再从 `scripts/` 搜索测试。文件归位时同步修改源码导入及测试中的加载路径。

## 内容源与生成结果

网站正文维护在 [../../knowledge/](../../knowledge/)：概览、全书、SOP 与配图在 `site/`，术语在 `glossary/`，Markdown 按岗位、面经和学习分类。`vite.config.ts` 使用根目录的 `knowledge/site/`，静态网页地址不随前端模块归位而改变。

`node_modules/` 是依赖环境。`dist/`、`handbook/articles/`、`handbook/.generated.json` 和 VitePress 缓存是生成内容，修改正文应回到知识源；完整构建会重建前端和手册。`npm run handbook` 先生成文章，再启动手册开发服务。

学习笔记：`pages/Notes.vue` 负责页面，`features/notes/` 负责缓存、编辑与编号，`components/NoteEditor.vue` 负责 CodeMirror 编辑器。文件夹和笔记保存到 API，不能用浏览器临时数据代替持久化。

AI 生成调用使用 `post(path, body, onProgress, signal?)`。有进度回调时请求同一路径的 SSE 响应，`state.ts` 处理最终业务结果与缓存，`features/ai/streaming.ts` 处理分包、心跳和中断。聊天直接增量渲染 Markdown；结构化任务使用 `components/AIStreamPreview.vue`，收到最终校验结果前不回填、不推进。失败时保留输入，离开页面取消请求。

部署见 [部署指南](../../docs/DEPLOYMENT.md)，全项目目录见 [维护入口](../../docs/README.md)。
