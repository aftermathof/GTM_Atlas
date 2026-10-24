<script setup lang="ts">
import { ArrowUpRight, ArrowRight, BookOpen, MessageSquare, FileText } from 'lucide-vue-next'
import { state } from '../state'
const paths = [
  { n: '01', en: 'BUILD YOUR FOUNDATION', title: 'GTM 知识学习', description: '从市场洞察、渠道策略到增长指标，建立有脉络的知识体系。让每一次提问，都能回到来源。', url: '/learn', action: '探索知识体系', icon: BookOpen, topics: 'GTM 基础 / 渠道与销售 / 市场营销' },
  { n: '02', en: 'TURN KNOWLEDGE INTO ANSWERS', title: '面经与 Mock 面试', description: '理解问题背后的业务逻辑，在逐题练习与追问中，把知道的知识变成说得清楚的判断。', url: '/interviews', action: '开始面试练习', icon: MessageSquare, topics: '题目练习 / 场景模拟 / 复盘反馈' },
  { n: '03', en: 'TELL YOUR REAL STORY', title: 'GTM 简历工作台', description: '以真实经历为起点，对照目标岗位诊断、改写与排版。每一处修改，由你确认。', url: '/career', action: '打磨我的简历', icon: FileText, topics: '岗位诊断 / 事实确认 / 版本管理' }
]
</script>
<template>
  <div class="container">
    <section class="home-hero"><div><p class="eyebrow"><span class="blue-square"></span>A FIELD GUIDE TO YOUR NEXT MARKET</p><h1 class="h-hero">从理解市场，<br>到<span class="blue">走向市场。</span></h1><p class="hero-description">为走向全球市场的你，连接知识、面试与职业表达。<br class="desktop-only">把零散的学习，变成有依据的下一步。</p><RouterLink to="/learn" class="text-link hero-link">从知识开始 <ArrowUpRight :size="19" /></RouterLink></div><div class="hero-path"><div class="path-caption"><span class="eyebrow">YOUR GTM JOURNEY</span><span class="meta">学习 → 练习 → 表达</span></div><RouterLink v-for="p in paths" :key="p.n" :to="p.url" class="journey-step"><span class="journey-number">{{ p.n }}</span><div><h3>{{ p.n === '01' ? '建立理解' : p.n === '02' ? '练习判断' : '表达价值' }}</h3><p>{{ p.n === '01' ? '以可追溯的知识，搭建你的业务框架。' : p.n === '02' ? '在具体问题里，训练你的思考与回答。' : '让真实经历，与目标岗位产生连接。' }}</p></div><ArrowUpRight :size="19" /></RouterLink><p class="path-footnote">从一个问题开始，让每一步都有积累。</p></div></section>
    <section class="portal-section"><div class="section-heading"><p class="eyebrow">THREE WAYS FORWARD</p><span class="meta">一个平台，三个相互连接的入口</span></div><RouterLink v-for="p in paths" :key="p.n" :to="p.url" class="portal-row"><span class="row-number">{{ p.n }}</span><div class="portal-title"><p class="eyebrow">{{ p.en }}</p><h2>{{ p.title }}</h2><span class="topic-line">{{ p.topics }}</span></div><p class="portal-description">{{ p.description }}</p><span class="row-arrow"><ArrowUpRight :size="26" /></span></RouterLink></section>
    <section class="home-bottom"><div><p class="eyebrow">BUILT ON TRUST</p><h2>好的准备，<br>从可信的信息开始。</h2></div><div class="principle-list"><p><span>01</span>知识有来源，回答有依据。</p><p><span>02</span>经历不虚构，修改由你决定。</p><p><span>03</span>练习是反馈，不是录用预测。</p><div class="home-bottom-links"><RouterLink to="/settings" class="text-link">了解资料、模型与隐私设置 <ArrowRight :size="16" /></RouterLink><RouterLink :to="state.user ? '/history' : '/login?next=/history'" class="text-link">进入我的空间 <ArrowRight :size="16" /></RouterLink></div></div></section>
  </div>
</template>

<style scoped>
.home-bottom-links{display:flex;flex-direction:column;align-items:flex-start;gap:24px}
</style>
