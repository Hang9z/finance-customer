import React, { useEffect, useRef } from 'react';
import { CreditCard, SendHorizontal } from 'lucide-react';
import { WorkflowState } from '../../types/chat';

interface ComposerProps {
  value: string;
  onChange: (next: string) => void;
  onSend: (text: string) => void;
  onOpenWallet: () => void;
  workflow: WorkflowState;
  isSending: boolean;
  inputRef: React.RefObject<HTMLTextAreaElement>;
}

export const Composer: React.FC<ComposerProps> = ({
  value,
  onChange,
  onSend,
  onOpenWallet,
  workflow,
  isSending,
  inputRef,
}) => {
  const localRef = useRef<HTMLTextAreaElement | null>(null);
  const resolvedRef = inputRef ?? localRef;

  useEffect(() => {
    const el = resolvedRef.current;
    if (!el) {
      return;
    }
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [value, resolvedRef]);

  const handleSubmit = () => {
    const trimmed = value.trim();
    if (!trimmed || isSending) {
      return;
    }
    onChange('');
    onSend(trimmed);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const quickActions = [
    { label: '继续刚才的贷款', text: '继续刚才的贷款' },
    { label: '取消当前任务', text: '取消当前任务' },
    { label: '转人工客服', text: '转人工客服' },
    ...workflow.paused.map((flowName) => ({
      label: `恢复「${flowName}」`,
      text: `继续${flowName}`,
    })),
  ];

  return (
    <div className="bg-paper border-t border-hairline px-4 md:px-8 pt-2.5 pb-3 shrink-0">
      <div className="max-w-[720px] mx-auto space-y-2">
        {/* 轻量文字快捷动作 */}
        <div className="flex items-center flex-wrap gap-x-4 gap-y-1 text-[12px]">
          {quickActions.map((act) => (
            <button
              key={act.label}
              type="button"
              disabled={isSending}
              onClick={() => onSend(act.text)}
              className="text-ink-2 hover:text-ink hover:underline underline-offset-4 transition-colors disabled:opacity-50"
            >
              {act.label}
            </button>
          ))}
        </div>

        {/* 主输入盒 */}
        <div className="bg-surface border border-hairline rounded-[10px] p-2 flex items-end gap-2 focus-within:border-ink transition-colors">
          <button
            type="button"
            onClick={onOpenWallet}
            aria-label="打开卡包"
            title="打开卡包"
            className="shrink-0 inline-flex items-center gap-1.5 px-2.5 py-2 rounded-[6px] text-[12px] text-ink-2 hover:text-ink hover:bg-paper transition-colors"
          >
            <CreditCard className="w-4 h-4" />
            <span>卡包</span>
          </button>

          <textarea
            ref={resolvedRef}
            rows={1}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="请输入您要办理的金融业务或咨询问题……"
            aria-label="对话输入框"
            className="flex-1 resize-none bg-transparent text-[14px] leading-[1.7] text-ink placeholder:text-mist py-1.5 px-1 max-h-[160px] focus:outline-none"
          />

          <button
            type="button"
            disabled={isSending || !value.trim()}
            onClick={handleSubmit}
            aria-label="发送消息"
            title="发送"
            className="shrink-0 inline-flex items-center justify-center px-3 py-2 rounded-[6px] bg-ink text-white text-[12px] font-medium hover:opacity-90 transition-opacity disabled:bg-mist disabled:cursor-not-allowed"
          >
            <SendHorizontal className="w-4 h-4" />
          </button>
        </div>

        <div className="text-[11px] text-mist">
          Enter 发送 · Shift+Enter 换行 · 卡片以 object 消息发送
        </div>
      </div>
    </div>
  );
};
