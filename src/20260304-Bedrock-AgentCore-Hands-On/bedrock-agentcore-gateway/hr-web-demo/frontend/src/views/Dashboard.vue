<template>
  <div class="dash">
    <!-- Top bar -->
    <header class="topbar">
      <div class="topbar-inner">
        <div class="topbar-left">
          <div class="topbar-brand">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
              <path d="M12 2L2 7l10 5 10-5-10-5z" fill="#ff9900" opacity="0.8"/>
              <path d="M2 17l10 5 10-5" stroke="#ff9900" stroke-width="2" fill="none"/>
              <path d="M2 12l10 5 10-5" stroke="#ff9900" stroke-width="2" fill="none" opacity="0.5"/>
            </svg>
            <span>HR Gateway</span>
          </div>
          <div class="topbar-divider"></div>
          <div class="role-badge" :class="role">
            <span class="role-dot"></span>
            {{ roleConfig.title }}
          </div>
        </div>
        <div class="topbar-right">
          <span class="user-name" v-if="userInfo">{{ userInfo.name }}</span>
          <button class="btn-icon" @click="refreshData" title="Refresh">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 4v6h-6"/><path d="M1 20v-6h6"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/></svg>
          </button>
          <button class="btn-icon" @click="goHome" title="Logout">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/><polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/></svg>
          </button>
        </div>
      </div>
    </header>

    <!-- Tab navigation -->
    <div class="tab-bar">
      <button class="tab-btn" :class="{ active: activeTab === 'chat' }" @click="switchTab('chat')">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>
        AI Chat
      </button>
      <button class="tab-btn" :class="{ active: activeTab === 'tools' }" @click="switchTab('tools')">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg>
        Tools
      </button>
    </div>

    <!-- Content -->
    <main class="dash-content">
      <!-- AI Chat Tab -->
      <div v-show="activeTab === 'chat'" class="tab-panel">
        <ChatAgent :role="role" :username="userInfo?.username || ''" />
      </div>

      <!-- Tools Tab -->
      <div v-show="activeTab === 'tools'" class="tab-panel">
        <!-- Tool selector -->
        <div class="tool-selector" v-if="availableTools.length > 0">
          <button
            v-for="tool in availableTools"
            :key="tool.name"
            class="tool-chip"
            :class="{ active: selectedTool === tool.name }"
            @click="selectTool(tool)"
          >
            <svg v-if="tool.name.includes('search')" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
            <svg v-else-if="tool.name.includes('leave')" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
            <svg v-else width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
            {{ getToolDisplayName(tool.name) }}
          </button>
        </div>
        <div v-else-if="loading.tools" class="empty-state">
          <div class="spinner"></div>
          <p style="margin-top:12px;">도구 목록을 불러오는 중...</p>
        </div>
        <div v-else class="empty-state">
          <p>사용 가능한 도구가 없습니다</p>
        </div>

        <!-- Employee Search -->
        <div v-if="selectedTool && selectedTool.includes('employee_search')" class="panel">
          <div class="panel-header">
            <h3>직원 검색</h3>
          </div>
          <div class="panel-body">
            <div class="quick-tags">
              <span
                v-for="emp in employeeList"
                :key="emp.id"
                class="qtag"
                :class="{ active: searchForm.search_name === emp.name }"
                @click="selectEmployee(emp.name)"
              >{{ emp.name }}</span>
            </div>
            <div class="search-row">
              <div class="search-input-wrap">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
                <input
                  v-model="searchForm.search_name"
                  placeholder="이름 또는 사번 (예: Employee 1, EMP-001)"
                  @keyup.enter="searchEmployees"
                />
              </div>
              <button class="btn-primary" @click="searchEmployees" :disabled="loading.search">
                {{ loading.search ? '검색 중...' : '검색' }}
              </button>
            </div>

            <!-- Result -->
            <div v-if="employeeData" class="result-card fade-in">
              <div class="result-header">
                <span class="result-name">{{ employeeData.name }}</span>
                <span class="result-badge">{{ employeeData.department }}</span>
                <span class="result-badge outline">{{ employeeData.position }}</span>
              </div>
              <div class="result-grid">
                <div class="result-field" v-if="employeeData.employee_id">
                  <span class="rf-label">사번</span>
                  <span class="rf-value">{{ employeeData.employee_id }}</span>
                </div>
                <div class="result-field" v-if="employeeData.email">
                  <span class="rf-label">이메일</span>
                  <span class="rf-value" :class="{ masked: isMasked(employeeData.email) }">{{ employeeData.email }}</span>
                </div>
                <div class="result-field" v-if="employeeData.phone">
                  <span class="rf-label">전화번호</span>
                  <span class="rf-value" :class="{ masked: isMasked(employeeData.phone) }">{{ employeeData.phone }}</span>
                </div>
                <div class="result-field" v-if="employeeData.address">
                  <span class="rf-label">주소</span>
                  <span class="rf-value" :class="{ masked: isMasked(employeeData.address) }">{{ employeeData.address }}</span>
                </div>
                <div class="result-field" v-if="employeeData.salary">
                  <span class="rf-label">연봉</span>
                  <span class="rf-value" :class="{ masked: isMasked(employeeData.salary) }">
                    {{ isMasked(employeeData.salary) ? employeeData.salary : '$' + employeeData.salary?.toLocaleString() }}
                  </span>
                </div>
                <div class="result-field" v-if="employeeData.hire_date">
                  <span class="rf-label">입사일</span>
                  <span class="rf-value">{{ employeeData.hire_date }}</span>
                </div>
                <div class="result-field" v-if="employeeData.status">
                  <span class="rf-label">상태</span>
                  <span class="rf-value status-active">{{ employeeData.status }}</span>
                </div>
              </div>
              <div v-if="role === 'employee'" class="masking-notice">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
                민감 정보는 Bedrock Guardrails에 의해 자동 마스킹됩니다
              </div>
            </div>
          </div>
        </div>

        <!-- All Employees (HR) -->
        <div v-if="selectedTool && selectedTool.includes('all_employees')" class="panel">
          <div class="panel-header">
            <h3>전체 직원 목록</h3>
            <button class="btn-primary sm" @click="loadAllEmployees" :disabled="loading.allEmployees">
              {{ loading.allEmployees ? '로딩...' : '조회' }}
            </button>
          </div>
          <div class="panel-body" v-if="allEmployeesData">
            <div class="table-wrap">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>사번</th><th>이름</th><th>부서</th><th>직책</th>
                    <th>이메일</th><th>전화번호</th><th>입사일</th><th>상태</th><th>연봉</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="emp in allEmployeesData.employees" :key="emp.employee_id">
                    <td class="mono">{{ emp.employee_id }}</td>
                    <td>{{ emp.name }}</td>
                    <td>{{ emp.department }}</td>
                    <td>{{ emp.position }}</td>
                    <td :class="{ masked: isMasked(emp.email) }">{{ emp.email }}</td>
                    <td :class="{ masked: isMasked(emp.phone) }">{{ emp.phone }}</td>
                    <td>{{ emp.hire_date }}</td>
                    <td><span class="status-dot active"></span>{{ emp.status }}</td>
                    <td :class="{ masked: isMasked(emp.salary) }">
                      {{ isMasked(emp.salary) ? emp.salary : '$' + emp.salary?.toLocaleString() }}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div class="table-footer">총 {{ allEmployeesData.total_employees }}명</div>
          </div>
        </div>

        <!-- Employee Leave -->
        <div v-if="selectedTool && selectedTool.includes('employee_leave') && !selectedTool.includes('all_leave')" class="panel">
          <div class="panel-header">
            <h3>휴가 조회</h3>
          </div>
          <div class="panel-body">
            <div class="search-row">
              <div class="search-input-wrap">
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
                <input
                  v-model="leaveForm.employee_id"
                  :placeholder="userInfo?.employee_id || 'EMP-002'"
                  :readonly="role === 'employee'"
                />
              </div>
              <button class="btn-primary" @click="getPersonalLeave" :disabled="loading.leave">
                {{ loading.leave ? '조회 중...' : '조회' }}
              </button>
            </div>

            <div v-if="leaveData" class="fade-in">
              <!-- Stats -->
              <div v-if="leaveData.statistics" class="stats-grid">
                <div class="stat-card">
                  <span class="stat-num">{{ leaveData.statistics.annual_entitlement || 0 }}</span>
                  <span class="stat-label">연차 부여</span>
                </div>
                <div class="stat-card">
                  <span class="stat-num">{{ leaveData.statistics.annual_taken || 0 }}</span>
                  <span class="stat-label">연차 사용</span>
                </div>
                <div class="stat-card accent">
                  <span class="stat-num">{{ leaveData.statistics.annual_remaining || 0 }}</span>
                  <span class="stat-label">연차 잔여</span>
                </div>
                <div class="stat-card">
                  <span class="stat-num">{{ leaveData.statistics.sick_taken || 0 }}</span>
                  <span class="stat-label">병가 사용</span>
                </div>
              </div>

              <!-- Leave records table -->
              <div v-if="leaveData.leave_records && leaveData.leave_records.length > 0" class="table-wrap" style="margin-top:16px;">
                <table class="data-table">
                  <thead>
                    <tr>
                      <th>Leave ID</th><th>유형</th><th>시작일</th><th>종료일</th>
                      <th>일수</th><th>상태</th><th>사유</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="rec in leaveData.leave_records" :key="rec.leave_id">
                      <td class="mono">{{ rec.leave_id }}</td>
                      <td>{{ rec.leave_type }}</td>
                      <td>{{ rec.start_date }}</td>
                      <td>{{ rec.end_date }}</td>
                      <td>{{ rec.days }}</td>
                      <td>
                        <span class="status-pill" :class="rec.status === 'Approved' ? 'approved' : 'pending'">
                          {{ rec.status }}
                        </span>
                      </td>
                      <td>{{ rec.reason }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>

        <!-- All Leave Records (HR) -->
        <div v-if="selectedTool && selectedTool.includes('all_leave_records')" class="panel">
          <div class="panel-header">
            <h3>전체 휴가 기록</h3>
            <button class="btn-primary sm" @click="getLeaveManagement" :disabled="loading.management">
              {{ loading.management ? '로딩...' : '조회' }}
            </button>
          </div>
          <div class="panel-body" v-if="managementData">
            <!-- Stats -->
            <div v-if="managementData.statistics" class="stats-grid">
              <div class="stat-card">
                <span class="stat-num">{{ managementData.statistics.total_records || 0 }}</span>
                <span class="stat-label">총 기록</span>
              </div>
              <div class="stat-card">
                <span class="stat-num">{{ managementData.statistics.total_days || 0 }}</span>
                <span class="stat-label">총 일수</span>
              </div>
              <div class="stat-card" v-for="(count, type) in managementData.statistics.by_type" :key="type">
                <span class="stat-num">{{ count }}</span>
                <span class="stat-label">{{ type }}</span>
              </div>
            </div>

            <!-- Employee summaries -->
            <div v-if="managementData.employee_summaries && managementData.employee_summaries.length > 0" class="table-wrap" style="margin-top:16px;">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>사번</th><th>이름</th><th>부서</th><th>연차 부여</th>
                    <th>연차 사용</th><th>연차 잔여</th><th>병가</th><th>개인휴가</th><th>대기</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="s in managementData.employee_summaries" :key="s.employee_id">
                    <td class="mono">{{ s.employee_id }}</td>
                    <td>{{ s.name }}</td>
                    <td>{{ s.department }}</td>
                    <td>{{ s.annual_entitlement }}</td>
                    <td>{{ s.annual_taken }}</td>
                    <td>
                      <span class="status-pill" :class="s.annual_remaining > 5 ? 'approved' : 'pending'">
                        {{ s.annual_remaining }}
                      </span>
                    </td>
                    <td>{{ s.sick_taken }}</td>
                    <td>{{ s.personal_taken }}</td>
                    <td>{{ s.pending_days || '-' }}</td>
                  </tr>
                </tbody>
              </table>
            </div>

            <!-- All records -->
            <div v-if="managementData.leave_records && managementData.leave_records.length > 0" class="table-wrap" style="margin-top:16px;">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>사번</th><th>Leave ID</th><th>유형</th><th>시작일</th>
                    <th>종료일</th><th>일수</th><th>상태</th><th>사유</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="rec in managementData.leave_records" :key="rec.leave_id">
                    <td class="mono">{{ rec.employee_id }}</td>
                    <td class="mono">{{ rec.leave_id }}</td>
                    <td>{{ rec.leave_type }}</td>
                    <td>{{ rec.start_date }}</td>
                    <td>{{ rec.end_date }}</td>
                    <td>{{ rec.days }}</td>
                    <td>
                      <span class="status-pill" :class="rec.status === 'Approved' ? 'approved' : 'pending'">
                        {{ rec.status }}
                      </span>
                    </td>
                    <td>{{ rec.reason }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { hrApi } from '../services/api'
import ChatAgent from './ChatAgent.vue'

export default {
  name: 'Dashboard',
  components: { ChatAgent },
  props: { role: { type: String, required: true } },
  setup(props) {
    const router = useRouter()
    const loading = ref({ tools: false, search: false, leave: false, management: false, refresh: false, allEmployees: false })
    const activeTab = ref('chat')
    const availableTools = ref([])
    const selectedTool = ref(null)
    const employeeData = ref(null)
    const leaveData = ref(null)
    const managementData = ref(null)
    const allEmployeesData = ref(null)

    const userInfo = ref(null)
    try {
      const stored = localStorage.getItem('userInfo')
      if (stored) userInfo.value = JSON.parse(stored)
    } catch (e) { /* ignore */ }

    const searchForm = ref({ search_name: '' })
    const leaveForm = ref({ employee_id: userInfo.value?.employee_id || '' })
    const managementForm = ref({ action: 'view', employee_id: '' })

    const employeeList = ref([])

    const loadEmployeeList = async () => {
      try {
        const data = await hrApi.getEmployeeList()
        employeeList.value = data
      } catch (e) {
        console.error('Failed to load employee list:', e)
      }
    }

    const roleConfigs = {
      'hr-manager': { title: 'HR Manager', description: 'Full access to all employee data and leave management' },
      'employee': { title: 'Employee', description: 'Limited access with PII masking' }
    }
    const roleConfig = computed(() => roleConfigs[props.role] || roleConfigs['employee'])

    const isMasked = (val) => {
      if (!val) return false
      const s = String(val)
      return s.includes('{') && s.includes('}')
    }

    const getToolDisplayName = (name) => {
      const map = {
        'all_employees_tool': '전체 직원',
        'employee_search_tool': '직원 검색',
        'all_leave_records_tool': '전체 휴가',
        'employee_leave_tool': '휴가 조회'
      }
      if (map[name]) return map[name]
      for (const [k, v] of Object.entries(map)) { if (name.includes(k)) return v }
      // 동적으로 추가된 도구: tool_name에서 읽기 좋은 이름 생성
      const cleaned = name.replace(/.*___/, '').replace(/_tool$/, '').replace(/_/g, ' ')
      return cleaned.charAt(0).toUpperCase() + cleaned.slice(1)
    }

    const loadTools = async () => {
      loading.value.tools = true
      try {
        const data = await hrApi.getTools(props.role)
        availableTools.value = data.tools || []
        if (availableTools.value.length > 0) selectTool(availableTools.value[0])
      } catch (e) {
        ElMessage.error('도구 목록 로딩 실패')
      } finally { loading.value.tools = false }
    }

    const selectTool = (tool) => {
      selectedTool.value = tool.name
      employeeData.value = null
      leaveData.value = null
      managementData.value = null
      allEmployeesData.value = null
    }

    const parseGatewayContent = (response) => {
      if (!response?.success || !response?.data?.result) return null
      const content = response.data.result?.content?.[0]?.text
      if (!content) return null
      try {
        const parsed = typeof content === 'string' ? JSON.parse(content) : content
        return parsed?.body?.result || null
      } catch { return null }
    }

    const loadAllEmployees = async () => {
      loading.value.allEmployees = true
      try {
        const response = await hrApi.getAllEmployees(props.role)
        const result = parseGatewayContent(response)
        if (result) {
          allEmployeesData.value = result
          ElMessage.success(`${result.total_employees}명 로딩 완료`)
        } else { ElMessage.warning('데이터 없음') }
      } catch (e) { ElMessage.error('전체 직원 로딩 실패') }
      finally { loading.value.allEmployees = false }
    }

    const searchEmployees = async () => {
      if (!searchForm.value.search_name) { ElMessage.warning('검색어를 입력하세요'); return }
      loading.value.search = true
      try {
        const response = await hrApi.searchEmployees(props.role, { search_name: searchForm.value.search_name })
        const result = parseGatewayContent(response)
        if (result?.employees?.length > 0) {
          employeeData.value = result.employees[0]
          ElMessage.success(`${result.employees[0].name} 검색 완료`)
        } else {
          employeeData.value = null
          ElMessage.warning('검색 결과 없음')
        }
      } catch (e) { ElMessage.error('검색 실패') }
      finally { loading.value.search = false }
    }

    const getPersonalLeave = async () => {
      let eid = leaveForm.value.employee_id
      if (props.role === 'employee' && userInfo.value?.employee_id) {
        eid = userInfo.value.employee_id
        leaveForm.value.employee_id = eid
      }
      if (!eid) { ElMessage.warning('Employee ID를 입력하세요'); return }
      loading.value.leave = true
      try {
        const response = await hrApi.getPersonalLeave(props.role, eid)
        const result = parseGatewayContent(response)
        if (result) { leaveData.value = result; ElMessage.success('휴가 데이터 로딩 완료') }
        else { ElMessage.warning('데이터 없음') }
      } catch (e) { ElMessage.error('휴가 조회 실패') }
      finally { loading.value.leave = false }
    }

    const getLeaveManagement = async () => {
      loading.value.management = true
      try {
        const response = await hrApi.getLeaveManagement(props.role, {
          action: managementForm.value.action,
          employee_id: managementForm.value.employee_id || undefined
        })
        const result = parseGatewayContent(response)
        if (result) { managementData.value = result; ElMessage.success('휴가 기록 로딩 완료') }
        else { ElMessage.warning('데이터 없음') }
      } catch (e) { ElMessage.error('휴가 기록 조회 실패') }
      finally { loading.value.management = false }
    }

    const toolsLoaded = ref(false)
    const switchTab = (tab) => {
      activeTab.value = tab
      if (tab === 'tools' && !toolsLoaded.value) {
        loadTools()
        toolsLoaded.value = true
      }
    }

    const selectEmployee = (name) => { searchForm.value.search_name = name; searchEmployees() }
    const refreshData = async () => { loading.value.refresh = true; await loadTools(); loading.value.refresh = false }
    const goHome = () => { localStorage.clear(); router.push('/') }

    onMounted(() => { loadEmployeeList() })

    return {
      loading, activeTab, availableTools, selectedTool, employeeData, leaveData,
      managementData, allEmployeesData, searchForm, leaveForm, managementForm,
      roleConfig, userInfo, employeeList, isMasked, getToolDisplayName,
      selectTool, loadAllEmployees, searchEmployees, getPersonalLeave,
      getLeaveManagement, selectEmployee, refreshData, goHome, loadEmployeeList,
      switchTab
    }
  }
}
</script>

<style scoped>
.dash { min-height: 100vh; background: var(--bg-primary); }

/* Top bar */
.topbar {
  position: sticky; top: 0; z-index: 100;
  background: rgba(15,25,35,0.85);
  backdrop-filter: blur(16px);
  border-bottom: 1px solid var(--border);
}
.topbar-inner {
  max-width: 1400px; margin: 0 auto;
  display: flex; justify-content: space-between; align-items: center;
  padding: 0 24px; height: 56px;
}
.topbar-left { display: flex; align-items: center; gap: 16px; }
.topbar-brand {
  display: flex; align-items: center; gap: 8px;
  font-size: 16px; font-weight: 700; color: var(--text-primary);
}
.topbar-divider { width: 1px; height: 24px; background: var(--border); }
.role-badge {
  display: flex; align-items: center; gap: 6px;
  font-size: 12px; font-weight: 600;
  padding: 4px 12px; border-radius: 20px;
  background: rgba(255,255,255,0.04); border: 1px solid var(--border);
  color: var(--text-secondary); text-transform: uppercase; letter-spacing: 0.5px;
}
.role-dot { width: 8px; height: 8px; border-radius: 50%; }
.role-badge.hr-manager .role-dot { background: #3498db; }
.role-badge.employee .role-dot { background: #2ecc71; }

.topbar-right { display: flex; align-items: center; gap: 12px; }
.user-name { font-size: 13px; color: var(--text-secondary); }
.btn-icon {
  width: 36px; height: 36px; border-radius: var(--radius-sm);
  background: rgba(255,255,255,0.04); border: 1px solid var(--border);
  color: var(--text-secondary); cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: all 0.2s;
}
.btn-icon:hover { border-color: var(--accent); color: var(--accent); background: var(--accent-glow); }

/* Tab bar */
.tab-bar {
  max-width: 1400px; margin: 0 auto;
  display: flex; gap: 4px; padding: 16px 24px 0;
}
.tab-btn {
  display: flex; align-items: center; gap: 6px;
  padding: 10px 20px; border-radius: var(--radius-sm) var(--radius-sm) 0 0;
  background: transparent; border: 1px solid transparent; border-bottom: none;
  color: var(--text-muted); font-size: 13px; font-weight: 600;
  cursor: pointer; font-family: inherit; transition: all 0.2s;
}
.tab-btn:hover { color: var(--text-secondary); }
.tab-btn.active {
  background: var(--bg-secondary); border-color: var(--border);
  color: var(--accent);
}

/* Content */
.dash-content {
  max-width: 1400px; margin: 0 auto; padding: 0 24px 40px;
}
.tab-panel {
  background: var(--bg-secondary);
  border: 1px solid var(--border);
  border-radius: 0 var(--radius-md) var(--radius-md) var(--radius-md);
  min-height: 500px;
}

/* Tool selector */
.tool-selector {
  display: flex; flex-wrap: wrap; gap: 8px;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border);
}
.tool-chip {
  display: flex; align-items: center; gap: 6px;
  padding: 8px 16px; border-radius: 20px;
  background: rgba(255,255,255,0.03); border: 1px solid var(--border);
  color: var(--text-secondary); font-size: 13px; font-weight: 500;
  cursor: pointer; font-family: inherit; transition: all 0.2s;
}
.tool-chip:hover { border-color: var(--accent); color: var(--accent); }
.tool-chip.active {
  background: var(--accent-glow); border-color: var(--accent); color: var(--accent);
}

.empty-state { padding: 60px; text-align: center; color: var(--text-muted); display: flex; flex-direction: column; align-items: center; }
.empty-state .spinner {
  width: 24px; height: 24px;
  border: 3px solid var(--border);
  border-top-color: var(--accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* Panel */
.panel { padding: 20px; }
.panel-header {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 16px; padding-bottom: 12px;
  border-bottom: 1px solid var(--border);
}
.panel-header h3 { font-size: 16px; font-weight: 700; color: var(--text-primary); }

/* Quick tags */
.quick-tags { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 12px; }
.qtag {
  padding: 4px 12px; border-radius: 16px; font-size: 12px; font-weight: 500;
  background: rgba(255,255,255,0.03); border: 1px solid var(--border);
  color: var(--text-secondary); cursor: pointer; transition: all 0.2s;
}
.qtag:hover { border-color: var(--accent); color: var(--accent); }
.qtag.active { background: var(--accent-glow); border-color: var(--accent); color: var(--accent); }

/* Search row */
.search-row { display: flex; gap: 8px; margin-bottom: 16px; }
.search-input-wrap {
  flex: 1; display: flex; align-items: center; gap: 10px;
  background: rgba(255,255,255,0.04); border: 1px solid var(--border);
  border-radius: var(--radius-sm); padding: 0 14px; height: 42px;
  transition: all 0.2s; color: var(--text-muted);
}
.search-input-wrap:focus-within {
  border-color: var(--accent); box-shadow: 0 0 0 3px rgba(255,153,0,0.08);
}
.search-input-wrap input {
  flex: 1; background: none; border: none; outline: none;
  color: var(--text-primary); font-size: 14px; font-family: inherit;
}
.search-input-wrap input::placeholder { color: var(--text-muted); }

/* Buttons */
.btn-primary {
  padding: 0 20px; height: 42px; border-radius: var(--radius-sm);
  background: linear-gradient(135deg, #ff9900, #ec7211);
  border: none; color: #0f1923; font-size: 14px; font-weight: 700;
  cursor: pointer; font-family: inherit; white-space: nowrap;
  transition: all 0.2s;
}
.btn-primary:hover:not(:disabled) { box-shadow: 0 4px 16px rgba(255,153,0,0.3); transform: translateY(-1px); }
.btn-primary:disabled { opacity: 0.6; cursor: not-allowed; }
.btn-primary.sm { height: 34px; padding: 0 14px; font-size: 12px; }

/* Result card */
.result-card {
  background: rgba(255,255,255,0.03); border: 1px solid var(--border);
  border-radius: var(--radius-md); overflow: hidden;
}
.result-header {
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
  padding: 16px 20px; border-bottom: 1px solid var(--border);
}
.result-name { font-size: 18px; font-weight: 700; color: var(--text-primary); }
.result-badge {
  font-size: 11px; font-weight: 600; padding: 3px 10px; border-radius: 12px;
  background: var(--accent-glow); color: var(--accent); border: 1px solid var(--border-accent);
}
.result-badge.outline { background: transparent; border-color: var(--border); color: var(--text-secondary); }

.result-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 1px; background: var(--border);
}
.result-field {
  display: flex; flex-direction: column; gap: 4px;
  padding: 12px 20px; background: var(--bg-secondary);
}
.rf-label { font-size: 11px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; }
.rf-value { font-size: 14px; color: var(--text-primary); word-break: break-all; }
.rf-value.masked {
  background: rgba(255,193,7,0.1); color: #f0c040;
  padding: 2px 8px; border-radius: 4px; font-family: 'Courier New', monospace;
  font-size: 12px; font-weight: 600; width: fit-content;
}
.status-active { color: var(--success); font-weight: 600; }

.masking-notice {
  display: flex; align-items: center; gap: 6px;
  padding: 10px 20px; font-size: 12px; color: var(--text-muted);
  background: rgba(255,153,0,0.04); border-top: 1px solid var(--border);
}

/* Stats grid */
.stats-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap: 8px; }
.stat-card {
  background: rgba(255,255,255,0.03); border: 1px solid var(--border);
  border-radius: var(--radius-sm); padding: 16px; text-align: center;
}
.stat-card.accent { border-color: var(--border-accent); background: var(--accent-glow); }
.stat-num { display: block; font-size: 28px; font-weight: 800; color: var(--text-primary); }
.stat-card.accent .stat-num { color: var(--accent); }
.stat-label { display: block; font-size: 11px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.5px; margin-top: 4px; }

/* Data table */
.table-wrap { overflow-x: auto; border-radius: var(--radius-sm); border: 1px solid var(--border); }
.data-table { width: 100%; border-collapse: collapse; font-size: 13px; white-space: nowrap; }
.data-table th {
  background: rgba(255,255,255,0.04); color: var(--text-secondary);
  font-weight: 600; padding: 10px 14px; text-align: left;
  border-bottom: 1px solid var(--border); font-size: 11px;
  text-transform: uppercase; letter-spacing: 0.5px;
}
.data-table td {
  padding: 10px 14px; border-bottom: 1px solid var(--border);
  color: var(--text-primary);
}
.data-table tbody tr:hover td { background: rgba(255,255,255,0.02); }
.data-table .mono { font-family: 'Courier New', monospace; font-size: 12px; color: var(--text-secondary); }
.data-table .masked {
  color: #f0c040; font-family: 'Courier New', monospace; font-size: 12px;
  background: rgba(255,193,7,0.06); padding: 2px 6px; border-radius: 3px;
}

.table-footer {
  padding: 10px 14px; font-size: 12px; color: var(--text-muted);
  background: rgba(255,255,255,0.02); border-top: 1px solid var(--border);
}

/* Status pills */
.status-pill {
  display: inline-block; padding: 2px 10px; border-radius: 12px;
  font-size: 11px; font-weight: 600;
}
.status-pill.approved { background: rgba(46,204,113,0.15); color: #2ecc71; }
.status-pill.pending { background: rgba(243,156,18,0.15); color: #f39c12; }

.status-dot { display: inline-block; width: 6px; height: 6px; border-radius: 50%; margin-right: 6px; }
.status-dot.active { background: #2ecc71; }

/* Animations */
.fade-in { animation: fadeIn 0.3s ease; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }

@media (max-width: 768px) {
  .topbar-inner { padding: 0 16px; }
  .tab-bar { padding: 12px 16px 0; }
  .dash-content { padding: 0 16px 24px; }
  .panel { padding: 16px; }
  .result-grid { grid-template-columns: 1fr; }
  .stats-grid { grid-template-columns: repeat(2, 1fr); }
}
</style>
