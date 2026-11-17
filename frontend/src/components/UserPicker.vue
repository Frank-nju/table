<script setup lang="ts">
import { X } from 'lucide-vue-next'
import { computed, ref, useId, watch } from 'vue'
import { api } from '@/api/client'
import type { Ref as Person } from '@/api/types'
import { isComposing } from '@/utils/ime'
import UiAvatar from './ui/UiAvatar.vue'

const props = withDefaults(defineProps<{ multiple?: boolean; exclude?: number[]; placeholder?: string; inputId?: string; invalid?: boolean }>(), {
  multiple: true,
})
const model = defineModel<Person[]>({ default: () => [] })

const query = ref('')
const results = ref<Person[]>([])
const open = ref(false)
const active = ref(0)
const listId = useId()
const inputEl = ref<HTMLInputElement | null>(null)
let timer: number | undefined

const hidden = computed(() => new Set([...(props.exclude ?? []), ...model.value.map((p) => p.id)]))
const visible = computed(() => results.value.filter((p) => !hidden.value.has(p.id)).slice(0, 8))

watch(query, (q) => {
  if (q) open.value = true
  window.clearTimeout(timer)
  timer = window.setTimeout(async () => {
    try {
      results.value = await api.users.search(q, 20)
      active.value = 0
    } catch {
      results.value = []
    }
  }, 180)
})

function pick(p: Person) {
  model.value = props.multiple ? [...model.value, p] : [p]
  query.value = ''
  open.value = false // reopens as soon as they type, so the list never covers what's below
}

function remove(id: number) {
  model.value = model.value.filter((p) => p.id !== id)
}

function onKey(e: KeyboardEvent) {
  // Enter, arrows and Backspace drive the input method while it is composing (e.g. pinyin).
  if (isComposing(e)) return
  if (e.key === 'ArrowDown') {
    open.value = true
    active.value = Math.min(active.value + 1, visible.value.length - 1)
    e.preventDefault()
  } else if (e.key === 'ArrowUp') {
    active.value = Math.max(active.value - 1, 0)
    e.preventDefault()
  } else if (e.key === 'Enter' && open.value && visible.value[active.value]) {
    pick(visible.value[active.value])
    e.preventDefault()
  } else if (e.key === 'Backspace' && !query.value && model.value.length) {
    remove(model.value[model.value.length - 1].id)
  } else if (e.key === 'Escape') {
    open.value = false
  }
}

async function onFocus() {
  open.value = true
  if (!results.value.length && !query.value) {
    try {
      results.value = await api.users.search('', 20)
    } catch {
      /* suggestions are optional */
    }
  }
}
</script>

<template>
  <div class="picker" :class="{ invalid }">
    <div class="box" @click="inputEl?.focus()">
      <span v-for="p in model" :key="p.id" class="chip">
        <UiAvatar :name="p.name" :size="20" />{{ p.name }}
        <button type="button" class="chip-x" :aria-label="`${$t('common.remove')} ${p.name}`" @click.stop="remove(p.id)"><X :size="12" /></button>
      </span>
      <input
        v-if="multiple || !model.length"
        :id="inputId"
        ref="inputEl"
        v-model="query"
        class="q"
        role="combobox"
        autocomplete="off"
        :aria-expanded="open && visible.length > 0"
        :aria-controls="listId"
        :placeholder="model.length ? '' : (placeholder ?? $t('picker.placeholder'))"
        @focus="onFocus"
        @blur="open = false"
        @keydown="onKey"
      />
    </div>
    <ul v-if="open && (visible.length || query)" :id="listId" class="results" role="listbox">
      <li
        v-for="(p, i) in visible"
        :key="p.id"
        role="option"
        :aria-selected="i === active"
        class="option"
        :class="{ active: i === active }"
        @mousedown.prevent="pick(p)"
        @mouseenter="active = i"
      >
        <UiAvatar :name="p.name" :size="24" />{{ p.name }}
      </li>
      <li v-if="!visible.length" class="none">{{ $t('picker.noMatches') }}</li>
    </ul>
  </div>
</template>

<style scoped>
.picker {
  position: relative;
}
.box {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  min-height: 40px;
  padding: 5px 8px;
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-sm);
  background: var(--surface);
  cursor: text;
}
.box:focus-within {
  border-color: var(--accent);
  box-shadow: var(--focus);
}
.invalid .box {
  border-color: var(--danger);
}
.chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-block-size: 1.75rem;
  padding: 0 4px 0 4px;
  border-radius: 999px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  font-size: 0.85rem;
  font-weight: 550;
}
.chip-x {
  display: grid;
  place-items: center;
  width: 20px;
  height: 20px;
  border: 0;
  border-radius: 50%;
  background: transparent;
  color: var(--text-3);
  cursor: pointer;
}
.chip-x:hover {
  background: var(--surface-3);
  color: var(--text);
}
.q {
  flex: 1;
  min-width: 120px;
  border: 0;
  outline: none;
  background: transparent;
  min-block-size: 1.75rem;
  padding: 0 4px;
}
.q:focus-visible {
  box-shadow: none;
}
.results {
  position: absolute;
  z-index: 30;
  top: calc(100% + 4px);
  left: 0;
  right: 0;
  list-style: none;
  margin: 0;
  padding: 4px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  box-shadow: var(--shadow-lg);
  max-height: 260px;
  overflow-y: auto;
}
.option {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 8px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.9rem;
}
.option.active {
  background: var(--accent-soft);
}
.none {
  padding: 8px;
  color: var(--text-3);
  font-size: 0.85rem;
}
</style>
