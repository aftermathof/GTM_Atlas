<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { CheckCircle2, CircleAlert } from 'lucide-vue-next'
import { API_ORIGIN } from '../state'

const route = useRoute(), router = useRouter()
const status = ref('checking')
const message = ref('')

async function confirmEmail() {
  const params = new URLSearchParams(route.hash.slice(1))
  const token = params.get('type') === 'signup' ? params.get('access_token') : null
  await router.replace({ path: '/auth/confirmed' })
  if (!token || params.has('error')) {
    status.value = 'error'
    message.value = '验证链接无效或已过期，请返回登录页重新注册或尝试登录。'
    return
  }
  try {
    const response = await fetch(API_ORIGIN + '/api/v1/auth/me', { headers: { Authorization: `Bearer ${token}` } })
    if (!response.ok) throw new Error(response.status >= 500 ? '暂时无法确认验证结果，请稍后尝试登录。' : '验证链接无效或已过期，请返回登录页尝试登录。')
    status.value = 'success'
  } catch (error: any) {
    status.value = 'error'
    message.value = error instanceof TypeError ? '网络连接异常，暂时无法确认验证结果，请稍后尝试登录。' : error.message
  }
}
onMounted(confirmEmail)
</script>

<template>
  <section class="confirmation-page" aria-live="polite" :aria-busy="status==='checking'">
    <div class="confirmation-content">
      <p class="eyebrow">GTM ATLAS / EMAIL VERIFICATION</p>
      <CheckCircle2 v-if="status==='success'" class="result-icon blue" :size="48" :stroke-width="1.25" aria-hidden="true"/>
      <CircleAlert v-else-if="status==='error'" class="result-icon" :size="48" :stroke-width="1.25" aria-hidden="true"/>
      <h1 class="h-xl">{{ status==='checking' ? '正在确认邮箱验证…' : status==='success' ? '邮箱已完成验证' : '暂未确认验证结果' }}</h1>
      <p class="lead">{{ status==='success' ? '你可以返回 GTM Atlas，使用邮箱和密码登录。' : message }}</p>
      <RouterLink v-if="status!=='checking'" to="/login" class="primary">返回登录</RouterLink>
    </div>
  </section>
</template>

<style scoped>
.confirmation-page{min-height:100svh;display:grid;place-items:center;padding:48px 24px;text-align:center}
.confirmation-content{width:100%;max-width:720px}
.result-icon{display:block;margin:0 auto 24px}
.h-xl{font-size:clamp(30px,5vw,48px)}
.lead{margin-bottom:32px}
</style>
