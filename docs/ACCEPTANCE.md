# V5.1 验收映射

自动化执行 `python -m pytest -q`；真实外部能力需要按下列步骤人工复测。

|plan.md 场景|自动化/人工覆盖|当前状态|
|---|---|---|
|1 学习页比较渠道与KOL|test_knowledge_permissions_and_citations；浏览器实际问答点击来源|本地已验证|
|2 KOL消费电子5题/3维度/种子|test_mock_seed_idempotency_and_ownership|已验证固定题池|
|3 简历真实AI运营追问|test_unauthorized_resume_context_and_artifacts|合成事实测试通过；真实模型未配置|
|4 扫描PDF与低置信字段|test_scan_requires_ocr_or_manual_confirmation；配置Vision上传扫描件核对page/confidence|退化已测，真实OCR待测|
|5 只诊断不生成|test_resume_confirmation_authorization_and_versions、test_ai_suggestion_does_not_create_version|已验证|
|6 授权段落、锁定教育、PDF|test_locked_education_cannot_be_rewritten、test_version_rollback_and_artifacts_remain_private|授权与TeX已测；隔离PDF待Docker|
|7 回滚只保留技能修改|版本测试检查教育保留、旧版保留、活动指针回滚；编辑器选择基础版只授权技能栏生成|API已验证，人工组合按此步骤复核|
|8 非法许可/用户隔离|test_forbidden_and_deleted_documents_never_searchable、私有API与下载隔离测试|已验证首版保守许可|
|9 重启恢复/幂等|test_restart_restores_session_and_duplicate_response|已验证SQLite文件持久化|
|10 缺少证据不编引用|知识不足与test_forged_citation_is_blocked|已验证|
|11 四类输入录音→转写→确认|学习/全局、面经、Mock、简历均复用Composer|组件已接入；真实STT/麦克风待测|
|12 校对后评分/修改|后端只接收已提交文字；建议不生成版本测试；确认与审批interrupt|文字边界已测，真实语音待测|

## 语音人工测试（配置STT后）

分别在 `/learn/ask`、文章问答、全局抽屉、Mock每题、简历问答与改写建议输入执行：

1. 保留已有草稿，点击麦克风。未同意第三方传输前不得开始录音。
2. 同意后允许浏览器麦克风，录制中文、英文、中英混合各一段。停止后等待转写，文字追加到原草稿。
3. 校对错字，不点击发送时不能出现回答、评价或新版本。确认提交后才执行文字API。
4. 重复录音并取消，原文字不变；拒绝权限显示可理解提示，键盘仍可使用。
5. 临时停用STT或模拟超时，错误不会清空草稿；重新启用后可重试。
6. 录制至120秒自动停止；超过8MB拒绝处理。检查 `.data` 中无原始音频文件。
7. 简历改写建议生成后仍须明确点击「确认授权并生成新版」，否则版本数量不变。

## PDF人工测试（Docker后）

启动Compose，配置生产PG并迁移。上传合成中文简历，确认事实，授权两段并锁定教育，生成版本。刷新编译状态后预览并下载PDF和TeX。比对姓名、教育、时间、技能和授权段落；页数不超过2页。使用另一账号访问文件应404。

停止Worker再生成一版，网页应显示等待且不提供PDF下载；恢复Worker后任务可继续。超长简历导致QA失败时，不允许下载该PDF，旧版仍可读取。检查renderer `NetworkMode=none`、非root、只读根文件系统、内存/CPU限制与禁用shell-escape。

## 当前验证记录

本地自动化23项通过（后续以最新pytest输出为准）。Vue类型检查、Vite与VitePress生产构建通过。浏览器已实际验证资料展览室与全文、带引用问答、JD/简历上传、字段校对、项目经历选择和用户模板版本生成。用户模板的合成样例已实际编译成功；Docker PDF Worker仍待验证。响应式检查以1440px桌面和390px手机进行。

依赖会输出PyMuPDF、Starlette/AnyIO与LangGraph的弃用提示，不影响当前测试通过；升级依赖应重跑全部测试。未把这些提示隐瞒为零警告。
