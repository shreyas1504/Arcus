const ARCUS_CHAT_EVENT = 'arcus-chat-open';
const ARCUS_CHAT_PENDING_KEY = 'arcus-chat-pending-message';

export function openArcusChat(message: string) {
  if (typeof window === 'undefined') return;
  const trimmed = message.trim();
  if (!trimmed) return;

  sessionStorage.setItem(ARCUS_CHAT_PENDING_KEY, trimmed);
  const baseUrl = new URL(import.meta.env.BASE_URL || '/', window.location.origin);
  const chatUrl = new URL('chat', baseUrl);
  const normalize = (value: string) => value.replace(/\/+$/, '') || '/';
  const isOnChatRoute = normalize(window.location.pathname) === normalize(chatUrl.pathname);

  if (isOnChatRoute) {
    window.dispatchEvent(new CustomEvent(ARCUS_CHAT_EVENT, { detail: { message: trimmed } }));
    sessionStorage.removeItem(ARCUS_CHAT_PENDING_KEY);
    return;
  }

  window.location.assign(chatUrl.toString());
}

export function consumePendingArcusChatMessage() {
  if (typeof window === 'undefined') return '';
  const pending = sessionStorage.getItem(ARCUS_CHAT_PENDING_KEY) || '';
  if (pending) sessionStorage.removeItem(ARCUS_CHAT_PENDING_KEY);
  return pending;
}

export { ARCUS_CHAT_EVENT };
