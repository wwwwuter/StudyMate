import { defineStore } from 'pinia'
import { ref } from 'vue'
import { userApi } from '@/api'

interface User {
  id: number
  openid: string
  nickname: string
  avatar: string
  create_time: string
}

export const useUserStore = defineStore('user', () => {
  const user = ref<User | null>(null)
  const isLoggedIn = ref(false)

  function initAuth() {
    const token = localStorage.getItem('studymate_token')
    const savedUser = localStorage.getItem('studymate_user')
    if (token && savedUser) {
      user.value = JSON.parse(savedUser)
      isLoggedIn.value = true
    }
  }

  async function login(code: string) {
    const res: any = await userApi.login(code)
    const { token, user: userData } = res.data
    localStorage.setItem('studymate_token', token)
    localStorage.setItem('studymate_user', JSON.stringify(userData))
    user.value = userData
    isLoggedIn.value = true
    return res
  }

  function logout() {
    localStorage.removeItem('studymate_token')
    localStorage.removeItem('studymate_user')
    user.value = null
    isLoggedIn.value = false
  }

  return { user, isLoggedIn, initAuth, login, logout }
})