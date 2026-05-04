const ARCUS_CHAT_EVENT = 'arcus-chat-open';
const ARCUS_CHAT_PENDING_KEY = 'arcus-chat-pending-message';

export function openArcusChat(message: string) {
  if (typeof window === 'undefined') return;
  const trimmed = message.trim();
  if (!trimmed) return;

  sessionStorage.setItem(ARCUS_CHAT_PENDING_KEY, trimmed);
  window.dispatchEvent(new CustomEvent(ARCUS_CHAT_EVENT, { detail: { message: trimmed } }));
}

export function consumePendingArcusChatMessage() {
  if (typeof window === 'undefined') return '';
  const pending = sessionStorage.getItem(ARCUS_CHAT_PENDING_KEY) || '';
  if (pending) sessionStorage.removeItem(ARCUS_CHAT_PENDING_KEY);
  return pending;
}

export { ARCUS_CHAT_EVENT };
