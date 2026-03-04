<template>
  <div class="chat">
    <!-- Messages -->
    <div class="messages" ref="messagesArea">
      <!-- Welcome -->
      <div v-if="messages.length === 0" class="welcome">
        <div class="welcome-icon">
          <svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#ff9900" stroke-width="1.5">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
          </svg>
        </div>
        <h3>HR AI Assistant</h3>
        <p>자연어로 질문하면 자동으로 적절한 도구를 사용하여 답변합니다.</p>
        <div class="suggestions">
          <button v-for="s in suggestions" :key="s" @click="sendMessage(s)" class="sug-btn">{{ s }}</button>
        </div>
      </div>

      <!-- Messages -->
      <div v-for="(msg, idx) in messages" :key="idx" class="msg-row" :class="msg.role">
        <!-- User -->
        <div v-if="msg.role === 'user'" class="bubble-row user-row">
          <div class="bubble user-bubble">{{ msg.content }}</div>
        </div>

        <!-- Agent -->
        <div v-if="msg.role === 'agent'" class="bubble-row agent-row">
          <div class="agent-avatar">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/>
            </svg>
          </div>
          <div class="agent-body">
            <!-- Tool usage indicators -->
            <div v-if="msg.toolCalls && msg.toolCalls.length" class="tool-indicators">
              <div v-for="(tc, ti) in msg.toolCalls" :key="ti" class="tool-tag">
                <span class="tool-dot"></span>
                {{ formatToolName(tc.tool_name) }}
                <span v-if="tc.execution_time" class="tool-time">{{ tc.execution_time.toFixed(1) }}s</span>
              </div>
            </div>

            <!-- Tool result: Employee cards -->
            <div v-if="msg.toolResults && msg.toolResults.length" class="results-area">
              <template v-for="(tr, tri) in msg.toolResults" :key="tri">
                <!-- Employee data -->
                <template v-if="isEmployeeResult(tr)">
                  <div v-for="(emp, ei) in getEmployees(tr)" :key="ei" class="emp-card">
                    <div class="emp-top">
                      <div class="emp-name-row">
                        <span class="emp-name">{{ emp.name }}</span>
                        <span class="emp-id">{{ emp.employee_id }}</span>
                      </div>
                      <div class="emp-meta">
                        <span v-if="emp.department" class="meta-tag">{{ emp.department }}</span>
                        <span v-if="emp.position" class="meta-tag dim">{{ emp.position }}</span>
                        <span v-if="emp.status" class="meta-tag" :class="emp.status === 'Active' ? 'green' : ''">{{ emp.status }}</span>
                      </div>
                    </div>
                    <div class="emp-details">
                      <div class="detail-item" v-if="emp.email">
                        <span class="d-icon">📧</span>
                        <span class="d-label">이메일</span>
                        <span class="d-val" :class="{ masked: isMasked(emp.email) }">{{ emp.email }}</span>
                      </div>
                      <div class="detail-item" v-if="emp.phone">
                        <span class="d-icon">📱</span>
                        <span class="d-label">전화</span>
                        <span class="d-val" :class="{ masked: isMasked(emp.phone) }">{{ emp.phone }}</span>
                      </div>
                      <div class="detail-item" v-if="emp.address">
                        <span class="d-icon">📍</span>
                        <span class="d-label">주소</span>
                        <span class="d-val" :class="{ masked: isMasked(emp.address) }">{{ emp.address }}</span>
                      </div>
                      <div class="detail-item" v-if="emp.salary !== undefined && emp.salary !== null">
                        <span class="d-icon">💰</span>
                        <span class="d-label">연봉</span>
                        <span class="d-val" :class="{ masked: isMasked(emp.salary) }">
                          {{ isMasked(emp.salary) ? emp.salary : '$' + Number(emp.salary).toLocaleString() }}
                        </span>
                      </div>
                      <div class="detail-item" v-if="emp.hire_date">
                        <span class="d-icon">📅</span>
                        <span class="d-label">입사일</span>
                        <span class="d-val">{{ emp.hire_date }}</span>
                      </div>
                    </div>
                  </div>
                </template>

                <!-- Leave data -->
                <template v-else-if="isLeaveResult(tr)">
                  <div class="leave-card">
                    <!-- Stats row -->
                    <div v-if="getLeaveStats(tr)" class="leave-stats">
                      <div class="ls-item" v-if="getLeaveStats(tr).annual_remaining !== undefined">
                        <span class="ls-num accent">{{ getLeaveStats(tr).annual_remaining }}</span>
                        <span class="ls-label">연차 잔여</span>
                      </div>
                      <div class="ls-item" v-if="getLeaveStats(tr).annual_taken !== undefined">
                        <span class="ls-num">{{ getLeaveStats(tr).annual_taken }}</span>
                        <span class="ls-label">연차 사용</span>
                      </div>
                      <div class="ls-item" v-if="getLeaveStats(tr).sick_taken !== undefined">
                        <span class="ls-num">{{ getLeaveStats(tr).sick_taken }}</span>
                        <span class="ls-label">병가</span>
                      </div>
                      <div class="ls-item" v-if="getLeaveStats(tr).personal_taken !== undefined">
                        <span class="ls-num">{{ getLeaveStats(tr).personal_taken }}</span>
                        <span class="ls-label">개인휴가</span>
                      </div>
                      <div class="ls-item" v-if="getLeaveStats(tr).total_records !== undefined">
                        <span class="ls-num">{{ getLeaveStats(tr).total_records }}</span>
                        <span class="ls-label">총 기록</span>
                      </div>
                      <div class="ls-item" v-if="getLeaveStats(tr).total_days !== undefined">
                        <span class="ls-num">{{ getLeaveStats(tr).total_days }}</span>
                        <span class="ls-label">총 일수</span>
                      </div>
                    </div>
                    <!-- Records table -->
                    <div v-if="getLeaveRecords(tr).length" class="leave-table-wrap">
                      <table class="leave-tbl">
                        <thead>
                          <tr>
                            <th v-if="getLeaveRecords(tr)[0].employee_id">사번</th>
                            <th>유형</th><th>시작일</th><th>종료일</th><th>일수</th><th>상태</th><th>사유</th>
                          </tr>
                        </thead>
                        <tbody>
                          <tr v-for="(rec, ri) in getLeaveRecords(tr)" :key="ri">
                            <td v-if="rec.employee_id" class="mono">{{ rec.employee_id }}</td>
                            <td>{{ rec.leave_type }}</td>
                            <td>{{ rec.start_date }}</td>
                            <td>{{ rec.end_date }}</td>
                            <td>{{ rec.days }}</td>
                            <td>
                              <span class="pill" :class="rec.status === 'Approved' ? 'ok' : 'wait'">{{ rec.status }}</span>
                            </td>
                            <td>{{ rec.reason }}</td>
                          </tr>
                        </tbody>
                      </table>
                    </div>
                  </div>
                </template>

                <!-- Error result -->
                <template v-else-if="isErrorResult(tr)">
                  <div class="error-card">
                    <span class="error-icon">🚫</span>
                    <span class="error-text">{{ getErrorMessage(tr) }}</span>
                  </div>
                </template>

                <!-- Fallback -->
                <template v-else>
                  <pre class="raw-json">{{ formatRaw(tr.data) }}</pre>
                </template>
              </template>
            </div>

            <!-- Text response -->
            <div v-if="msg.content" class="bubble agent-bubble" v-html="renderMarkdown(msg.content)"></div>
          </div>
        </div>

        <!-- Status -->
        <div v-if="msg.role === 'status'" class="status-row">
          <div class="spinner"></div>
          <span>{{ msg.content }}</span>
        </div>

        <!-- Error -->
        <div v-if="msg.role === 'error'" class="error-row">
          ⚠️ {{ msg.content }}
        </div>
      </div>

      <!-- Typing -->
      <div v-if="isLoading" class="msg-row agent">
        <div class="bubble-row agent-row">
          <div class="agent-avatar">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/>
            </svg>
          </div>
          <div class="typing"><span></span><span></span><span></span></div>
        </div>
      </div>
    </div>

    <!-- Input -->
    <div class="input-bar">
      <div class="input-row" :class="{ focused: inputFocused }">
        <input
          v-model="inputMessage"
          :placeholder="inputPlaceholder"
          :disabled="isLoading"
          @keyup.enter="sendMessage()"
          @focus="inputFocused = true"
          @blur="inputFocused = false"
        />
        <button class="send-btn" @click="sendMessage()" :disabled="!inputMessage.trim() || isLoading">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
          </svg>
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, nextTick, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { chatWithAgent } from '../services/api'

export default {
  name: 'ChatAgent',
  props: {
    role: { type: String, required: true },
    username: { type: String, required: true }
  },
  setup(props) {
    const messages = ref([])
    const inputMessage = ref('')
    const isLoading = ref(false)
    const messagesArea = ref(null)
    const inputFocused = ref(false)

    const suggestions = computed(() =>
      props.role === 'hr-manager'
        ? ['전체 직원 목록을 보여줘', 'Employee 1의 정보를 검색해줘', '전체 휴가 현황을 알려줘', 'Engineering 부서 직원들을 보여줘']
        : ['내 정보를 보여줘', '내 휴가 현황을 알려줘', 'Employee 1을 검색해줘']
    )
    const inputPlaceholder = computed(() =>
      props.role === 'hr-manager' ? '예: 전체 직원 목록을 보여줘' : '예: 내 정보를 보여줘'
    )

    const scroll = async () => {
      await nextTick()
      if (messagesArea.value) messagesArea.value.scrollTop = messagesArea.value.scrollHeight
    }

    // --- Data helpers ---
    const parseData = (d) => {
      if (typeof d === 'string') { try { return JSON.parse(d) } catch { return d } }
      return d
    }

    const isEmployeeResult = (tr) => {
      const d = parseData(tr.data)
      if (!d || typeof d !== 'object') return false
      if (['search_employee', 'list_all_employees'].includes(tr.tool_name)) {
        return !!(d.employees || d.employee_id || d.name)
      }
      return false
    }

    const getEmployees = (tr) => {
      const d = parseData(tr.data)
      if (Array.isArray(d)) return d
      if (d.employees) return d.employees
      if (d.employee_id || d.name) return [d]
      return []
    }

    const isErrorResult = (tr) => {
      const d = parseData(tr.data)
      if (!d || typeof d !== 'object') return false
      return d.error && d.success === false
    }

    const getErrorMessage = (tr) => {
      const d = parseData(tr.data)
      return d?.error || '알 수 없는 오류가 발생했습니다.'
    }

    const isLeaveResult = (tr) => {
      const d = parseData(tr.data)
      if (!d || typeof d !== 'object') return false
      return ['get_employee_leave', 'get_all_leave_records'].includes(tr.tool_name) &&
        !!(d.leave_records || d.statistics || d.records)
    }

    const getLeaveRecords = (tr) => {
      const d = parseData(tr.data)
      return d?.leave_records || d?.records || []
    }

    const getLeaveStats = (tr) => {
      const d = parseData(tr.data)
      return d?.statistics || null
    }

    const isMasked = (val) => {
      if (val === null || val === undefined) return false
      const s = String(val)
      return s.includes('{') && s.includes('}')
    }

    const formatRaw = (data) => {
      const d = parseData(data)
      return typeof d === 'object' ? JSON.stringify(d, null, 2) : String(d)
    }

    const formatToolName = (n) => ({
      search_employee: '직원 검색',
      get_employee_leave: '휴가 조회',
      list_all_employees: '전체 직원 조회',
      get_all_leave_records: '전체 휴가 기록'
    })[n] || n

    // --- Markdown rendering ---
    const escapeHtml = (t) => t.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')

    const inlineFormat = (t) => {
      let s = escapeHtml(t)
      s = s.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      s = s.replace(/\{([A-Z_]+)\}/g, '<span class="pii-tag">{$1}</span>')
      return s
    }

    const renderMarkdown = (text) => {
      if (!text) return ''
      const lines = text.split('\n')
      const out = []
      let tblRows = [], inTbl = false

      const flushTable = () => {
        if (tblRows.length === 0) return
        let h = '<div class="md-tbl-wrap"><table class="md-tbl"><thead><tr>'
        tblRows[0].forEach(c => { h += `<th>${inlineFormat(c)}</th>` })
        h += '</tr></thead><tbody>'
        for (let i = 1; i < tblRows.length; i++) {
          h += '<tr>'
          tblRows[i].forEach(c => { h += `<td>${inlineFormat(c)}</td>` })
          h += '</tr>'
        }
        h += '</tbody></table></div>'
        out.push(h)
        tblRows = []
        inTbl = false
      }

      for (const raw of lines) {
        const line = raw.trim()
        if (line.startsWith('|') && line.endsWith('|')) {
          if (/^\|[\s\-:|]+\|$/.test(line)) continue
          const cells = line.split('|').slice(1, -1).map(c => c.trim())
          inTbl = true
          tblRows.push(cells)
        } else {
          if (inTbl) flushTable()
          if (!line) { out.push('<br/>'); continue }
          if (line.startsWith('### ')) { out.push(`<h4 class="md-h4">${inlineFormat(line.slice(4))}</h4>`); continue }
          if (line.startsWith('## ')) { out.push(`<h3 class="md-h3">${inlineFormat(line.slice(3))}</h3>`); continue }
          if (line.startsWith('# ')) { out.push(`<h2 class="md-h2">${inlineFormat(line.slice(2))}</h2>`); continue }
          if (/^[-*] /.test(line)) { out.push(`<p class="md-li">• ${inlineFormat(line.slice(2))}</p>`); continue }
          if (/^\d+\.\s/.test(line)) { out.push(`<p class="md-li">${inlineFormat(line)}</p>`); continue }
          out.push(`<p class="md-p">${inlineFormat(line)}</p>`)
        }
      }
      if (inTbl) flushTable()
      return out.join('')
    }

    // --- Send ---
    const sendMessage = async (text) => {
      const msg = text || inputMessage.value.trim()
      if (!msg) return
      messages.value.push({ role: 'user', content: msg })
      inputMessage.value = ''
      isLoading.value = true
      scroll()

      const agentMsg = { role: 'agent', content: '', toolCalls: [], toolResults: [] }
      let added = false
      const ensure = () => {
        if (messages.value.length && messages.value[messages.value.length - 1].role === 'status') messages.value.pop()
        if (!added) { messages.value.push(agentMsg); added = true }
      }

      try {
        await chatWithAgent(props.role, props.username, msg, (ev) => {
          switch (ev.type) {
            case 'status':
              if (!added) { messages.value.push({ role: 'status', content: ev.content }); scroll() }
              break
            case 'tool_call': ensure(); agentMsg.toolCalls.push(ev.content); scroll(); break
            case 'tool_result': ensure(); agentMsg.toolResults.push(ev.content); scroll(); break
            case 'text': ensure(); agentMsg.content += ev.content; scroll(); break
            case 'error':
              if (messages.value.length && messages.value[messages.value.length - 1].role === 'status') messages.value.pop()
              messages.value.push({ role: 'error', content: ev.content }); scroll()
              break
          }
        })
      } catch (e) {
        if (messages.value.length && messages.value[messages.value.length - 1].role === 'status') messages.value.pop()
        messages.value.push({ role: 'error', content: `요청 실패: ${e.message}` })
      } finally {
        isLoading.value = false
        scroll()
      }
    }

    return {
      messages, inputMessage, isLoading, messagesArea, inputFocused,
      suggestions, inputPlaceholder,
      isEmployeeResult, getEmployees, isLeaveResult, getLeaveRecords, getLeaveStats,
      isErrorResult, getErrorMessage,
      isMasked, formatRaw, formatToolName, renderMarkdown, sendMessage
    }
  }
}
</script>

<style scoped>
.chat {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
  background: var(--bg-primary);
}

/* Messages area */
.messages {
  flex: 1;
  overflow-y: auto;
  padding: 24px 20px 16px;
  scroll-behavior: smooth;
}
.messages::-webkit-scrollbar { width: 4px; }
.messages::-webkit-scrollbar-thumb { background: var(--text-muted); border-radius: 4px; }
.messages::-webkit-scrollbar-track { background: transparent; }

/* Welcome */
.welcome {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  text-align: center;
}
.welcome-icon {
  width: 56px; height: 56px;
  display: flex; align-items: center; justify-content: center;
  background: var(--accent-glow);
  border: 1px solid var(--border-accent);
  border-radius: 50%;
  margin-bottom: 16px;
}
.welcome h3 {
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 6px;
}
.welcome p {
  font-size: 13px;
  color: var(--text-secondary);
  margin-bottom: 24px;
}
.suggestions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
  max-width: 500px;
}
.sug-btn {
  padding: 8px 14px;
  font-size: 12.5px;
  font-family: inherit;
  color: var(--text-secondary);
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  cursor: pointer;
  transition: all 0.2s;
}
.sug-btn:hover {
  color: var(--accent);
  border-color: var(--border-accent);
  background: var(--accent-glow);
}

/* Bubble rows */
.msg-row { margin-bottom: 16px; }
.bubble-row { display: flex; gap: 10px; }
.user-row { justify-content: flex-end; }
.agent-row { justify-content: flex-start; align-items: flex-start; }

.user-bubble {
  max-width: 70%;
  padding: 10px 16px;
  font-size: 13.5px;
  line-height: 1.6;
  color: #fff;
  background: linear-gradient(135deg, var(--accent), #e68a00);
  border-radius: var(--radius-md) var(--radius-md) 4px var(--radius-md);
  word-break: break-word;
}

.agent-avatar {
  flex-shrink: 0;
  width: 30px; height: 30px;
  display: flex; align-items: center; justify-content: center;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: 50%;
  color: var(--accent);
  margin-top: 2px;
}

.agent-body {
  max-width: 85%;
  min-width: 0;
}

.agent-bubble {
  padding: 12px 16px;
  font-size: 13.5px;
  line-height: 1.7;
  color: var(--text-primary);
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 4px var(--radius-md) var(--radius-md) var(--radius-md);
  word-break: break-word;
}

/* Tool indicators */
.tool-indicators {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 8px;
}
.tool-tag {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 10px;
  font-size: 11px;
  font-weight: 500;
  color: var(--accent-light);
  background: var(--accent-glow);
  border: 1px solid var(--border-accent);
  border-radius: var(--radius-lg);
}
.tool-dot {
  width: 5px; height: 5px;
  background: var(--accent);
  border-radius: 50%;
}
.tool-time {
  color: var(--text-muted);
  font-size: 10px;
  font-weight: 400;
}

/* Results area */
.results-area {
  margin-bottom: 8px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* Employee card */
.emp-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  overflow: hidden;
  transition: border-color 0.2s;
}
.emp-card:hover {
  border-color: var(--border-accent);
}
.emp-top {
  padding: 12px 14px 10px;
  border-bottom: 1px solid var(--border);
}
.emp-name-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}
.emp-name {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
}
.emp-id {
  font-size: 11px;
  font-weight: 500;
  color: var(--text-muted);
  background: var(--bg-card);
  padding: 2px 7px;
  border-radius: 4px;
  font-family: 'SF Mono', 'Fira Code', monospace;
}
.emp-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}
.meta-tag {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  background: var(--bg-card);
  color: var(--text-secondary);
  border: 1px solid var(--border);
}
.meta-tag.dim { color: var(--text-muted); }
.meta-tag.green { color: var(--success); border-color: rgba(46,204,113,0.2); background: rgba(46,204,113,0.08); }

.emp-details {
  padding: 10px 14px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.detail-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12.5px;
  line-height: 1.4;
}
.d-icon { font-size: 13px; flex-shrink: 0; width: 18px; text-align: center; }
.d-label {
  flex-shrink: 0;
  width: 42px;
  color: var(--text-muted);
  font-size: 11px;
  font-weight: 500;
}
.d-val {
  color: var(--text-secondary);
  word-break: break-all;
}
.masked {
  color: var(--warning);
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-size: 11.5px;
  opacity: 0.85;
}

/* Leave card */
.leave-card {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  overflow: hidden;
}
.leave-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 1px;
  background: var(--border);
  border-bottom: 1px solid var(--border);
}
.ls-item {
  flex: 1;
  min-width: 80px;
  padding: 12px 10px;
  text-align: center;
  background: var(--bg-secondary);
}
.ls-num {
  display: block;
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary);
  margin-bottom: 2px;
}
.ls-num.accent { color: var(--accent); }
.ls-label {
  font-size: 10.5px;
  color: var(--text-muted);
  font-weight: 500;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.leave-table-wrap {
  overflow-x: auto;
}
.leave-tbl {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}
.leave-tbl th {
  padding: 8px 10px;
  text-align: left;
  font-weight: 600;
  font-size: 10.5px;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: 0.3px;
  background: var(--bg-card);
  border-bottom: 1px solid var(--border);
}
.leave-tbl td {
  padding: 8px 10px;
  color: var(--text-secondary);
  border-bottom: 1px solid var(--border);
  white-space: nowrap;
}
.leave-tbl tbody tr:hover td {
  background: var(--bg-card);
}
.leave-tbl .mono {
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-size: 11px;
  color: var(--text-muted);
}
.pill {
  display: inline-block;
  padding: 2px 8px;
  border-radius: var(--radius-sm);
  font-size: 11px;
  font-weight: 500;
}
.pill.ok { color: var(--success); background: rgba(46,204,113,0.1); }
.pill.wait { color: var(--warning); background: rgba(243,156,18,0.1); }

/* Error card */
.error-card {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  background: rgba(231,76,60,0.06);
  border: 1px solid rgba(231,76,60,0.2);
  border-radius: var(--radius-md);
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.5;
}
.error-icon {
  flex-shrink: 0;
  font-size: 16px;
}
.error-text {
  word-break: break-word;
}

/* Raw JSON fallback */
.raw-json {
  padding: 12px 14px;
  font-size: 11.5px;
  font-family: 'SF Mono', 'Fira Code', monospace;
  color: var(--text-secondary);
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  overflow-x: auto;
  white-space: pre-wrap;
  word-break: break-all;
  max-height: 300px;
}

/* Status & error */
.status-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  font-size: 12.5px;
  color: var(--text-muted);
}
.spinner {
  width: 14px; height: 14px;
  border: 2px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

.error-row {
  padding: 10px 16px;
  font-size: 13px;
  color: var(--danger);
  background: rgba(231,76,60,0.08);
  border: 1px solid rgba(231,76,60,0.2);
  border-radius: var(--radius-md);
  margin: 0 4px;
}

/* Typing indicator */
.typing {
  display: flex;
  gap: 4px;
  padding: 10px 16px;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 4px var(--radius-md) var(--radius-md) var(--radius-md);
}
.typing span {
  width: 6px; height: 6px;
  background: var(--text-muted);
  border-radius: 50%;
  animation: bounce 1.2s ease-in-out infinite;
}
.typing span:nth-child(2) { animation-delay: 0.15s; }
.typing span:nth-child(3) { animation-delay: 0.3s; }
@keyframes bounce {
  0%, 60%, 100% { transform: translateY(0); opacity: 0.4; }
  30% { transform: translateY(-6px); opacity: 1; }
}

/* Input bar */
.input-bar {
  padding: 12px 16px 16px;
  background: var(--bg-primary);
  border-top: 1px solid var(--border);
}
.input-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 4px 4px 16px;
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  transition: border-color 0.2s, box-shadow 0.2s;
}
.input-row.focused {
  border-color: var(--border-accent);
  box-shadow: 0 0 0 3px var(--accent-glow);
}
.input-row input {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  font-size: 13.5px;
  font-family: inherit;
  color: var(--text-primary);
  padding: 8px 0;
}
.input-row input::placeholder { color: var(--text-muted); }
.send-btn {
  width: 36px; height: 36px;
  display: flex; align-items: center; justify-content: center;
  background: var(--accent);
  border: none;
  border-radius: var(--radius-md);
  color: #fff;
  cursor: pointer;
  transition: all 0.2s;
  flex-shrink: 0;
}
.send-btn:hover:not(:disabled) {
  background: var(--accent-light);
  box-shadow: 0 0 12px var(--accent-glow);
}
.send-btn:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}

/* PII tag in markdown */
.pii-tag {
  display: inline;
  padding: 1px 5px;
  font-size: 11px;
  font-family: 'SF Mono', 'Fira Code', monospace;
  color: var(--warning);
  background: rgba(243,156,18,0.1);
  border: 1px solid rgba(243,156,18,0.2);
  border-radius: 3px;
}

/* Markdown tables */
.md-tbl-wrap {
  overflow-x: auto;
  margin: 8px 0;
}
.md-tbl {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}
.md-tbl th {
  padding: 6px 10px;
  text-align: left;
  font-weight: 600;
  font-size: 11px;
  color: var(--text-muted);
  background: var(--bg-card);
  border-bottom: 1px solid var(--border);
}
.md-tbl td {
  padding: 6px 10px;
  color: var(--text-secondary);
  border-bottom: 1px solid var(--border);
}

/* Markdown headings & text */
.md-h2 { font-size: 15px; font-weight: 600; color: var(--text-primary); margin: 10px 0 4px; }
.md-h3 { font-size: 14px; font-weight: 600; color: var(--text-primary); margin: 8px 0 4px; }
.md-h4 { font-size: 13px; font-weight: 600; color: var(--text-secondary); margin: 6px 0 3px; }
.md-li { font-size: 13px; color: var(--text-secondary); padding-left: 8px; margin: 2px 0; line-height: 1.6; }
.md-p { font-size: 13px; color: var(--text-secondary); margin: 2px 0; line-height: 1.6; }
</style>