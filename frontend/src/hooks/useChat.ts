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
  mapServerWorkflowToState,
  parseTaskEvent,
} from '../lib/events';
import { normalizeServerReceipt, parseReceiptsAndCleanMarkdown } from '../lib/receipts';
import {
  buildObjectRequest,
  buildTextRequest,
  checkEngineHealth,
  checkFinanceApiHealth,
  createMessageId,
  EngineOfflineError,
  fetchCustomerAssets,
  fetchHistory,
  fetchRagStatus,
  sendChatStream,
} from '../services/api';
import {
  ChatMessage,
  ChatObject,
  CustomerAssetAccount,
  CustomerCreditLimit,
  KnowledgeCitation,
  QuickReplyOption,
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
  liveAccounts: CustomerAssetAccount[],
  customCards: WalletCard[],
  sessionTickets: WalletCard[],
  sessionLoans: WalletCard[],
): WalletCard[] {
  const preset = CUSTOMER_PRESETS.find((c) => c.id === customerId);
  const baseCards = preset ? preset.cards : [];

  const liveBalanceByAccount = new Map<string, string>();
  for (const acc of liveAccounts) {
    if (acc.account_no) {
      liveBalanceByAccount.set(
        acc.account_no,
        `${acc.balance_amount} ${acc.currency_code || 'CNY'}`,
      );
    }
  }

  const hydratedPresets: WalletCard[] = baseCards.map((card) => {
    if (card.type === 'account') {
      const liveBal = liveBalanceByAccount.get(card.id);
      if (liveBal) {
        return { ...card, attributes: { ...card.attributes, balance: liveBal } };
      }
    }
    if (card.type === 'card' && card.attributes.accountNo) {
      const liveBal = liveBalanceByAccount.get(card.attributes.accountNo);
      if (liveBal) {
        return { ...card, attributes: { ...card.attributes, balance: liveBal } };
      }
    }
    return card;
  });

  const extraLiveAccountCards: WalletCard[] = liveAccounts
    .filter(
      (acc) =>
        acc.account_no &&
        !hydratedPresets.some((card) => card.type === 'account' && card.id === acc.account_no),
    )
    .map((acc) => ({
      type: 'account',
      id: acc.account_no,
      title: acc.account_product?.product_name || '银行活期账户',
      attributes: {
        balance: `${acc.balance_amount} ${acc.currency_code || 'CNY'}`,
        status: '正常',
        ...(acc.account_product?.product_code
          ? { product: acc.account_product.product_code }
          : {}),
      },
      questionPrompt: `帮我查询账户 ${acc.account_no} 的余额和近期交易流水。`,
    }));

  const merged: WalletCard[] = [
    ...hydratedPresets,
    ...extraLiveAccountCards,
    ...COMMON_WEALTH_CARDS,
  ];

  for (const extra of [...customCards, ...sessionLoans, ...sessionTickets]) {
    if (!merged.some((item) => item.type === extra.type && item.id === extra.id)) {
      merged.push(extra);
    }
  }
  return merged;
}

const TX_RAW_LINE_RE = /^\d+\.\s*\[[^\]]+\]\s+\S+\s+[\d,.]+\s+\S+\s*\|/;

interface ProcessedBotMessage {
  item: TimelineItem;
  receipts: ReceiptData[];
  discoveredTickets: Array<{ ticketNo: string; category: string }>;
  discoveredLoans: Array<{ applicationNo: string; amount: string; status: string }>;
  rawText: string;
}

function normalizeCitations(raw: ChatMessage['citations']): KnowledgeCitation[] {
  if (!Array.isArray(raw)) {
    return [];
  }
  return raw.filter(
    (c): c is KnowledgeCitation =>
      Boolean(c && typeof c === 'object' && typeof c.source === 'string' && c.source.trim()),
  );
}

function processServerBotMessage(
  msg: {
    text?: string | null;
    receipt?: Record<string, unknown> | null;
    event?: ChatMessage['event'];
    citations?: ChatMessage['citations'];
  },
  itemId: string,
): ProcessedBotMessage | null {
  const rawText = msg.text ?? '';
  const serverEvent = msg.event ?? (rawText ? parseTaskEvent(rawText) : null);
  if (serverEvent) {
    return {
      item: { id: itemId, kind: 'event', event: serverEvent },
      receipts: [],
      discoveredTickets: [],
      discoveredLoans: [],
      rawText,
    };
  }
  if (!rawText && !msg.receipt) {
    return null;
  }

  const citations = normalizeCitations(msg.citations);
  const discoveredTickets: Array<{ ticketNo: string; category: string }> = [];
  const discoveredLoans: Array<{ applicationNo: string; amount: string; status: string }> = [];

  if (msg.receipt) {
    const receipt = normalizeServerReceipt(msg.receipt, `${itemId}_srv`);
    if (receipt) {
      let cleanMarkdown = rawText;
      if (receipt.kind === 'transactions') {
        cleanMarkdown = rawText
          .split(/\r?\n/)
          .filter((line) => !TX_RAW_LINE_RE.test(line.trim()))
          .join('\n')
          .trim();
      } else if (receipt.kind === 'ticket') {
        discoveredTickets.push({ ticketNo: receipt.ticketNo, category: receipt.category });
      } else if (receipt.kind === 'loan') {
        discoveredLoans.push({
          applicationNo: receipt.applicationNo,
          amount: receipt.amount,
          status: receipt.status,
        });
      }
      return {
        item: {
          id: itemId,
          kind: 'bot',
          text: cleanMarkdown,
          receipts: [receipt],
          ...(citations.length > 0 ? { citations } : {}),
        },
        receipts: [receipt],
        discoveredTickets,
        discoveredLoans,
        rawText,
      };
    }
  }

  const parsed = parseReceiptsAndCleanMarkdown(rawText, itemId);
  for (const rcpt of parsed.receipts) {
    if (rcpt.kind === 'loan') {
      discoveredLoans.push({
        applicationNo: rcpt.applicationNo,
        amount: rcpt.amount,
        status: rcpt.status,
      });
    }
  }
  return {
    item: {
      id: itemId,
      kind: 'bot',
      text: parsed.cleanMarkdown,
      receipts: parsed.receipts,
      ...(citations.length > 0 ? { citations } : {}),
    },
    receipts: parsed.receipts,
    discoveredTickets: parsed.discoveredTickets,
    discoveredLoans,
    rawText,
  };
}

export function useChat() {
  const [customerId, setCustomerId] = useState<string>(getInitialCustomerId);
  const [timeline, setTimeline] = useState<TimelineItem[]>([]);
  const [receipts, setReceipts] = useState<ReceiptData[]>([]);
  const [workflow, setWorkflow] = useState<WorkflowState>(createInitialWorkflowState);
  const [quickReplies, setQuickReplies] = useState<QuickReplyOption[]>([]);
  const [streamStageLabel, setStreamStageLabel] = useState<string | null>(null);
  const [isLoadingHistory, setIsLoadingHistory] = useState<boolean>(false);
  const [isSending, setIsSending] = useState<boolean>(false);
  const [engineStatus, setEngineStatus] = useState<ServiceHealthStatus>('checking');
  const [financeStatus, setFinanceStatus] = useState<ServiceHealthStatus>('checking');
  const [ragStatus, setRagStatus] = useState<ServiceHealthStatus>('checking');
  const [ragEndpoints, setRagEndpoints] = useState<{
    chatUrl: string;
    importUrl: string;
    importOnline: boolean;
  }>({
    chatUrl: 'http://127.0.0.1:8001/chat.html',
    importUrl: 'http://127.0.0.1:8002/import.html',
    importOnline: false,
  });
  const [engineOfflineBanner, setEngineOfflineBanner] = useState<boolean>(false);
  const [customCards, setCustomCards] = useState<WalletCard[]>([]);
  const [sessionTickets, setSessionTickets] = useState<WalletCard[]>([]);
  const [sessionLoans, setSessionLoans] = useState<WalletCard[]>([]);
  const [liveAccounts, setLiveAccounts] = useState<CustomerAssetAccount[]>([]);
  const [creditLimits, setCreditLimits] = useState<CustomerCreditLimit[]>([]);
  const [assetsSynced, setAssetsSynced] = useState<boolean>(false);

  const activeCustomerRef = useRef<string>(customerId);
  const historyAbortRef = useRef<AbortController | null>(null);
  const assetsAbortRef = useRef<AbortController | null>(null);
  const sendAbortRef = useRef<AbortController | null>(null);
  const isSendingRef = useRef<boolean>(false);

  useEffect(() => {
    activeCustomerRef.current = customerId;
  }, [customerId]);

  const appendDiscoveredCards = useCallback(
    (
      tickets: Array<{ ticketNo: string; category: string }>,
      loans: Array<{ applicationNo: string; amount: string; status: string }>,
    ) => {
      if (tickets.length > 0) {
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
      }
      if (loans.length > 0) {
        setSessionLoans((prev) => {
          const next = [...prev];
          for (const loan of loans) {
            if (!next.some((item) => item.id === loan.applicationNo)) {
              next.push({
                type: 'loan_application',
                id: loan.applicationNo,
                title: '消费贷款申请',
                attributes: { amount: `${loan.amount} 元`, status: loan.status },
                questionPrompt: `请帮我查询贷款申请 ${loan.applicationNo} 的审批进度。`,
              });
            }
          }
          return next;
        });
      }
    },
    [],
  );

  const loadCustomerAssets = useCallback(async (targetCustomerId: string) => {
    if (assetsAbortRef.current) {
      assetsAbortRef.current.abort();
    }
    const controller = new AbortController();
    assetsAbortRef.current = controller;

    const assets = await fetchCustomerAssets(targetCustomerId, controller.signal);
    if (activeCustomerRef.current !== targetCustomerId || !assets) {
      return;
    }
    setLiveAccounts(assets.accounts ?? []);
    setCreditLimits(assets.credit_limits ?? []);
    setAssetsSynced(Boolean(assets.synced));
  }, []);

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
        const allDiscoveredLoans: Array<{ applicationNo: string; amount: string; status: string }> = [];
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
            const processed = processServerBotMessage(msg, itemId);
            if (processed) {
              if (processed.rawText) {
                currentTurnBotTexts.push(processed.rawText);
              }
              nextTimeline.push(processed.item);
              nextReceipts.push(...processed.receipts);
              allDiscoveredTickets.push(...processed.discoveredTickets);
              allDiscoveredLoans.push(...processed.discoveredLoans);
            }
          }
        });
        flushTurn();

        const serverWorkflow = mapServerWorkflowToState(data.workflow_state);
        setTimeline(nextTimeline);
        setReceipts(nextReceipts);
        setWorkflow(serverWorkflow ?? nextWorkflow);
        setQuickReplies(data.quick_replies ?? []);
        appendDiscoveredCards(allDiscoveredTickets, allDiscoveredLoans);
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
    [appendDiscoveredCards],
  );

  const runHealthChecks = useCallback(async () => {
    const [engOk, finOk, ragInfo] = await Promise.all([
      checkEngineHealth(),
      checkFinanceApiHealth(),
      fetchRagStatus(),
    ]);
    setEngineStatus(engOk ? 'online' : 'offline');
    setFinanceStatus(finOk ? 'online' : 'offline');
    if (ragInfo) {
      setRagStatus(ragInfo.query_online ? 'online' : 'offline');
      setRagEndpoints({
        chatUrl: ragInfo.chat_url,
        importUrl: ragInfo.import_url,
        importOnline: ragInfo.import_online,
      });
    } else {
      setRagStatus('offline');
    }
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
    void loadCustomerAssets(customerId);
  }, [customerId, loadCustomerAssets, loadHistory]);

  const switchCustomer = useCallback((nextId: string) => {
    const trimmed = nextId.trim();
    if (!trimmed || trimmed === activeCustomerRef.current) {
      return;
    }

    if (historyAbortRef.current) {
      historyAbortRef.current.abort();
    }
    if (assetsAbortRef.current) {
      assetsAbortRef.current.abort();
    }
    if (sendAbortRef.current) {
      sendAbortRef.current.abort();
      sendAbortRef.current = null;
    }

    isSendingRef.current = false;
    setIsSending(false);
    setStreamStageLabel(null);
    setTimeline([]);
    setReceipts([]);
    setSessionTickets([]);
    setSessionLoans([]);
    setLiveAccounts([]);
    setCreditLimits([]);
    setAssetsSynced(false);
    setQuickReplies([]);
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
    setSessionLoans([]);
    setQuickReplies([]);
    setStreamStageLabel(null);
    setWorkflow(createInitialWorkflowState());
  }, []);

  const appendBotMessages = useCallback(
    (
      botMessages: ChatMessage[],
      baseMsgId: string,
      streamingItemId: string,
      serverWorkflowState?: Parameters<typeof mapServerWorkflowToState>[0],
      nextQuickReplies?: QuickReplyOption[],
    ) => {
      const botTexts: string[] = [];
      const newItems: TimelineItem[] = [];
      const newReceipts: ReceiptData[] = [];
      const discoveredTickets: Array<{ ticketNo: string; category: string }> = [];
      const discoveredLoans: Array<{ applicationNo: string; amount: string; status: string }> = [];

      botMessages.forEach((msg, idx) => {
        const processed = processServerBotMessage(msg, `${baseMsgId}_bot_${idx}`);
        if (processed) {
          if (processed.rawText) {
            botTexts.push(processed.rawText);
          }
          newItems.push(processed.item);
          newReceipts.push(...processed.receipts);
          discoveredTickets.push(...processed.discoveredTickets);
          discoveredLoans.push(...processed.discoveredLoans);
        }
      });

      setTimeline((prev) => [
        ...prev.filter((item) => item.id !== streamingItemId),
        ...newItems,
      ]);
      if (newReceipts.length > 0) {
        setReceipts((prev) => [...prev, ...newReceipts]);
      }
      appendDiscoveredCards(discoveredTickets, discoveredLoans);

      const mappedServer = mapServerWorkflowToState(serverWorkflowState);
      if (mappedServer) {
        setWorkflow(mappedServer);
      } else {
        setWorkflow((prev) => applyTurnTextsToWorkflow(prev, botTexts));
      }
      setQuickReplies(nextQuickReplies ?? []);

      return newReceipts.some(
        (rcpt) =>
          rcpt.kind === 'loan' ||
          rcpt.kind === 'card_loss' ||
          rcpt.kind === 'loan_repayment',
      );
    },
    [appendDiscoveredCards],
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
      const streamingItemId = `${newMsgId}_stream`;

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
      setQuickReplies([]);
      setStreamStageLabel('正在建立安全会话...');

      let accumulatedDelta = '';

      try {
        const request = options.object
          ? buildObjectRequest(targetCustomerId, options.object, newMsgId)
          : buildTextRequest(targetCustomerId, (options.text ?? '').trim(), newMsgId);

        const response = await sendChatStream(
          request,
          {
            onStage: (_stage, label) => {
              if (activeCustomerRef.current === targetCustomerId) {
                setStreamStageLabel(label || null);
              }
            },
            onDelta: (chunk) => {
              if (activeCustomerRef.current !== targetCustomerId) {
                return;
              }
              accumulatedDelta += chunk;
              setTimeline((prev) => {
                const exists = prev.some((item) => item.id === streamingItemId);
                if (exists) {
                  return prev.map((item) =>
                    item.id === streamingItemId && item.kind === 'bot'
                      ? { ...item, text: accumulatedDelta }
                      : item,
                  );
                }
                return [
                  ...prev,
                  {
                    id: streamingItemId,
                    kind: 'bot',
                    text: accumulatedDelta,
                    receipts: [],
                    streaming: true,
                  },
                ];
              });
            },
          },
          controller.signal,
        );

        // 切换客户后丢弃旧客户的迟到响应
        if (activeCustomerRef.current !== targetCustomerId) {
          return false;
        }

        setEngineStatus('online');
        setEngineOfflineBanner(false);
        const shouldRefreshAssets = appendBotMessages(
          response.messages,
          newMsgId,
          streamingItemId,
          response.workflow_state,
          response.quick_replies,
        );
        if (shouldRefreshAssets) {
          void loadCustomerAssets(targetCustomerId);
        }
        return true;
      } catch (err) {
        if (activeCustomerRef.current !== targetCustomerId) {
          return false;
        }
        setTimeline((prev) =>
          prev
            .filter((item) => item.id !== streamingItemId)
            .map((item) =>
              item.id === itemId && item.kind === 'user'
                ? { ...item, status: 'failed' }
                : item,
            ),
        );
        if (err instanceof DOMException && err.name === 'AbortError') {
          return false;
        }
        if (err instanceof EngineOfflineError) {
          setEngineStatus('offline');
          setEngineOfflineBanner(true);
        }
        return false;
      } finally {
        if (sendAbortRef.current === controller) {
          sendAbortRef.current = null;
        }
        if (activeCustomerRef.current === targetCustomerId) {
          isSendingRef.current = false;
          setIsSending(false);
          setStreamStageLabel(null);
        }
      }
    },
    [appendBotMessages, loadCustomerAssets],
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
    () =>
      buildWalletForCustomer(
        customerId,
        liveAccounts,
        customCards,
        sessionTickets,
        sessionLoans,
      ),
    [customerId, liveAccounts, customCards, sessionTickets, sessionLoans],
  );

  const awaitingSlot = workflow.active?.awaitingSlot ?? null;

  const awaitingAccountQuestion = useMemo(() => {
    if (awaitingSlot === 'account_no' || awaitingSlot === 'card_no') {
      return workflow.active?.awaitingQuestion ?? '请提供银行卡号或账户号';
    }
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
  }, [awaitingSlot, timeline, workflow.active]);

  return {
    customerId,
    timeline,
    receipts,
    workflow,
    quickReplies,
    streamStageLabel,
    walletCards,
    creditLimits,
    assetsSynced,
    awaitingSlot,
    awaitingAccountQuestion,
    isLoadingHistory,
    isSending,
    engineStatus,
    financeStatus,
    ragStatus,
    ragEndpoints,
    engineOfflineBanner,
    switchCustomer,
    refreshHistory: () => {
      void loadHistory(customerId);
      return loadCustomerAssets(customerId);
    },
    reconnectEngine: runHealthChecks,
    clearLocalView,
    sendText,
    sendObject,
    retryFailedMessage,
    addCustomCard,
  };
}
