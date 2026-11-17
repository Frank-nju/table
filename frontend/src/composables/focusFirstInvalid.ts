import { nextTick } from 'vue'

/**
 * After a failed submit, move focus to the first invalid field so screen readers announce its error.
 * Native validation already does this for constraint errors; this covers errors returned by the server.
 */
export async function focusFirstInvalid(root: ParentNode | null | undefined): Promise<void> {
  await nextTick()
  root?.querySelector<HTMLElement>('[aria-invalid="true"], :user-invalid')?.focus()
}
