<template>
  <div class="home">
    <!-- Animated background -->
    <div class="bg-grid"></div>
    <div class="bg-glow bg-glow-1"></div>
    <div class="bg-glow bg-glow-2"></div>

    <div class="home-inner">
      <!-- Logo / Brand -->
      <div class="brand">
        <div class="brand-icon">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none">
            <path d="M12 2L2 7l10 5 10-5-10-5z" fill="#ff9900" opacity="0.8"/>
            <path d="M2 17l10 5 10-5" stroke="#ff9900" stroke-width="2" fill="none"/>
            <path d="M2 12l10 5 10-5" stroke="#ff9900" stroke-width="2" fill="none" opacity="0.5"/>
          </svg>
        </div>
        <h1>HR Gateway</h1>
        <p class="brand-sub">PII Masking & Access Control Demo</p>
        <p class="brand-desc">Amazon Bedrock Guardrails 기반 실시간 PII 마스킹과<br/>세분화된 접근 제어를 체험하세요.</p>
      </div>

      <!-- Login Card -->
      <div class="login-card">
        <div class="card-glow"></div>
        <form @submit.prevent="login" class="login-form">
          <div class="input-group">
            <label>Username</label>
            <div class="input-wrap" :class="{ focused: focusUser }">
              <svg class="input-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
                <circle cx="12" cy="7" r="4"/>
              </svg>
              <input
                v-model="form.username"
                placeholder="Enter username"
                @focus="focusUser = true"
                @blur="focusUser = false"
                autocomplete="username"
              />
            </div>
          </div>

          <div class="input-group">
            <label>Password</label>
            <div class="input-wrap" :class="{ focused: focusPass }">
              <svg class="input-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <rect x="3" y="11" width="18" height="11" rx="2" ry="2"/>
                <path d="M7 11V7a5 5 0 0 1 10 0v4"/>
              </svg>
              <input
                v-model="form.password"
                :type="showPass ? 'text' : 'password'"
                placeholder="Enter password"
                @focus="focusPass = true"
                @blur="focusPass = false"
                autocomplete="current-password"
              />
              <button type="button" class="toggle-pass" @click="showPass = !showPass" tabindex="-1">
                <svg v-if="!showPass" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/>
                </svg>
                <svg v-else width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
                  <line x1="1" y1="1" x2="23" y2="23"/>
                </svg>
              </button>
            </div>
          </div>

          <button type="submit" class="btn-login" :disabled="loading">
            <span v-if="!loading">Sign In</span>
            <span v-else class="btn-loading">
              <svg class="spinner" width="20" height="20" viewBox="0 0 24 24"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="3" fill="none" stroke-dasharray="31.4" stroke-linecap="round"><animateTransform attributeName="transform" type="rotate" from="0 12 12" to="360 12 12" dur="0.8s" repeatCount="indefinite"/></circle></svg>
              Signing in...
            </span>
          </button>
        </form>

        <!-- Quick access hints -->
        <div class="hints">
          <button class="hint-chip" @click="fillCredentials('hr-manager', 'hr123!')">
            <span class="hint-dot hr"></span> HR Manager
          </button>
          <button class="hint-chip" @click="fillCredentials('employee2', 'emp789!')">
            <span class="hint-dot emp"></span> Employee
          </button>
        </div>
      </div>

      <!-- Footer badges -->
      <div class="footer-badges">
        <span class="badge">Amazon Bedrock</span>
        <span class="badge">Guardrails</span>
        <span class="badge">AgentCore</span>
        <span class="badge">DynamoDB</span>
        <span class="badge">Cognito</span>
      </div>
    </div>
  </div>
</template>

<script>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { hrApi } from '../services/api'

export default {
  name: 'Home',
  setup() {
    const router = useRouter()
    const form = ref({ username: '', password: '' })
    const loading = ref(false)
    const showPass = ref(false)
    const focusUser = ref(false)
    const focusPass = ref(false)

    const fillCredentials = (u, p) => {
      form.value.username = u
      form.value.password = p
    }

    const login = async () => {
      if (!form.value.username || !form.value.password) {
        ElMessage.warning('Username과 Password를 입력해주세요')
        return
      }
      loading.value = true
      try {
        const data = await hrApi.login(form.value.username, form.value.password)
        localStorage.setItem('userInfo', JSON.stringify({
          ...data.user_info,
          access_token: data.access_token,
          role: data.role,
          client_id: data.client_id
        }))
        localStorage.setItem('userRole', data.role)
        ElMessage.success(`Welcome, ${data.user_info.name}`)
        router.push(`/dashboard/${data.role}`)
      } catch (e) {
        ElMessage.error(e.response?.data?.detail || 'Login failed')
      } finally {
        loading.value = false
      }
    }

    return { form, loading, showPass, focusUser, focusPass, login, fillCredentials }
  }
}
</script>

<style scoped>
.home {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
  padding: 40px 20px;
}

/* Animated background */
.bg-grid {
  position: absolute; inset: 0;
  background-image:
    linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px);
  background-size: 60px 60px;
  animation: gridMove 20s linear infinite;
}
@keyframes gridMove {
  0% { transform: translate(0, 0); }
  100% { transform: translate(60px, 60px); }
}

.bg-glow {
  position: absolute;
  border-radius: 50%;
  filter: blur(120px);
  pointer-events: none;
}
.bg-glow-1 {
  width: 500px; height: 500px;
  background: rgba(255,153,0,0.08);
  top: -100px; right: -100px;
  animation: float1 8s ease-in-out infinite;
}
.bg-glow-2 {
  width: 400px; height: 400px;
  background: rgba(0,115,187,0.06);
  bottom: -80px; left: -80px;
  animation: float2 10s ease-in-out infinite;
}
@keyframes float1 {
  0%, 100% { transform: translate(0, 0); }
  50% { transform: translate(-30px, 30px); }
}
@keyframes float2 {
  0%, 100% { transform: translate(0, 0); }
  50% { transform: translate(20px, -20px); }
}

.home-inner {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 420px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 32px;
}

/* Brand */
.brand {
  text-align: center;
}
.brand-icon {
  width: 72px; height: 72px;
  margin: 0 auto 16px;
  background: rgba(255,153,0,0.1);
  border: 1px solid rgba(255,153,0,0.2);
  border-radius: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  animation: iconPulse 3s ease-in-out infinite;
}
@keyframes iconPulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(255,153,0,0.1); }
  50% { box-shadow: 0 0 30px 10px rgba(255,153,0,0.08); }
}
.brand h1 {
  font-size: 32px;
  font-weight: 800;
  letter-spacing: -0.5px;
  background: linear-gradient(135deg, #ffffff 0%, #ff9900 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}
.brand-sub {
  font-size: 13px;
  font-weight: 600;
  color: var(--accent);
  letter-spacing: 1.5px;
  text-transform: uppercase;
  margin-top: 4px;
}
.brand-desc {
  font-size: 14px;
  color: var(--text-secondary);
  line-height: 1.7;
  margin-top: 12px;
}

/* Login Card */
.login-card {
  width: 100%;
  position: relative;
  background: rgba(255,255,255,0.04);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 32px;
  backdrop-filter: blur(20px);
}
.card-glow {
  position: absolute;
  inset: -1px;
  border-radius: var(--radius-lg);
  background: linear-gradient(135deg, rgba(255,153,0,0.15), transparent 50%, rgba(0,115,187,0.1));
  z-index: -1;
  opacity: 0;
  transition: opacity 0.4s;
}
.login-card:hover .card-glow { opacity: 1; }

.login-form {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.input-group label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.8px;
  margin-bottom: 8px;
}

.input-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
  background: rgba(255,255,255,0.04);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: 0 14px;
  height: 48px;
  transition: all 0.2s;
}
.input-wrap.focused {
  border-color: var(--accent);
  background: rgba(255,153,0,0.04);
  box-shadow: 0 0 0 3px rgba(255,153,0,0.08);
}
.input-icon { color: var(--text-muted); flex-shrink: 0; }
.input-wrap.focused .input-icon { color: var(--accent); }

.input-wrap input {
  flex: 1;
  background: none;
  border: none;
  outline: none;
  color: var(--text-primary);
  font-size: 15px;
  font-family: inherit;
}
.input-wrap input::placeholder { color: var(--text-muted); }

.toggle-pass {
  background: none; border: none; cursor: pointer;
  color: var(--text-muted); padding: 4px;
  display: flex; align-items: center;
  transition: color 0.2s;
}
.toggle-pass:hover { color: var(--text-secondary); }

.btn-login {
  width: 100%;
  height: 48px;
  background: linear-gradient(135deg, #ff9900, #ec7211);
  border: none;
  border-radius: var(--radius-sm);
  color: #0f1923;
  font-size: 15px;
  font-weight: 700;
  font-family: inherit;
  cursor: pointer;
  transition: all 0.2s;
  margin-top: 4px;
}
.btn-login:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 20px rgba(255,153,0,0.3);
}
.btn-login:active:not(:disabled) { transform: translateY(0); }
.btn-login:disabled { opacity: 0.7; cursor: not-allowed; }

.btn-loading {
  display: flex; align-items: center; justify-content: center; gap: 8px;
}

/* Hints */
.hints {
  display: flex;
  gap: 10px;
  justify-content: center;
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid var(--border);
}
.hint-chip {
  display: flex; align-items: center; gap: 6px;
  background: rgba(255,255,255,0.04);
  border: 1px solid var(--border);
  border-radius: 20px;
  padding: 6px 14px;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-secondary);
  cursor: pointer;
  font-family: inherit;
  transition: all 0.2s;
}
.hint-chip:hover {
  border-color: var(--accent);
  color: var(--accent);
  background: rgba(255,153,0,0.06);
}
.hint-dot {
  width: 8px; height: 8px; border-radius: 50%;
}
.hint-dot.hr { background: #3498db; }
.hint-dot.emp { background: #2ecc71; }

/* Footer badges */
.footer-badges {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
}
.badge {
  font-size: 11px;
  font-weight: 500;
  color: var(--text-muted);
  background: rgba(255,255,255,0.03);
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 20px;
  padding: 4px 12px;
  letter-spacing: 0.3px;
}

@media (max-width: 480px) {
  .home-inner { max-width: 100%; }
  .login-card { padding: 24px; }
  .brand h1 { font-size: 26px; }
}
</style>
