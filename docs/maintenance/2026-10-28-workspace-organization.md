# GTM desk 目录整理

日期：2026-10-28。

目标：按功能归位前端模块，统一测试入口，清除可再生成的临时文件，更新当前功能与维护文档。

## 执行计划

- [x] 记录整理前的目录、受保护文件哈希与前端测试基线。
- [x] 将前端辅助模块归入 `src/features/{ai,auth,career,knowledge,notes}/`，同步相对导入、测试和文档路径；页面与共享组件保留原目录。
- [x] 将前端回归测试统一到 `apps/web/tests/`，`scripts/` 仅保留手册生成脚本，提供 `npm test`。
- [x] 将已完成的引用功能方案归入 `docs/archive/development/`。
- [x] 更新根 README、目录导航、架构、内容数量、部署及笔记文件夹验收说明。
- [x] 完成前端测试、完整构建、后端测试、资料校验、文档链接和保护文件哈希核对。
- [x] 清除项目 Python 缓存、pytest 缓存和测试临时目录，保留最新前端构建供本机使用。

## 保护范围

不修改业务行为和网页地址。保留私有配置、SQLite 数据库、上传原件、产物和任务队列、采集证据、隧道日志、依赖环境、知识正文、图片、字体、许可证与 TeX 原件。

本机操作清单、清理大小、文件移动映射及哈希校验存于 `.data/maintenance/organization-20261028-*.json`；不包含配置正文。

## 验证命令

```powershell
npm --prefix apps/web test
npm --prefix apps/web run build
.venv/Scripts/python.exe -m pytest -q
.venv/Scripts/python.exe scripts/validate_knowledge.py
git diff --check
```

## 整理结果

- 归位 22 个文件：9 个前端辅助模块、11 个前端测试、2 份已完成开发方案。业务行为、接口与静态网页地址保持不变。
- `apps/web/scripts/` 仅保留手册生成，全部 13 个前端测试文件集中于 `apps/web/tests/`；`npm test` 包含两项 Node 实验参数，避免漏跑已有 VM 与 TypeScript 测试。
- 重写根 README 和目录导航，将详细配置与隧道操作归入部署指南，更新知识数量、SOP、资料管理、笔记文件夹、邮箱验证和找回密码说明。
- 删除 15 个项目缓存／测试临时目录，共 1,092 个文件、94,740,753 字节（约 90.35 MiB）；删除已归档方案留下的空目录。保留当前构建产物供本机使用。
- 985 个受保护文件在整理后哈希一致；包括知识源、图片、模板、领域配置、字体、本机数据与私有环境配置。

## 验证结果

| 检查 | 结果 |
| --- | --- |
| 前端回归 | 146 项通过 |
| 完整前端构建 | Vue 类型检查、Vite 和 VitePress 均通过；手册构建有大文件分块提示 |
| 后端回归（整理时） | 215 项通过，1 项旧规则断言失败；后续处理见下方说明 |
| 知识校验 | 无错误；JD 10、面经 30、在职经验／学习 167 |
| 当前维护文档本地链接 | 12 份文档，无失效链接 |
| 文件归位 | 22 个目标文件存在，旧路径已移除 |
| 受保护文件 | 985 个文件哈希一致 |
| 差异格式检查 | `git diff --check` 通过 |

整理时的失败来自旧测试 `test_entire_mock_completes_and_keeps_followups_bounded`：要求固定步数内完成且每题最多追问一次，与当前运行逻辑不符。后续用户明确不设总步数和每题追问次数上限，已将测试更新为 `test_mock_allows_repeated_followups_and_completes_when_answers_are_sufficient`，覆盖同题连续追问超过七轮、信息充分后推进和最终完成复盘。运行逻辑原本支持此规则，本次仅校正测试与说明；整理阶段的校验结果作为历史记录保留。

本次未部署或重启服务，也未删除 Docker 镜像、容器和数据卷。
