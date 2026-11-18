import {
  ChatObject,
  ChatRequest,
  ChatResponse,
  HistoryResponse,
} from '../types/chat';

const CHAT_TIMEOUT_MS = 90_000;

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

export async function sendChat(
  payload: ChatRequest,
  externalSignal?: AbortSignal,
): Promise<ChatResponse> {
  const { signal, cleanup, isTimeout } = linkAbortSignals(externalSignal, CHAT_TIMEOUT_MS);

  try {
    const response = await fetch('/api/chat', {
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

export async function fetchHistory(
  senderId: string,
  externalSignal?: AbortSignal,
): Promise<HistoryResponse> {
  const { signal, cleanup } = linkAbortSignals(externalSignal, 15_000);
  try {
    const response = await fetch(
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
