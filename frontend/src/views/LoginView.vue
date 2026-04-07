<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import axios from 'axios'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import loginLogo from '../../logo2.png'
import type { TokenObtainPairResponse } from '../types/auth'
import { resolvePostLoginRedirect } from '../utils/sessionFlow.js'
import { buildApiErrorNotice } from '../utils/apiFeedback.js'
import {
  buildPasswordSecurityNotice,
  buildSessionRecoveryNotice,
  resolveLoginFailureMessage,
} from '../utils/authPresentation.js'
import { resolvePostLoginLandingPath } from '../utils/workspaceNavigation.js'
import {
  clearSessionAuth,
  consumeAuthRedirectTarget,
  consumeSessionExpiredReason,
  fetchCurrentSessionUser,
  setSessionToken,
} from '../utils/sessionAuth'

const username = ref('')
const password = ref('')
const route = useRoute()
const router = useRouter()
const loading = ref(false)
const loginErrorNotice = ref<{ message: string; guidance: string; requestHint: string } | null>(null)
const expiredRecoveryNotice = ref('')
const heroCanvasRef = ref<HTMLCanvasElement | null>(null)
const disposeHeroAnimation = ref<(() => void) | null>(null)

const redirectHint = computed(() =>
  typeof route.query.redirect === 'string' && route.query.redirect.trim()
    ? '登录成功后将回到你刚才访问的受保护页面。'
    : '',
)

const handleLogin = async () => {
  clearSessionAuth()
  loginErrorNotice.value = null
  loading.value = true

  try {
    const response = await axios.post<TokenObtainPairResponse>('/api/token/', {
      username: username.value.trim(),
      password: password.value,
    })

    setSessionToken(response.data.access, response.data.refresh)
    const sessionUser = await fetchCurrentSessionUser()

    if (sessionUser.password_reset_required) {
      ElMessage.warning(buildPasswordSecurityNotice(sessionUser))
    }

    const redirectTarget = resolvePostLoginRedirect(
      typeof route.query.redirect === 'string' ? route.query.redirect : '',
      consumeAuthRedirectTarget(),
    )

    router.push(resolvePostLoginLandingPath(redirectTarget, sessionUser))
    ElMessage.success('登录成功')
  } catch (error: any) {
    clearSessionAuth()
    loginErrorNotice.value = buildApiErrorNotice(error, {
      fallbackMessage: resolveLoginFailureMessage(error),
      fallbackGuidance: '请核对工号或管理员账号、密码；若账户被停用或密码被初始化，请联系管理员处理。',
    })
    ElMessage.error(loginErrorNotice.value.message)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  const expiredReason = consumeSessionExpiredReason()
  if (expiredReason) {
    expiredRecoveryNotice.value = buildSessionRecoveryNotice(
      expiredReason,
      typeof route.query.redirect === 'string' && route.query.redirect.trim().length > 0,
    )
    ElMessage.warning(expiredReason)
  }

  const canvas = heroCanvasRef.value
  const heroSection = canvas?.parentElement
  if (!canvas || !heroSection) {
    return
  }

  const context = canvas.getContext('2d')
  if (!context) {
    return
  }

  type Particle = {
    x: number
    y: number
    vx: number
    vy: number
    radius: number
    update: () => void
    draw: () => void
  }

  const config = {
    particleCount: 60,
    connectionDistance: 180,
    particleColor: 'rgba(37, 99, 235, 0.4)',
    lineColorPrefix: 'rgba(37, 99, 235, ',
    particleRadius: 3,
    speedModifier: 0.3,
  }

  const mouse = {
    x: -1000,
    y: -1000,
    active: false,
  }

  let width = 0
  let height = 0
  let particles: Particle[] = []
  let animationFrameId: number | null = null

  const initCanvas = () => {
    width = canvas.clientWidth
    height = canvas.clientHeight
    canvas.width = width
    canvas.height = height
  }

  const createParticle = (): Particle => ({
    x: Math.random() * width,
    y: Math.random() * height,
    vx: (Math.random() - 0.5) * config.speedModifier,
    vy: (Math.random() - 0.5) * config.speedModifier,
    radius: Math.random() * config.particleRadius + 1.5,
    update() {
      this.x += this.vx
      this.y += this.vy
      if (this.x < 0 || this.x > width) {
        this.vx *= -1
      }
      if (this.y < 0 || this.y > height) {
        this.vy *= -1
      }
    },
    draw() {
      context.beginPath()
      context.arc(this.x, this.y, this.radius, 0, Math.PI * 2)
      context.fillStyle = config.particleColor
      context.fill()
    },
  })

  const createParticles = () => {
    particles = Array.from({ length: config.particleCount }, () => createParticle())
    particles.push({
      x: mouse.x,
      y: mouse.y,
      vx: 0,
      vy: 0,
      radius: 0,
      update() {
        if (mouse.active) {
          this.x = mouse.x
          this.y = mouse.y
        } else {
          this.x = -1000
          this.y = -1000
        }
      },
      draw() {
        return
      },
    })
  }

  const drawConnections = () => {
    for (let i = 0; i < particles.length; i += 1) {
      for (let j = i + 1; j < particles.length; j += 1) {
        const source = particles[i]
        const target = particles[j]
        if (!source || !target) {
          continue
        }

        const dx = source.x - target.x
        const dy = source.y - target.y
        const distance = Math.sqrt(dx * dx + dy * dy)
        if (distance >= config.connectionDistance) {
          continue
        }

        const opacity = (1 - distance / config.connectionDistance) * 0.3
        context.beginPath()
        context.moveTo(source.x, source.y)
        context.lineTo(target.x, target.y)
        context.strokeStyle = `${config.lineColorPrefix}${opacity})`
        context.lineWidth = 1
        context.stroke()
      }
    }
  }

  const animate = () => {
    context.clearRect(0, 0, width, height)
    particles.forEach(particle => {
      particle.update()
      particle.draw()
    })
    drawConnections()
    animationFrameId = requestAnimationFrame(animate)
  }

  const onResize = () => {
    initCanvas()
    createParticles()
  }

  const onMouseMove = (event: MouseEvent) => {
    const rect = heroSection.getBoundingClientRect()
    mouse.x = event.clientX - rect.left
    mouse.y = event.clientY - rect.top
    mouse.active = true
  }

  const onMouseLeave = () => {
    mouse.active = false
  }

  initCanvas()
  createParticles()
  animate()
  window.addEventListener('resize', onResize)
  heroSection.addEventListener('mousemove', onMouseMove)
  heroSection.addEventListener('mouseleave', onMouseLeave)

  disposeHeroAnimation.value = () => {
    if (animationFrameId !== null) {
      cancelAnimationFrame(animationFrameId)
    }
    window.removeEventListener('resize', onResize)
    heroSection.removeEventListener('mousemove', onMouseMove)
    heroSection.removeEventListener('mouseleave', onMouseLeave)
  }
})

onBeforeUnmount(() => {
  disposeHeroAnimation.value?.()
  disposeHeroAnimation.value = null
})
</script>

<template>
  <div class="login-page">
    <div class="login-brand">
      <img :src="loginLogo" alt="系统 Logo" />
    </div>

    <section class="hero-section">
      <canvas ref="heroCanvasRef" class="network-canvas"></canvas>
      <div class="hero-content">
        <h1>打通成果治理闭环<br />驱动<span>教师精准发展</span></h1>
        <p>面向高校的成果治理、教师画像与学术决策一体化智能平台</p>
      </div>
    </section>

    <section class="form-section">
      <div class="login-wrapper">
        <div class="login-header">
          <h2>欢迎登录</h2>
          <p>请输入您的工号与密码进入系统</p>
        </div>

        <div class="form-body">
          <el-alert
            v-if="loginErrorNotice"
            :title="loginErrorNotice.message"
            type="error"
            :description="[loginErrorNotice.guidance, loginErrorNotice.requestHint].filter(Boolean).join(' ')"
            :closable="false"
            show-icon
          />

          <el-alert
            v-if="redirectHint"
            :title="redirectHint"
            type="info"
            :closable="false"
            show-icon
          />

          <el-alert
            v-if="expiredRecoveryNotice"
            :title="expiredRecoveryNotice"
            type="warning"
            :closable="false"
            show-icon
          />

          <div class="input-group">
            <label>账号</label>
            <el-input v-model="username" placeholder="工号 / 管理员账号" size="large" />
          </div>

          <div class="input-group">
            <label>密码</label>
            <el-input
              v-model="password"
              type="password"
              placeholder="请输入密码"
              size="large"
              show-password
              @keyup.enter="handleLogin"
            />
          </div>

          <button type="button" class="forgot-link" @click="router.push('/forgot-password')">忘记密码？</button>

          <el-button class="submit-btn" type="primary" size="large" :loading="loading" @click="handleLogin">登 录</el-button>
        </div>
      </div>
    </section>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  width: 100%;
  display: flex;
  position: relative;
  background-color: #ffffff;
}

.login-brand {
  position: absolute;
  top: 16px;
  left: 20px;
  z-index: 30;
  width: 176px;
  height: 176px;
}

.login-brand img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  display: block;
}

.hero-section {
  flex: 1.3;
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 80px;
  overflow: hidden;
  background: linear-gradient(135deg, #f0f4fd 0%, #e0eafc 100%);
}

.network-canvas {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  z-index: 1;
  opacity: 0.8;
}

.hero-content {
  position: relative;
  z-index: 2;
  max-width: 600px;
  pointer-events: none;
}

.hero-content h1 {
  margin: 0 0 20px;
  font-size: 48px;
  color: #1e293b;
  font-weight: 700;
  line-height: 1.2;
  letter-spacing: 1px;
}

.hero-content h1 span {
  color: #2563eb;
}

.hero-content p {
  margin: 0;
  font-size: 18px;
  color: #475569;
  line-height: 1.6;
  font-weight: 300;
}

.form-section {
  flex: 1;
  z-index: 10;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #ffffff;
  box-shadow: -20px 0 40px rgba(0, 0, 0, 0.03);
}

.login-wrapper {
  width: 100%;
  max-width: 420px;
  padding: 0 40px;
}

.login-header {
  margin-bottom: 36px;
}

.login-header h2 {
  margin: 0 0 8px;
  font-size: 28px;
  color: #0f172a;
}

.login-header p {
  margin: 0;
  font-size: 14px;
  color: #64748b;
}

.form-body {
  display: grid;
  gap: 16px;
}

.input-group {
  display: grid;
  gap: 8px;
}

.input-group label {
  margin: 0;
  font-size: 14px;
  color: #334155;
  font-weight: 500;
}

.forgot-link {
  justify-self: end;
  border: none;
  background: transparent;
  color: #2563eb;
  font-size: 13px;
  line-height: 1;
  padding: 0;
  cursor: pointer;
}

.submit-btn {
  height: 52px;
  font-size: 16px;
  letter-spacing: 2px;
}

.forgot-link:hover {
  color: #1d4ed8;
  text-decoration: underline;
}

@media (max-width: 900px) {
  .login-page {
    flex-direction: column;
  }

  .login-brand {
    top: 10px;
    left: 12px;
    width: 144px;
    height: 144px;
  }

  .hero-section {
    flex: none;
    min-height: 280px;
    padding: 40px;
  }

  .hero-content h1 {
    font-size: 32px;
  }

  .form-section {
    padding: 36px 0;
    box-shadow: none;
  }
}
</style>
