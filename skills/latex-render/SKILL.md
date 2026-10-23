---
name: latex-render
version: 1
tools: [render_tex, compile_pdf]
---
只使用内置模板与转义后的纯文本。禁止shell-escape、外部网络、任意宿主路径。限制时间与资源。PDF必须校验可读文本、事实完整、页数与边界，失败时保留旧版本。
