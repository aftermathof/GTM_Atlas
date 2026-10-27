# 浏览器采集：连接、全量、详情一致性

## 连接诊断

使用当前适用的联网/浏览器 skill 与可用连接器，用户指定浏览器优先，不把一次使用的 CDP 工具写成唯一入口。

若当前 web-access 工具提供 check-deps --browser edge，沙箱内失败可能是本机网络权限问题；可在适当权限下重复同一检测，确认后才要求用户调整浏览器或登录。不要读取浏览器磁盘凭据、导出 Cookie。重新发现端口和 target，输出脱敏 URL。

浏览器工具若因无法建立 URL 等问题要求本轮停止，应遵守，不能同一轮换工具绕过。只关闭自己创建的工作标签页，保留用户页面。

## 清单完整性

1. 核对昵称、稳定主页 ID 和内容，不采收藏页或其他同名用户。
2. 每轮把当前卡片并入累计集合，记录首次标题、类型和发现顺序。虚拟 DOM 回收旧卡片，当前屏幕可能只保留十几项。
3. 带参数的实际 href 留在浏览器会话内存。落盘规范 URL；兼容实际观察到的 /explore/NOTE、/discovery/item/NOTE、/user/profile/AUTHOR/NOTE，最后一种取末尾帖子 ID。
4. 等加载结束后连续多轮无新 ID，结合底部/结束信号或无后续加载证据，再最后复查。记录结束依据，不以固定数量或次数为阈值。
5. 页面计数与清单不符时排查视频、置顶重复和不可见内容，不凑总数。恢复时通过正常 UI 重新获取实际链接，不假定旧 target 和签名仍有效。

## 详情与媒体

URL 变了而标题仍是上一帖时继续等待/重试；保存前核对目标 ID、卡片/详情标题、作者和正文。不能以摘要代正文，也不能把失效帖记为已有来源。

下列仅是曾观察过的 DOM，先检查当前页面再使用：

```javascript
const title = document.querySelector('#detail-title')?.innerText;
const body = document.querySelector('#detail-desc')?.innerText;
const slides = [...document.querySelectorAll(
  '.note-slider .swiper-slide:not(.swiper-slide-duplicate)'
)];
```

轮播排除重复 slide，保留原始页序。翻页/滚动触发懒加载，检查页数、currentSrc、naturalWidth 和实际图片。naturalWidth 为 0 说明尚未就绪或失败，不表示无图。缺失超过尝试上限如实记录。

普通单帖最多 3 次总尝试；验证码、账号异常、明确频率限制或持续 403/429 则立即停止站点采集，不耗尽次数撞限制，不轮换账号/代理。保存进度，可离线继续整理。
