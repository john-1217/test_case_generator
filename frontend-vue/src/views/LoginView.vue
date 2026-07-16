<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '../stores/auth'
import AppIcon from '../components/ui/AppIcon.vue'

const router = useRouter()
const authStore = useAuthStore()
const isLoading = ref(false)
const form = reactive({ username: 'admin', password: 'admin' })

async function submit() {
  if (!form.username || !form.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }

  isLoading.value = true
  try {
    await authStore.login(form)
    await router.push('/tasks')
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '登录失败')
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-card glass-card">
      <div class="login-logo"><AppIcon :size="42" /></div>
      <h1>Test Case Generator</h1>
      <p>登录后开始生成测试用例</p>

      <el-form label-position="top" @submit.prevent="submit">
        <el-form-item label="用户名">
          <el-input v-model="form.username" size="large" autocomplete="username" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input
            v-model="form.password"
            size="large"
            type="password"
            autocomplete="current-password"
            show-password
            @keyup.enter="submit"
          />
        </el-form-item>
        <el-button type="primary" size="large" :loading="isLoading" class="login-btn" @click="submit">
          登录
        </el-button>
      </el-form>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px;
}
.login-card { width: min(420px, 100%); padding: 36px; text-align: center; }
.login-logo {
  width: 64px;
  height: 64px;
  margin: 0 auto 16px;
  display: grid;
  place-items: center;
  border-radius: 20px;
  background: var(--gradient-primary);
  color: white;
}
h1 { margin: 0; font-size: 26px; }
p { margin: 10px 0 28px; color: var(--color-text-secondary); }
.login-btn { width: 100%; margin-top: 6px; }
</style>
