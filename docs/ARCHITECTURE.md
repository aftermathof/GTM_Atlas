# 架构与实现边界

## 自研模块

|目录|职责|
|---|---|
|apps/web/src|Vue门户、统一VoiceInput/Composer、作用域助手、三类工作台|
|apps/web/handbook|VitePress生成知识手册，只发布public_display；构建清理撤销的生成文件|
|services/api|认证、对象级鉴权、请求DTO、业务API、审计、下载、静态站点|
|packages/agent_core|独立LLM/STT/Embedding Provider、受控Skill Registry、ToolRegistry/MCPAdapter、SQL checkpoint|
|packages/rag|frontmatter校验、SHA256、标题chunk、许可与岗位过滤、FTS/向量RRF、证据包|
|packages/learning|retrieve → compose → citation validate 状态图|
|packages/mock|固定蓝图/真实模型规划、逐题评价、有界追问、幂等记录、复盘|
|packages/career|解析、诊断、patch验证、LangGraph持久interrupt/resume审批|
|packages/document_renderer|受控模板、TeX转义、文件队列、隔离编译与PDF QA|

## 开源框架承担什么

- FastAPI/Pydantic：HTTP、OpenAPI、类型校验；不代替业务权限。
- LangGraph：有状态节点与checkpoint、interrupt/resume；图与授权约束由本项目实现。
- SQLAlchemy/Alembic：关系持久化与迁移；PG/pgvector存储向量，原生FTS做词法信号。
- Vue/Vite/Vue Router：交互工作台；VitePress：同源可搜索知识手册。不是三个单独站点。
- PyMuPDF：PDF文字提取和QA；Jinja2：受控模板；XeLaTeX/ctex：隔离排版。
- marked/DOMPurify/Mermaid：受净化Markdown及受限图表；不执行文档脚本。

## 状态与恢复

Mock业务记录、回答幂等响应、题目及评价保存数据库；每次评价的LangGraph节点也有持久checkpoint。答案按题目索引检查，在事务内推进。SQLite单进程锁，PostgreSQL行锁。API可重建并继续原会话；已有相同幂等键返回原响应，不重复推进。

简历的事实确认和段落批准使用持久LangGraph interrupt/resume。HTTP端点同样检查确认状态、所有者、段落授权、锁定及数字保真。每个版本持有独立审批thread；render不由AI聊天自动调用。应用层版本不可变，回滚只改变活动指针。

首版用 `business_records` 存储有类型的私有aggregate、checkpoint、审计、版本与job，知识文档和chunk独立表。没有把需求中的每一种业务实体机械拆成一张表；扩展高并发前可按查询与事务边界逐步拆表。私有owner不会由客户端指定。

## 许可与模型信任边界

受限资料首版不索引，不发送模型；检索在任何向量/模型调用之前完成许可与标签过滤。Embedding只对public_display文本处理。来源、用户文件和JD均包装为不可信数据；模型没有代码/任意工具执行通道。引用必须对应返回chunk；缺失或伪造引用拦截回答。

在没有Embedding服务时，只提供词法开发模式；真实语义检索没有伪向量替代。STT未配置不生成假转写。扫描件未配置Vision不伪造事实，可手动校对。未运行Renderer不伪造PDF成功。

## 尚需真实环境验证或进一步建设

1. 用户模板的合成样例已由桌面编译器实际编译成功；当前机器Docker未运行，PostgreSQL迁移、pgvector与隔离XeLaTeX Worker仍未完成集成验证。
2. 未提供真实LLM/STT/Vision/Embedding配置，真实供应商的兼容性、准确率、耗时与数据保留政策待验证。
3. OCR/模型调用目前是有超时的同步请求；PDF使用单Worker文件队列。高并发OCR/长报告应迁移通用持久异步Job队列。
4. 未实现SSE流式回答、单题重试分支、通用会话导出、收藏/阅读进度与答案反馈统计。
5. 实现精确正文去重，未做语义近重复清理和reranker；向量升级通过模型名触发重建，跨模型维度变化须迁移。
6. 角色基础rubric仍是首版通用权重，非经过专家审核的细分岗位评分体系。真实内容扩充、人工标注评测与对照实验仍需后续工作。
7. 登录是邮箱密码基础认证，无邮件验证、重置密码、共享限流或企业SSO；公开部署前需要运维与身份强化。

这些是当前交付边界，不能以单元测试或演示Provider宣称已完成生产验收。
