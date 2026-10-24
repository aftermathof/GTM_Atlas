# 网站前端

从项目根目录进入 `apps/web`，运行 `npm run dev` 开发、`npm run build` 构建。

| 目录或文件 | 用途 |
| --- | --- |
| `src/pages/` | 首页、知识学习、面经与 Mock、简历、我的空间 |
| `src/components/` | 共享阅读器、AI 助手、输入框和改写对话框 |
| `src/state.ts` | API 请求、登录状态、会话和资料缓存 |
| `src/style.css`、`src/tokens.css` | 全站样式与设计变量 |
| `src/content/gtm-glossary.ts` | 引用根目录名词库的前端入口 |
| `scripts/` | 手册生成与前端测试 |
| `handbook/` | VitePress 手册配置及生成结果 |
| `vite.config.ts` | 构建、静态资料目录与开发 API 代理 |

GTM 概览原件在 [../../knowledge/site/gtm-overview/](../../knowledge/site/gtm-overview/)，名词库在 [../../knowledge/glossary/](../../knowledge/glossary/)。Markdown 正文也统一在根目录 `knowledge/`，不要编辑 `dist/` 或自动生成的手册文章。

`node_modules/` 是安装依赖；`dist/` 是构建结果。页面部署与后端启动见 [部署指南](../../docs/DEPLOYMENT.md)。
