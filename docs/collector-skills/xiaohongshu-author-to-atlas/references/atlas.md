# Atlas 入库、批次格式与运行验收

## 路径和单篇

先读当前项目内容维护指南和 ingest/build 代码，不硬编码本机路径。通常：

- 学习：knowledge/learning/research-notes/research-lNN.md；面经：knowledge/interviews/research-notes/research-iNN.md。
- 图片：knowledge/site/xhs-author-assets/<内容哈希>.<实际格式>；Markdown 使用 /xhs-author-assets/... 根路径。实际 publicDir、base 和路由应从代码验证。
- 原始证据、OCR、报告、manifest 均在项目外批次 work/ 或交付目录，不放 knowledge/。即便 knowledge/site/ 下的裸 Markdown 也可能被递归摄入，导致缺 frontmatter 错误。

模板中的示例值必须替换，标签使用项目词表。quality_status 不因成功访问就升级。

```markdown
---
id: research-l08
title: 示例业务复盘
kind: learning
permission: public_display
quality_status: unverified
source_type: original_research_note
source_note_id: L08
source_id: bbbbbbbbbbbbbbbbbbbbbbbb
source_url: https://www.xiaohongshu.com/explore/bbbbbbbbbbbbbbbbbbbbbbbb
source_author: 示例博主
role_tags: [gtm]
industry_tags: []
tags: [业务复盘]
collected_at: '本次带时区的 ISO 时间'
displayed_date: null
excerpt: 以独立语言概括具体情境、信息价值和适用边界。
limitations:
  - 作者自述未独立核实。
content_notice: ''
source_author_id: aaaaaaaaaaaaaaaaaaaaaaaa
author_collection_id: xhs-aaaaaaaaaaaaaaaaaaaaaaaa
author_collection_title: 示例博主
---
# 示例业务复盘

## 内容概述

填写实质概述。

## 来源内容整理

按独立主题写来源支持的情境、步骤、交付物和局限。

## 图片补充与保留图表

仅在有 keep 原图时提供；每张图配简短标题和必要说明，不把正文再重复一次。无图时省略本节。
```

新批次默认精简正文，具体页面布局与合集展示编号见 [前端页面与内容格式](frontend.md)。稳定 L 编号不从 1 重置；author_collection_id 由平台及核验后的作者 ID 构成，不能使用易变昵称或批次日期。上述 ID 均为示例。

## 辅助工具与批次 schema

Python 需 PyYAML；Pillow 用于图片解码校验。优先使用已有项目解释器，缺依赖按当前环境允许方式安装。没有 Pillow 时脚本会报告 image_decoder_available=false，此时必须另做图片实际打开检查。工具不抓浏览器、不调用模型、不修改知识库、不发布。

批次目录：manifest.json、project-scan.json、notes/、assets/、work/。以下是本 skill 的 schema，不能直接套用旧单次采集脚本的 manifest。

```json
{
  "author": "示例博主",
  "author_profile_id": "aaaaaaaaaaaaaaaaaaaaaaaa",
  "author_collection_id": "xhs-aaaaaaaaaaaaaaaaaaaaaaaa",
  "content_format": "concise",
  "asset_url_prefix": "/xhs-author-assets/",
  "inventory_file": "work/inventory.json",
  "snapshot_file": "project-scan.json",
  "posts": [{
    "source_id": "bbbbbbbbbbbbbbbbbbbbbbbb",
    "source_url": "https://www.xiaohongshu.com/explore/bbbbbbbbbbbbbbbbbbbbbbbb",
    "title": "示例业务复盘",
    "status": "staged",
    "source_note_id": "L08",
    "note_file": "notes/research-l08.md",
    "images": [{
      "index": 1,
      "decision": "keep",
      "reason": "展示正文没有的字段关系。",
      "file": "assets/图像内容哈希.png",
      "sha256": "实际完整SHA256"
    }]
  }]
}
```

inventory.json 为对象数组，每项含 id 或 source_id，列出全部发现项；所有项须在 manifest 对账。snapshot_file 指向采集前 scan 输出。正式批次两项都应提供，否则脚本无法验证清单覆盖和旧文件保护。非 staged 帖不用 note_file，failed/excluded 必须有 reason；非 keep 图不用 file，原始缓存仍可保留在 work/。

scan 扫描现存知识、来源和编号，--git-history 纳入 Git 删除/历史编号，--reserved 可纳入一个旧 manifest 中的 source_note_id、numbers、reserved_numbers。多个历史批次先汇总预留清单。history_checked=false 不能当作已核验。

validate 检查身份、元数据、编号/来源冲突、原始文件哈希、图像哈希/解码/引用和清单对账；concise 模式还检查作者合集身份、空 content_notice 及不含两个已移除章节。未指定 content_format 的旧批次保持 legacy 规则（包括旧阅读边界章节），不要漏写字段导致精简稿误走旧规则。--published 检查项目副本完全一致。退出码 0 是结构无错误，complete=false 仍代表有失败或待处理。即便 complete=true 也不证明浏览器清单真的全量或语义审图正确。

先校验，新增文件写临时文件再原子改名，不覆盖既有文件；只导入 keep 资源，已有同名资源先比较哈希。不要把临时/原始目录整体复制进去。更新旧文档另走项目更新流程。

## 项目构建与页面

从项目根目录用项目解释器运行 python -m scripts.validate_knowledge；从 apps/web 按实际 package.json 运行受影响的前端和手册构建。

主应用和 VitePress 可能共同消费静态资源。手册构建若把 /xhs-author-assets/... 当作模块导入而找不到资源，应修生成器而非逐篇生成文档。曾验证的方法是在生成阶段把限定资源前缀的 Markdown 图片转成运行时绑定的 img，alt 先 HTML 转义，例如 `<img :src="'/xhs-author-assets/HASH.webp'" alt="安全转义文本" loading="lazy">`。须适配当前 base/publicDir，验证共享资源实际可达，不凭构建通过假定发布路径正确。

图片 CSS 使用 max-width:100%、height:auto，桌面和移动端核对长图宽高比。若新增资源不影响代码，无需为了本次采集改造前端。

列表 API 若每页最多 100 条，前端计数/搜索/最后一项要检查所有 offset 页，不能只用第一页缓存；并发响应采用请求代次保护，避免旧请求覆盖新结果。只在实际出现此问题且用户范围允许时修改代码。

## 服务与 RAG

文件交付不等于索引运行。仅在本次或既有会话授权同步服务时，检查实际 Docker labels、compose 和配置；不能硬编码旧容器名。镜像打包知识源的项目需要重建相应服务，不能只改宿主文件。不要重新初始化数据库、清空个人数据、主动 git push 或发布前端。

若向量重建耗时，优先利用项目现有且获准的维护路径预索引，让旧 API 尽量保持服务；避免并行启动多个带删除同步的 ingest 进程而相互删除数据。没有可靠维护路径则按真实停机窗口操作并报告。

Started/running 不等于 ready，长初始向量索引可超过健康宽限期。看日志进度、重启次数、网络和实际数据，再判断是否故障；不要反复重启重跑嵌入，也不要为健康变绿关闭向量检索。

运行验收：

1. 真实健康接口 status ok；核对日志无持续错误。
2. 分页读取所有新增 ID，数量对账，抽查单篇和图片引用。
3. 用新笔记的具体主题实际查询 RAG，确认返回新 doc ID/来源；启用向量时核对向量索引状态，只配置词法时如实说明。
4. 浏览器抽查桌面/移动端、长图、最后一项及超过单页上限时的完整列表。
5. 保护既有文件哈希；分别报告源码、索引、健康、构建、远端发布五种状态。

本 skill 的安装、离线验证或文件复制不能作为上述运行验收证据。
