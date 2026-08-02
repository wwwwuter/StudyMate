import { ref, readonly } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { getKeySettings, type KeySettings } from '@/api/ai'

/**
 * 全局 AI Key 状态管理 + 首次使用引导
 *
 * - 应用启动时加载一次 Key 状态
 * - 任何 AI 功能调用前调 ensureKey() 检查，无 Key 时弹窗引导去设置页
 * - 设置页保存后调 refresh() 更新状态
 */
const _keySettings = ref<KeySettings | null>(null)
const _loaded = ref(false)
const _guiding = ref(false) // 防止重复弹窗

export function useAiKey() {
  const router = useRouter()
  const keySettings = readonly(_keySettings)
  const hasKey = () => !!(_keySettings.value?.has_key && _keySettings.value?.enabled)

  async function load() {
    if (_loaded.value) return
    try {
      const res = await getKeySettings()
      _keySettings.value = res.data
    } catch {
      _keySettings.value = null
    }
    _loaded.value = true
  }

  async function refresh() {
    try {
      const res = await getKeySettings()
      _keySettings.value = res.data
    } catch {
      /* ignore */
    }
    _loaded.value = true
  }

  /**
   * 确保用户已配置 AI Key。
   * - 已配置：返回 true
   * - 未配置：弹窗引导去设置页，返回 false（调用方应中止 AI 操作）
   */
  async function ensureKey(actionLabel = '使用 AI 功能'): Promise<boolean> {
    await load()
    if (hasKey()) return true
    if (_guiding.value) return false
    _guiding.value = true
    try {
      await ElMessageBox.confirm(
        `${actionLabel}需要先配置 AI API Key。\n\n支持 DeepSeek / 通义千问 / 智谱 / 月之暗面 等兼容模型。\n密钥仅保存在你本机，不上传不记账。`,
        '配置 AI 接入',
        {
          confirmButtonText: '前往设置',
          cancelButtonText: '暂不配置',
          type: 'info',
          distinguishCancelAndClose: true,
        },
      )
      router.push('/settings')
      return false
    } catch {
      // 用户选择"暂不配置"或关闭
      return false
    } finally {
      _guiding.value = false
    }
  }

  return { keySettings, hasKey, load, refresh, ensureKey }
}
