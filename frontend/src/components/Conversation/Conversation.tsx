import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  AlertCircle,
  ArrowDown,
  ArrowRightLeft,
  CheckCircle2,
  Play,
  RotateCcw,
  XCircle,
} from 'lucide-react';
import { OBJECT_SLOT_MAP } from '../../constants/presets';
import { TaskEventInfo, TimelineItem, WalletCard } from '../../types/chat';
import { PhysicalCardPreview } from '../cards/PhysicalCardPreview';
import { ReceiptCard } from '../receipts/ReceiptCard';
import { EmptyState } from './EmptyState';
import { InlineMarkdown } from './InlineMarkdown';

const THINKING_PHASES = ['理解意图', '推进流程', '查询中台'];

interface ConversationProps {
  timeline: TimelineItem[];
  isLoadingHistory: boolean;
  isSending: boolean;
  engineOfflineBanner: boolean;
  onReconnect: () => void;
  onSelectPrompt: (prompt: string) => void;
  onRetryMessage: (timelineId: string) => void;
}

const TaskEventDivider: React.FC<{ event: TaskEventInfo }> = ({ event }) => {
  let colorClass = 'text-ink';
  let Icon = Play;
  let label = `开始办理 · ${event.flow}`;

  if (event.kind === 'switch') {
    colorClass = 'text-amber';
    Icon = ArrowRightLeft;
    label = `${event.previousFlow ?? '当前业务'} 已暂停 ⟶ 插队办理 ${event.flow}`;
  } else if (event.kind === 'resume') {
    colorClass = 'text-celadon';
    Icon = CheckCircle2;
    label = `恢复办理 · ${event.flow}`;
  } else if (event.kind === 'cancel') {
    colorClass = 'text-mist';
    Icon = XCircle;
    label = `已撤销 · ${event.flow}`;
  }

  return (
    <div className="my-4 flex items-center gap-3 animate-message-enter">
      <div className="flex-1 h-px bg-hairline" />
      <div className={`inline-flex items-center gap-1.5 text-[12px] font-medium ${colorClass}`}>
        <Icon className="w-3.5 h-3.5 shrink-0" />
        <span>{label}</span>
      </div>
      <div className="flex-1 h-px bg-hairline" />
    </div>
  );
};

export const Conversation: React.FC<ConversationProps> = ({
  timeline,
  isLoadingHistory,
  isSending,
  engineOfflineBanner,
  onReconnect,
  onSelectPrompt,
  onRetryMessage,
}) => {
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const isNearBottomRef = useRef<boolean>(true);
  const prevCountRef = useRef<number>(0);
  const [hasUnreadBelow, setHasUnreadBelow] = useState<boolean>(false);
  const [thinkingIdx, setThinkingIdx] = useState<number>(0);

  useEffect(() => {
    if (!isSending) {
      setThinkingIdx(0);
      return;
    }
    const timer = window.setInterval(() => {
      setThinkingIdx((prev) => (prev + 1) % THINKING_PHASES.length);
    }, 1200);
    return () => window.clearInterval(timer);
  }, [isSending]);

  const scrollToBottom = (behavior: ScrollBehavior = 'smooth') => {
    const el = scrollRef.current;
    if (!el) {
      return;
    }
    el.scrollTo({ top: el.scrollHeight, behavior });
    setHasUnreadBelow(false);
    isNearBottomRef.current = true;
  };

  useEffect(() => {
    const totalItems = timeline.length + (isSending ? 1 : 0);
    if (totalItems > prevCountRef.current) {
      if (isNearBottomRef.current) {
        scrollToBottom('smooth');
      } else {
        setHasUnreadBelow(true);
      }
    }
    prevCountRef.current = totalItems;
  }, [timeline.length, isSending]);

  const handleScroll = () => {
    const el = scrollRef.current;
    if (!el) {
      return;
    }
    const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
    isNearBottomRef.current = nearBottom;
    if (nearBottom) {
      setHasUnreadBelow(false);
    }
  };

  // 找到对话流中最后一张电子凭证，只有最后一张盖朱砂印章（控制全屏朱砂色数量）
  const latestReceiptId = useMemo(() => {
    for (let i = timeline.length - 1; i >= 0; i -= 1) {
      const item = timeline[i];
      if (item.kind === 'bot' && item.receipts.length > 0) {
        return item.receipts[item.receipts.length - 1].id;
      }
    }
    return null;
  }, [timeline]);

  return (
    <div className="relative flex-1 min-h-0 flex flex-col">
      {engineOfflineBanner ? (
        <div className="bg-surface border-b border-seal/50 px-4 py-2 flex items-center justify-between gap-3 text-[12px]">
          <div className="flex items-center gap-2 text-seal min-w-0">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span className="truncate">
              无法连接智能客服引擎（127.0.0.1:18082）。请在后端目录执行{' '}
              <code className="tabular-mono px-1 py-0.5 bg-paper border border-hairline rounded text-ink">
                .\.venv\Scripts\python main.py
              </code>
            </span>
          </div>
          <button
            type="button"
            onClick={onReconnect}
            className="shrink-0 px-2.5 py-1 border border-hairline rounded text-ink hover:border-ink transition-colors"
          >
            重新连接
          </button>
        </div>
      ) : null}

      <div
        ref={scrollRef}
        onScroll={handleScroll}
        className="flex-1 overflow-y-auto px-4 md:px-8 py-6"
      >
        <div className="max-w-[720px] mx-auto space-y-4">
          {isLoadingHistory ? (
            <div className="space-y-4 py-4" aria-label="历史加载中">
              <div className="h-10 w-2/3 rounded-[10px] skeleton-shimmer" />
              <div className="h-14 w-3/4 ml-auto rounded-[10px] skeleton-shimmer" />
              <div className="h-20 w-4/5 rounded-[10px] skeleton-shimmer" />
              <div className="h-12 w-1/2 ml-auto rounded-[10px] skeleton-shimmer" />
            </div>
          ) : timeline.length === 0 && !isSending ? (
            <EmptyState disabled={isSending} onSelectPrompt={onSelectPrompt} />
          ) : (
            timeline.map((item) => {
              if (item.kind === 'event') {
                return <TaskEventDivider key={item.id} event={item.event} />;
              }

              if (item.kind === 'user') {
                if (item.object) {
                  const obj = item.object;
                  const slotTarget = OBJECT_SLOT_MAP[obj.type] ?? 'slot';
                  const attrStrings: Record<string, string> = {};
                  if (obj.attributes) {
                    for (const [k, v] of Object.entries(obj.attributes)) {
                      attrStrings[k] = String(v);
                    }
                  }
                  const cardModel: WalletCard = {
                    type: obj.type,
                    id: obj.id,
                    title: obj.title ?? obj.id,
                    attributes: attrStrings,
                    questionPrompt: '',
                  };

                  return (
                    <div
                      key={item.id}
                      className="flex flex-col items-end gap-1 animate-message-enter"
                    >
                      <span className="text-[11px] text-ink-2 tabular-mono">
                        业务卡片 · 自动填槽 → {slotTarget}
                      </span>
                      <PhysicalCardPreview card={cardModel} compact />
                      {item.status === 'failed' ? (
                        <button
                          type="button"
                          onClick={() => onRetryMessage(item.id)}
                          className="inline-flex items-center gap-1 text-[11px] text-seal hover:underline mt-0.5"
                        >
                          <RotateCcw className="w-3 h-3" />
                          <span>发送失败 · 重试</span>
                        </button>
                      ) : null}
                    </div>
                  );
                }

                return (
                  <div
                    key={item.id}
                    className="flex flex-col items-end gap-1 animate-message-enter"
                  >
                    <div className="max-w-[82%] bg-ink text-white px-4 py-2.5 rounded-[14px] rounded-br-[4px] text-[14px] leading-[1.7] whitespace-pre-wrap break-words">
                      {item.text}
                    </div>
                    {item.status === 'failed' ? (
                      <button
                        type="button"
                        onClick={() => onRetryMessage(item.id)}
                        className="inline-flex items-center gap-1 text-[11px] text-seal hover:underline"
                      >
                        <RotateCcw className="w-3 h-3" />
                        <span>发送失败 · 重试</span>
                      </button>
                    ) : null}
                  </div>
                );
              }

              // Bot 消息 + 可选凭证
              return (
                <div
                  key={item.id}
                  className="flex flex-col items-start gap-2.5 animate-message-enter"
                >
                  {item.text ? (
                    <div className="max-w-[88%] bg-surface border border-hairline rounded-[14px] rounded-bl-[4px] px-4 py-3">
                      <InlineMarkdown content={item.text} />
                    </div>
                  ) : null}

                  {item.receipts.map((receipt) => (
                    <div key={receipt.id} className="w-full max-w-[540px]">
                      <ReceiptCard
                        receipt={receipt}
                        sealTone={receipt.id === latestReceiptId ? 'seal' : 'ink'}
                      />
                    </div>
                  ))}
                </div>
              );
            })
          )}

          {isSending ? (
            <div className="flex items-center gap-3 py-2 animate-message-enter">
              <div className="bg-surface border border-hairline rounded-[14px] rounded-bl-[4px] px-4 py-2.5 inline-flex items-center gap-3">
                <div className="flex items-center gap-1" aria-hidden="true">
                  <span className="w-1.5 h-1.5 rounded-full bg-ink thinking-dot-1" />
                  <span className="w-1.5 h-1.5 rounded-full bg-ink thinking-dot-2" />
                  <span className="w-1.5 h-1.5 rounded-full bg-ink thinking-dot-3" />
                </div>
                <span className="text-[12px] text-ink-2">
                  {THINKING_PHASES[thinkingIdx]}
                </span>
              </div>
            </div>
          ) : null}
        </div>
      </div>

      {hasUnreadBelow ? (
        <div className="absolute bottom-4 left-1/2 -translate-x-1/2 z-10">
          <button
            type="button"
            onClick={() => scrollToBottom('smooth')}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-ink text-white text-[12px] shadow-ledger hover:opacity-90 transition-opacity"
          >
            <ArrowDown className="w-3.5 h-3.5" />
            <span>↓ 新消息</span>
          </button>
        </div>
      ) : null}
    </div>
  );
};
