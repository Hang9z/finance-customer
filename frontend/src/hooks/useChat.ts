import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  COMMON_WEALTH_CARDS,
  CUSTOMER_PRESETS,
  DEFAULT_CUSTOMER_ID,
  STORAGE_CUSTOMER_KEY,
} from '../constants/presets';
import {
  applyTurnTextsToWorkflow,
  createInitialWorkflowState,
  parseTaskEvent,
} from '../lib/events';
import { parseReceiptsAndCleanMarkdown } from '../lib/receipts';
import {
  buildObjectRequest,
  buildTextRequest,
  checkEngineHealth,
  checkFinanceApiHealth,
  createMessageId,
  EngineOfflineError,
  fetchHistory,
  sendChat,
} from '../services/api';
import {
  ChatMessage,
  ChatObject,
  ReceiptData,
  ServiceHealthStatus,
  TimelineItem,
  WalletCard,
  WorkflowState,
} from '../types/chat';

function getInitialCustomerId(): string {
  try {
    const saved = window.localStorage.getItem(STORAGE_CUSTOMER_KEY);
    if (saved && saved.trim()) {
      return saved.trim();
    }
  } catch {
    // 忽略 storage 读写受限场景
  }
  return DEFAULT_CUSTOMER_ID;
}

function buildWalletForCustomer(
  customerId: string,
  customCards: WalletCard[],
  sessionTickets: WalletCard[],
): WalletCard[] {
  const preset = CUSTOMER_PRESETS.find((c) => c.id === customerId);
  const baseCards = preset ? preset.cards : [];
  const merged: WalletCard[] = [...baseCards, ...COMMON_WEALTH_CARDS];

  for (const extra of [...customCards, ...sessionTickets]) {
    if (!merged.some((item) => item.type === extra.type && item.id === extra.id)) {
      merged.push(extra);
    }
  }
  return merged;
}

export function useChat() {
  const [customerId, setCustomerId] = useState<string>(getInitialCustomerId);
  const [timeline, setTimeline] = useState<TimelineItem[]>([]);
  const [receipts, setReceipts] = useState<ReceiptData[]>([]);
  const [workflow, setWorkflow] = useState<WorkflowState>(createInitialWorkflowState);
  const [isLoadingHistory, setIsLoadingHistory] = useState<boolean>(false);
  const [isSending, setIsSending] = useState<boolean>(false);
  const [engineStatus, setEngineStatus] = useState<ServiceHealthStatus>('checking');
  const [financeStatus, setFinanceStatus] = useState<ServiceHealthStatus>('checking');
  const [engineOfflineBanner, setEngineOfflineBanner] = useState<boolean>(false);
  const [customCards, setCustomCards] = useState<WalletCard[]>([]);
  const [sessionTickets, setSessionTickets] = useState<WalletCard[]>([]);

  const activeCustomerRef = useRef<string>(customerId);
  const historyAbortRef = useRef<AbortController | null>(null);
  const sendAbortRef = useRef<AbortController | null>(null);
  const isSendingRef = useRef<boolean>(false);

  useEffect(() => {
    activeCustomerRef.current = customerId;
  }, [customerId]);

  const appendTicketsFromDiscovered = useCallback(
    (tickets: Array<{ ticketNo: string; category: string }>) => {
      if (tickets.length === 0) {
        return;
      }
      setSessionTickets((prev) => {
        const next = [...prev];
        for (const tkt of tickets) {
          if (!next.some((item) => item.id === tkt.ticketNo)) {
            next.push({
              type: 'ticket',
              id: tkt.ticketNo,
              title: `工单 · ${tkt.category}`,
              attributes: { category: tkt.category, status: '已登记' },
              questionPrompt: `请帮我查询工单 ${tkt.ticketNo} 的当前处理进度。`,
              isSessionTicket: true,
            });
          }
        }
        return next;
      });
    },
    [],
  );

  const loadHistory = useCallback(
    async (targetCustomerId: string) => {
      if (historyAbortRef.current) {
        historyAbortRef.current.abort();
      }
      const controller = new AbortController();
      historyAbortRef.current = controller;

      setIsLoadingHistory(true);
      try {
        const data = await fetchHistory(targetCustomerId, controller.signal);
        if (activeCustomerRef.current !== targetCustomerId) {
          return;
        }

        setEngineStatus('online');
        setEngineOfflineBanner(false);

        const nextTimeline: TimelineItem[] = [];
        const nextReceipts: ReceiptData[] = [];
        const allDiscoveredTickets: Array<{ ticketNo: string; category: string }> = [];
        let nextWorkflow = createInitialWorkflowState();
        let currentTurnBotTexts: string[] = [];

        const flushTurn = () => {
          if (currentTurnBotTexts.length > 0) {
            nextWorkflow = applyTurnTextsToWorkflow(nextWorkflow, currentTurnBotTexts);
            currentTurnBotTexts = [];
          }
        };

        data.messages.forEach((msg, index) => {
          const itemId = `hist_${targetCustomerId}_${index}`;
          if (msg.role === 'user') {
            flushTurn();
            nextTimeline.push({
              id: itemId,
              kind: 'user',
              messageId: itemId,
              text: msg.text ?? null,
              object: msg.object ?? null,
              status: 'sent',
            });
          } else {
            const rawText = msg.text ?? '';
            if (rawText) {
              currentTurnBotTexts.push(rawText);
              const event = parseTaskEvent(rawText);
              if (event) {
                nextTimeline.push({ id: itemId, kind: 'event', event });
              } else {
                const parsed = parseReceiptsAndCleanMarkdown(rawText, itemId);
                nextTimeline.push({
                  id: itemId,
                  kind: 'bot',
                  text: parsed.cleanMarkdown,
                  receipts: parsed.receipts,
                });
                nextReceipts.push(...parsed.receipts);
                allDiscoveredTickets.push(...parsed.discoveredTickets);
              }
            }
          }
        });
        flushTurn();

        setTimeline(nextTimeline);
        setReceipts(nextReceipts);
        setWorkflow(nextWorkflow);
        appendTicketsFromDiscovered(allDiscoveredTickets);
      } catch (err) {
        if (err instanceof DOMException && err.name === 'AbortError') {
          return;
        }
        if (activeCustomerRef.current !== targetCustomerId) {
          return;
        }
        if (err instanceof EngineOfflineError) {
          setEngineStatus('offline');
          setEngineOfflineBanner(true);
        }
      } finally {
        if (activeCustomerRef.current === targetCustomerId) {
          setIsLoadingHistory(false);
        }
      }
    },
    [appendTicketsFromDiscovered],
  );

  const runHealthChecks = useCallback(async () => {
    const [engOk, finOk] = await Promise.all([
      checkEngineHealth(),
      checkFinanceApiHealth(),
    ]);
    setEngineStatus(engOk ? 'online' : 'offline');
    setFinanceStatus(finOk ? 'online' : 'offline');
    if (engOk) {
      setEngineOfflineBanner(false);
    } else {
      setEngineOfflineBanner(true);
    }
  }, []);

  useEffect(() => {
    void runHealthChecks();
    const timer = window.setInterval(() => {
      void runHealthChecks();
    }, 30_000);
    return () => window.clearInterval(timer);
  }, [runHealthChecks]);

  useEffect(() => {
    void loadHistory(customerId);
  }, [customerId, loadHistory]);

  const switchCustomer = useCallback((nextId: string) => {
    const trimmed = nextId.trim();
    if (!trimmed || trimmed === activeCustomerRef.current) {
      return;
    }

    if (historyAbortRef.current) {
      historyAbortRef.current.abort();
    }
    if (sendAbortRef.current) {
      sendAbortRef.current.abort();
      sendAbortRef.current = null;
    }

    isSendingRef.current = false;
    setIsSending(false);
    setTimeline([]);
    setReceipts([]);
    setSessionTickets([]);
    setWorkflow(createInitialWorkflowState());
    activeCustomerRef.current = trimmed;

    try {
      window.localStorage.setItem(STORAGE_CUSTOMER_KEY, trimmed);
    } catch {
      // 忽略 storage 异常
    }

    setCustomerId(trimmed);
  }, []);

  const clearLocalView = useCallback(() => {
    setTimeline([]);
    setReceipts([]);
    setSessionTickets([]);
    setWorkflow(createInitialWorkflowState());
  }, []);

  const appendBotMessages = useCallback(
    (botMessages: ChatMessage[], baseMsgId: string) => {
      const botTexts: string[] = [];
      const newItems: TimelineItem[] = [];
      const newReceipts: ReceiptData[] = [];
      const discoveredTickets: Array<{ ticketNo: string; category: string }> = [];

      botMessages.forEach((msg, idx) => {
        const rawText = msg.text ?? '';
        if (!rawText) {
          return;
        }
        botTexts.push(rawText);
        const itemId = `${baseMsgId}_bot_${idx}`;
        const event = parseTaskEvent(rawText);
        if (event) {
          newItems.push({ id: itemId, kind: 'event', event });
        } else {
          const parsed = parseReceiptsAndCleanMarkdown(rawText, itemId);
          newItems.push({
            id: itemId,
            kind: 'bot',
            text: parsed.cleanMarkdown,
            receipts: parsed.receipts,
          });
          newReceipts.push(...parsed.receipts);
          discoveredTickets.push(...parsed.discoveredTickets);
        }
      });

      setTimeline((prev) => [...prev, ...newItems]);
      if (newReceipts.length > 0) {
        setReceipts((prev) => [...prev, ...newReceipts]);
      }
      if (discoveredTickets.length > 0) {
        appendTicketsFromDiscovered(discoveredTickets);
      }
      setWorkflow((prev) => applyTurnTextsToWorkflow(prev, botTexts));
    },
    [appendTicketsFromDiscovered],
  );

  const sendPayload = useCallback(
    async (
      options: { text?: string | null; object?: ChatObject | null },
      reuseTimelineId?: string,
    ): Promise<boolean> => {
      if (isSendingRef.current) {
        return false;
      }

      const targetCustomerId = activeCustomerRef.current;
      const newMsgId = createMessageId();
      const itemId = reuseTimelineId ?? `user_${newMsgId}`;

      if (reuseTimelineId) {
        setTimeline((prev) =>
          prev.map((item) =>
            item.id === reuseTimelineId && item.kind === 'user'
              ? { ...item, messageId: newMsgId, status: 'sent' }
              : item,
          ),
        );
      } else {
        setTimeline((prev) => [
          ...prev,
          {
            id: itemId,
            kind: 'user',
            messageId: newMsgId,
            text: options.text ?? null,
            object: options.object ?? null,
            status: 'sent',
          },
        ]);
      }

      const controller = new AbortController();
      sendAbortRef.current = controller;
      isSendingRef.current = true;
      setIsSending(true);

      try {
        const request = options.object
          ? buildObjectRequest(targetCustomerId, options.object, newMsgId)
          : buildTextRequest(targetCustomerId, (options.text ?? '').trim(), newMsgId);

        const response = await sendChat(request, controller.signal);

        // 切换客户后丢弃旧客户的迟到响应
        if (activeCustomerRef.current !== targetCustomerId) {
          return false;
        }

        setEngineStatus('online');
        setEngineOfflineBanner(false);
        appendBotMessages(response.messages, newMsgId);
        return true;
      } catch (err) {
        if (activeCustomerRef.current !== targetCustomerId) {
          return false;
        }
        if (err instanceof DOMException && err.name === 'AbortError') {
          setTimeline((prev) =>
            prev.map((item) =>
              item.id === itemId && item.kind === 'user'
                ? { ...item, status: 'failed' }
                : item,
            ),
          );
          return false;
        }
        if (err instanceof EngineOfflineError) {
          setEngineStatus('offline');
          setEngineOfflineBanner(true);
        }
        setTimeline((prev) =>
          prev.map((item) =>
            item.id === itemId && item.kind === 'user'
              ? { ...item, status: 'failed' }
              : item,
          ),
        );
        return false;
      } finally {
        if (sendAbortRef.current === controller) {
          sendAbortRef.current = null;
        }
        if (activeCustomerRef.current === targetCustomerId) {
          isSendingRef.current = false;
          setIsSending(false);
        }
      }
    },
    [appendBotMessages],
  );

  const sendText = useCallback(
    async (text: string): Promise<boolean> => {
      const trimmed = text.trim();
      if (!trimmed) {
        return false;
      }
      return sendPayload({ text: trimmed, object: null });
    },
    [sendPayload],
  );

  const sendObject = useCallback(
    async (card: ChatObject): Promise<boolean> => {
      return sendPayload({ text: null, object: card });
    },
    [sendPayload],
  );

  const retryFailedMessage = useCallback(
    async (timelineId: string): Promise<boolean> => {
      const target = timeline.find(
        (item): item is Extract<TimelineItem, { kind: 'user' }> =>
          item.id === timelineId && item.kind === 'user',
      );
      if (!target) {
        return false;
      }
      return sendPayload(
        { text: target.text ?? null, object: target.object ?? null },
        timelineId,
      );
    },
    [sendPayload, timeline],
  );

  const addCustomCard = useCallback((card: WalletCard) => {
    setCustomCards((prev) => {
      const filtered = prev.filter(
        (c) => !(c.type === card.type && c.id === card.id),
      );
      return [...filtered, card];
    });
  }, []);

  const walletCards = useMemo(
    () => buildWalletForCustomer(customerId, customCards, sessionTickets),
    [customerId, customCards, sessionTickets],
  );

  const awaitingAccountQuestion = useMemo(() => {
    const lastBot = [...timeline]
      .reverse()
      .find((item): item is Extract<TimelineItem, { kind: 'bot' }> => item.kind === 'bot');
    const question = workflow.active?.awaitingQuestion ?? lastBot?.text ?? '';
    if (
      question &&
      (question.includes('卡号') || question.includes('账户号')) &&
      (workflow.active !== null || question.startsWith('请提供'))
    ) {
      return question;
    }
    return null;
  }, [timeline, workflow.active]);

  return {
    customerId,
    timeline,
    receipts,
    workflow,
    walletCards,
    awaitingAccountQuestion,
    isLoadingHistory,
    isSending,
    engineStatus,
    financeStatus,
    engineOfflineBanner,
    switchCustomer,
    refreshHistory: () => loadHistory(customerId),
    reconnectEngine: runHealthChecks,
    clearLocalView,
    sendText,
    sendObject,
    retryFailedMessage,
    addCustomCard,
  };
}
