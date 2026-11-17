import { defineStore } from 'pinia'
import { ref } from 'vue'

export type ToastTone = 'success' | 'error' | 'info'

export interface Toast {
  id: number
  message: string
  tone: ToastTone
}

export interface ConfirmRequest {
  title: string
  body?: string
  confirmLabel?: string
  danger?: boolean
  resolve: (ok: boolean) => void
}

let nextId = 1
const AUTO_DISMISS_MS = 5000

export const useUi = defineStore('ui', () => {
  const toasts = ref<Toast[]>([])
  const confirmRequest = ref<ConfirmRequest | null>(null)
  const timers = new Map<number, number>()

  function schedule(t: Toast): void {
    // Errors stay until dismissed; confirmations of something the page already shows can go away.
    if (t.tone !== 'error') timers.set(t.id, window.setTimeout(() => dismiss(t.id), AUTO_DISMISS_MS))
  }

  function show(t: Toast): void {
    toasts.value.push(t)
    schedule(t)
  }

  function toast(message: string, tone: ToastTone = 'success'): void {
    const t = { id: nextId++, message, tone }
    // A toast behind an open modal would be inert and easy to miss, so hold it until the modal closes.
    const modal = document.querySelector<HTMLDialogElement>('dialog:modal')
    if (modal) modal.addEventListener('close', () => show(t), { once: true })
    else show(t)
  }

  function dismiss(id: number): void {
    window.clearTimeout(timers.get(id))
    timers.delete(id)
    toasts.value = toasts.value.filter((t) => t.id !== id)
  }

  /** Pause auto-dismissal while the user is hovering or focused inside the notifications. */
  function pause(): void {
    for (const id of timers.keys()) window.clearTimeout(timers.get(id))
    timers.clear()
  }

  function resume(): void {
    for (const t of toasts.value) if (!timers.has(t.id)) schedule(t)
  }

  function confirm(options: Omit<ConfirmRequest, 'resolve'>): Promise<boolean> {
    return new Promise((resolve) => {
      confirmRequest.value = { ...options, resolve }
    })
  }

  function settleConfirm(ok: boolean): void {
    confirmRequest.value?.resolve(ok)
    confirmRequest.value = null
  }

  return { toasts, toast, dismiss, pause, resume, confirmRequest, confirm, settleConfirm }
})
