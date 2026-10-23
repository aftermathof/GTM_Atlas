import { defineConfig } from 'vitepress'
export default defineConfig({title: 'GTM Atlas · 知识手册', description: '可溯源的 GTM 学习资料', lang: 'zh-CN', base: '/handbook/', outDir: '../dist/handbook', themeConfig: { search: { provider: 'local' }, nav: [{ text: '返回工作台', link: '/' }], sidebar: [{ text: '知识手册', link: '/' }] }})
