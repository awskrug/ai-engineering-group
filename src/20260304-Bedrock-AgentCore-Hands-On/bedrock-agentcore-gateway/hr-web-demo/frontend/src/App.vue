<template>
  <div id="app">
    <router-view v-slot="{ Component }">
      <transition name="fade" mode="out-in">
        <component :is="Component" />
      </transition>
    </router-view>
  </div>
</template>

<script>
export default { name: 'App' }
</script>

<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

* { margin: 0; padding: 0; box-sizing: border-box; }

:root {
  --bg-primary: #0f1923;
  --bg-secondary: #1a2634;
  --bg-card: rgba(255,255,255,0.04);
  --bg-card-hover: rgba(255,255,255,0.08);
  --accent: #ff9900;
  --accent-light: #ffb84d;
  --accent-glow: rgba(255,153,0,0.15);
  --text-primary: #f2f3f3;
  --text-secondary: #8d9baa;
  --text-muted: #5a6b7d;
  --border: rgba(255,255,255,0.08);
  --border-accent: rgba(255,153,0,0.3);
  --success: #2ecc71;
  --warning: #f39c12;
  --danger: #e74c3c;
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;
  --radius-xl: 24px;
  --shadow-sm: 0 2px 8px rgba(0,0,0,0.2);
  --shadow-md: 0 4px 24px rgba(0,0,0,0.3);
  --shadow-lg: 0 8px 48px rgba(0,0,0,0.4);
  --shadow-glow: 0 0 40px rgba(255,153,0,0.1);
}

#app {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
  min-height: 100vh;
  background: var(--bg-primary);
  color: var(--text-primary);
  -webkit-font-smoothing: antialiased;
}

.fade-enter-active, .fade-leave-active {
  transition: opacity 0.25s ease;
}
.fade-enter-from, .fade-leave-to {
  opacity: 0;
}

/* Override Element Plus for dark theme */
.el-message { border-radius: var(--radius-md) !important; }
</style>
