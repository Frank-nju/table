/**
 * True while an input method (pinyin, kana, Hangul...) is composing text. During composition, Enter
 * confirms a candidate and the arrow keys move through candidates, so custom key handlers must ignore
 * them. Safari can report isComposing=false on the confirming Enter, but it still sends keyCode 229.
 */
export function isComposing(event: KeyboardEvent): boolean {
  return event.isComposing || event.keyCode === 229
}
