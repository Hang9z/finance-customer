import {
  ChatObject,
  ChatRequest,
  ChatResponse,
  CustomerAssetsResponse,
  HistoryResponse,
  RagStatusResponse,
} from '../types/chat';

const CHAT_TIMEOUT_MS = 180_000;

interface CachedSessionToken {
  token: string;
  expiresAt: number;
}

const sessionTokenCache = new Map<string, CachedSessionToken>();

export interface ChatStreamCallbacks {
  onStage?: (stage: string, label: string) => void;
  onDelta?: (deltaText: string) => void;
}

export class EngineOfflineError extends Error {
  constructor(message = '无法连接智能客服引擎（127.0.0.1:18082）') {
    super(message);
    this.name = 'EngineOfflineError';
  }
}

export function createMessageId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID();
  }
  return `msg_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
}

export function buildTextRequest(
  senderId: string,
  text: string,
  messageId = createMessageId(),
): ChatRequest {
  return {
    sender_id: senderId,
    text,
    object: null,
    message_id: messageId,
  };
}

export function buildObjectRequest(
  senderId: string,
  object: ChatObject,
  messageId = createMessageId(),
): ChatRequest {
  return {
    sender_id: senderId,
    text: null,
    object,
    message_id: messageId,
  };
}

function linkAbortSignals(
  externalSignal?: AbortSignal,
  timeoutMs = CHAT_TIMEOUT_MS,
): { signal: AbortSignal; cleanup: () => void; isTimeout: () => boolean } {
  const controller = new AbortController();
  let timedOut = false;

  const onExternalAbort = () => controller.abort();
  if (externalSignal) {
    if (externalSignal.aborted) {
      controller.abort();
    } else {
      externalSignal.addEventListener('abort', onExternalAbort, { once: true });
    }
  }

  const timer = window.setTimeout(() => {
    timedOut = true;
    controller.abort();
  }, timeoutMs);

  return {
    signal: controller.signal,
    isTimeout: () => timedOut,
    cleanup: () => {
      window.clearTimeout(timer);
      if (externalSignal) {
        externalSignal.removeEventListener('abort', onExternalAbort);
      }
    },
  };
}

function isGatewayError(status: number): boolean {
  return status === 502 || status === 503 || status === 504;
}

export async function ensureSessionToken(
  senderId: string,
  forceRefresh = false,
): Promise<string | null> {
  const cleanId = senderId.trim();
  if (!cleanId || cleanId === '__healthcheck__') {
    return null;
  }

  const now = Date.now();
  const cached = sessionTokenCache.get(cleanId);
  if (!forceRefresh && cached && cached.expiresAt - now > 30_000) {
    return cached.token;
  }

  try {
    const response = await fetch('/api/auth/session', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ customer_no: cleanId }),
    });
    if (!response.ok) {
      return null;
    }
    const data = (await response.json()) as { access_token?: string; expires_in?: number };
    if (!data.access_token) {
      return null;
    }
    const ttlMs = (data.expires_in ?? 7200) * 1000;
    sessionTokenCache.set(cleanId, {
      token: data.access_token,
      expiresAt: now + ttlMs,
    });
    return data.access_token;
  } catch {
    return null;
  }
}

async function fetchWithSessionAuth(
  senderId: string,
  url: string,
  init: RequestInit,
): Promise<Response> {
  const token = await ensureSessionToken(senderId, false);
  const headers = new Headers(init.headers);
  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }
  const response = await fetch(url, { ...init, headers });
  if (response.status === 401 && senderId !== '__healthcheck__') {
    const refreshed = await ensureSessionToken(senderId, true);
    if (refreshed) {
      const retryHeaders = new Headers(init.headers);
      retryHeaders.set('Authorization', `Bearer ${refreshed}`);
      return fetch(url, { ...init, headers: retryHeaders });
    }
  }
  return response;
}

export async function sendChat(
  payload: ChatRequest,
  externalSignal?: AbortSignal,
): Promise<ChatResponse> {
  const { signal, cleanup, isTimeout } = linkAbortSignals(externalSignal, CHAT_TIMEOUT_MS);

  try {
    const response = await fetchWithSessionAuth(payload.sender_id, '/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal,
    });

    if (isGatewayError(response.status)) {
      throw new EngineOfflineError(`客服引擎网关不可用 (${response.status})`);
    }
    if (!response.ok) {
      throw new Error(`请求失败 (${response.status})`);
    }

    return (await response.json()) as ChatResponse;
  } catch (err) {
    if (err instanceof EngineOfflineError) {
      throw err;
    }
    if (err instanceof DOMException && err.name === 'AbortError') {
      if (isTimeout()) {
        throw new Error('请求超时（90秒），请重试');
      }
      throw err;
    }
    if (err instanceof TypeError) {
      throw new EngineOfflineError();
    }
    throw err;
  } finally {
    cleanup();
  }
}

function processSseBlock(
  block: string,
  callbacks: ChatStreamCallbacks,
): ChatResponse | null {
  const lines = block.split(/\r?\n/);
  let eventName = 'message';
  const dataLines: string[] = [];

  for (const line of lines) {
    if (line.startsWith('event:')) {
      eventName = line.slice(6).trim();
    } else if (line.startsWith('data:')) {
      dataLines.push(line.slice(5).trimStart());
    }
  }
  const dataRaw = dataLines.join('\n');
  if (!dataRaw) {
    return null;
  }

  if (eventName === 'stage') {
    const parsed = JSON.parse(dataRaw) as { stage?: string; label?: string };
    callbacks.onStage?.(parsed.stage ?? '', parsed.label ?? '');
    return null;
  }
  if (eventName === 'delta') {
    const parsed = JSON.parse(dataRaw) as { text?: string };
    if (parsed.text) {
      callbacks.onDelta?.(parsed.text);
    }
    return null;
  }
  if (eventName === 'error') {
    const parsed = JSON.parse(dataRaw) as { message?: string };
    throw new Error(parsed.message || '智能客服流式响应失败');
  }
  if (eventName === 'done') {
    return JSON.parse(dataRaw) as ChatResponse;
  }
  return null;
}

export async function sendChatStream(
  payload: ChatRequest,
  callbacks: ChatStreamCallbacks,
  externalSignal?: AbortSignal,
): Promise<ChatResponse> {
  const { signal, cleanup, isTimeout } = linkAbortSignals(externalSignal, CHAT_TIMEOUT_MS);

  try {
    const response = await fetchWithSessionAuth(payload.sender_id, '/api/chat/stream', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'text/event-stream',
      },
      body: JSON.stringify(payload),
      signal,
    });

    if (isGatewayError(response.status)) {
      throw new EngineOfflineError(`客服引擎网关不可用 (${response.status})`);
    }
    const contentType = response.headers.get('content-type') ?? '';
    if (response.status === 404 || !contentType.includes('text/event-stream')) {
      return sendChat(payload, externalSignal);
    }
    if (!response.ok || !response.body) {
      throw new Error(`流式请求失败 (${response.status})`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';
    let finalResponse: ChatResponse | null = null;

    while (true) {
      const { value, done } = await reader.read();
      if (value) {
        buffer += decoder.decode(value, { stream: !done });
        const parts = buffer.split(/\r?\n\r?\n/);
        buffer = parts.pop() ?? '';
        for (const block of parts) {
          if (block.trim()) {
            const parsedDone = processSseBlock(block, callbacks);
            if (parsedDone) {
              finalResponse = parsedDone;
            }
          }
        }
      }
      if (done) {
        break;
      }
    }

    const tail = buffer + decoder.decode();
    if (tail.trim()) {
      const parsedDone = processSseBlock(tail, callbacks);
      if (parsedDone) {
        finalResponse = parsedDone;
      }
    }

    if (!finalResponse) {
      throw new Error('未收到完整的流式响应结果');
    }
    return finalResponse;
  } catch (err) {
    if (err instanceof EngineOfflineError) {
      throw err;
    }
    if (err instanceof DOMException && err.name === 'AbortError') {
      if (isTimeout()) {
        throw new Error('请求超时（90秒），请重试');
      }
      throw err;
    }
    if (err instanceof TypeError) {
      throw new EngineOfflineError();
    }
    throw err;
  } finally {
    cleanup();
  }
}

export async function fetchHistory(
  senderId: string,
  externalSignal?: AbortSignal,
): Promise<HistoryResponse> {
  const { signal, cleanup } = linkAbortSignals(externalSignal, 15_000);
  try {
    const response = await fetchWithSessionAuth(
      senderId,
      `/api/chat/history?sender_id=${encodeURIComponent(senderId)}`,
      { signal },
    );

    if (isGatewayError(response.status)) {
      throw new EngineOfflineError(`客服引擎网关不可用 (${response.status})`);
    }
    if (!response.ok) {
      throw new Error(`历史加载失败 (${response.status})`);
    }

    return (await response.json()) as HistoryResponse;
  } catch (err) {
    if (err instanceof EngineOfflineError) {
      throw err;
    }
    if (err instanceof TypeError) {
      throw new EngineOfflineError();
    }
    throw err;
  } finally {
    cleanup();
  }
}

export async function fetchCustomerAssets(
  senderId: string,
  externalSignal?: AbortSignal,
): Promise<CustomerAssetsResponse | null> {
  const cleanId = senderId.trim();
  if (!cleanId || cleanId === '__healthcheck__') {
    return null;
  }
  const { signal, cleanup } = linkAbortSignals(externalSignal, 10_000);
  try {
    const response = await fetchWithSessionAuth(
      cleanId,
      `/api/customer/assets?sender_id=${encodeURIComponent(cleanId)}`,
      { signal },
    );
    if (!response.ok) {
      return null;
    }
    return (await response.json()) as CustomerAssetsResponse;
  } catch {
    return null;
  } finally {
    cleanup();
  }
}

export async function checkEngineHealth(externalSignal?: AbortSignal): Promise<boolean> {
  const { signal, cleanup } = linkAbortSignals(externalSignal, 5_000);
  try {
    const response = await fetch(
      '/api/chat/history?sender_id=__healthcheck__',
      { signal },
    );
    return response.ok;
  } catch {
    return false;
  } finally {
    cleanup();
  }
}

export async function checkFinanceApiHealth(externalSignal?: AbortSignal): Promise<boolean> {
  const { signal, cleanup } = linkAbortSignals(externalSignal, 5_000);
  try {
    const response = await fetch('/finance-api/health', { signal });
    return response.ok;
  } catch {
    return false;
  } finally {
    cleanup();
  }
}

export async function fetchRagStatus(
  externalSignal?: AbortSignal,
): Promise<RagStatusResponse | null> {
  const { signal, cleanup } = linkAbortSignals(externalSignal, 5_000);
  try {
    const response = await fetch('/api/rag/status', { signal });
    if (!response.ok) {
      return null;
    }
    return (await response.json()) as RagStatusResponse;
  } catch {
    return null;
  } finally {
    cleanup();
  }
}
