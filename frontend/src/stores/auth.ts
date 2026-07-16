import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { authService } from '../services/api'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(null)
  const username = ref('')

  const isAuthenticated = computed(() => Boolean(token.value))

  function init() {
    token.value = localStorage.getItem('token')
    username.value = localStorage.getItem('username') || ''
  }

  async function login(credentials: { username: string; password: string }) {
    const result = await authService.login(credentials)
    token.value = result.token
    username.value = result.username
    localStorage.setItem('token', result.token)
    localStorage.setItem('username', result.username)
  }

  function logout() {
    token.value = null
    username.value = ''
    localStorage.removeItem('token')
    localStorage.removeItem('username')
  }

  return { token, username, isAuthenticated, init, login, logout }
})
