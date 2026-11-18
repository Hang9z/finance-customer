import React, { useState } from 'react';
import { Check, Copy } from 'lucide-react';
import { formatCardNoDisplay } from '../../lib/receipts';
import { ReceiptData } from '../../types/chat';
import { Seal } from '../Seal';

interface ReceiptCardProps {
  receipt: ReceiptData;
  sealTone?: 'seal' | 'ink';
}

const CopyCodeButton: React.FC<{ value: string; strike?: boolean }> = ({
  value,
  strike = false,
}) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    void navigator.clipboard?.writeText(value);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1400);
  };

  return (
    <button
      type="button"
      onClick={handleCopy}
      className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded bg-paper border border-hairline tabular-mono text-[12px] text-ink hover:border-ink transition-colors"
      title="点击复制"
      aria-label={`复制 ${value}`}
    >
      <span className={strike ? 'line-through text-ink-2' : ''}>{value}</span>
      {copied ? (
        <Check className="w-3 h-3 text-celadon" />
      ) : (
        <Copy className="w-3 h-3 text-mist" />
      )}
    </button>
  );
};

export const ReceiptCard: React.FC<ReceiptCardProps> = ({
  receipt,
  sealTone = 'seal',
}) => {
  return (
    <div className="relative bg-surface border border-hairline rounded-[10px] shadow-ledger overflow-hidden animate-message-enter">
      {/* 顶部微标签行 */}
      <div className="px-4 pt-3 pb-2 border-b border-hairline flex items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="micro-label text-ink-2 font-medium">
            RECEIPT · {receipt.title}
          </span>
        </div>
        <span className="tabular-mono text-[11px] text-mist">{receipt.createdAt}</span>
      </div>

      {/* 主体内容 */}
      <div className="relative px-4 py-4 pr-20">
        {receipt.kind === 'balance' ? (
          <div className="space-y-3">
            <div>
              <div className="text-[11px] text-ink-2">可用余额</div>
              <div className="tabular-mono text-[32px] leading-tight font-semibold text-ink mt-0.5">
                {receipt.availableBalance}{' '}
                <span className="text-[14px] font-normal text-ink-2">
                  {receipt.currency}
                </span>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-x-4 gap-y-2 text-[12px] pt-1">
              <div>
                <span className="text-ink-2 block text-[11px]">银行账户</span>
                <span className="tabular-mono text-ink">
                  {formatCardNoDisplay(receipt.accountNo)}
                </span>
              </div>
              <div>
                <span className="text-ink-2 block text-[11px]">冻结金额 / 状态</span>
                <span className="tabular-mono text-ink">
                  {receipt.frozenAmount} {receipt.currency} · {receipt.accountStatus}
                </span>
              </div>
            </div>
          </div>
        ) : null}

        {receipt.kind === 'transactions' ? (
          <div className="space-y-2.5 pr-0 -mr-16">
            <div className="flex items-center justify-between text-[12px] text-ink-2">
              <span>
                账户{' '}
                <span className="tabular-mono text-ink">
                  {formatCardNoDisplay(receipt.accountNo)}
                </span>
              </span>
              <span className="tabular-mono text-[11px]">
                共 {receipt.totalCount} 笔 · 展示最近 {receipt.rows.length} 笔
              </span>
            </div>
            <div className="overflow-x-auto border border-hairline rounded">
              <table className="w-full text-left border-collapse text-[12px]">
                <thead>
                  <tr className="bg-paper border-b border-hairline text-ink-2 text-[11px]">
                    <th className="py-1.5 px-2.5 font-medium">时间</th>
                    <th className="py-1.5 px-2.5 font-medium">摘要</th>
                    <th className="py-1.5 px-2.5 font-medium">对象</th>
                    <th className="py-1.5 px-2.5 font-medium text-right">金额</th>
                  </tr>
                </thead>
                <tbody>
                  {receipt.rows.map((row, idx) => (
                    <tr
                      key={`${row.time}_${idx}`}
                      className="border-b border-hairline last:border-b-0"
                    >
                      <td className="py-1.5 px-2.5 tabular-mono text-[11px] text-ink-2 whitespace-nowrap">
                        {row.time}
                      </td>
                      <td className="py-1.5 px-2.5 text-ink whitespace-nowrap">
                        {row.typeLabel}
                      </td>
                      <td className="py-1.5 px-2.5 text-ink-2 max-w-[120px] truncate">
                        {row.counterparty}
                      </td>
                      <td
                        className={`py-1.5 px-2.5 tabular-mono text-right font-medium whitespace-nowrap ${
                          row.isCredit ? 'text-celadon' : 'text-ink'
                        }`}
                      >
                        {row.isCredit ? '+' : '−'}
                        {row.amount} {row.currency}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        ) : null}

        {receipt.kind === 'loan' ? (
          <div className="space-y-3">
            <div>
              <div className="text-[11px] text-ink-2">申请金额 / 期限</div>
              <div className="tabular-mono text-[24px] leading-tight font-semibold text-ink mt-0.5">
                {receipt.amount}{' '}
                <span className="text-[14px] font-normal text-ink-2">
                  元 · {receipt.termMonths} 期
                </span>
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-3 text-[12px]">
              <div>
                <span className="text-ink-2 mr-1.5">申请编号</span>
                <CopyCodeButton value={receipt.applicationNo} />
              </div>
              <div>
                <span className="text-ink-2 mr-1">状态</span>
                <span className="tabular-mono text-celadon font-medium">
                  {receipt.status}
                </span>
              </div>
            </div>
          </div>
        ) : null}

        {receipt.kind === 'ticket' ? (
          <div className="space-y-2.5">
            <div className="text-[16px] font-serif font-semibold text-ink">
              {receipt.category}
            </div>
            <div className="flex items-center gap-2 text-[12px]">
              <span className="text-ink-2">工单编号</span>
              <CopyCodeButton value={receipt.ticketNo} />
            </div>
          </div>
        ) : null}

        {receipt.kind === 'card_loss' ? (
          <div className="space-y-2.5">
            <div className="text-[12px] text-ink-2">已办理止付挂失卡片 / 账户</div>
            <div className="flex flex-wrap items-center gap-2.5">
              <CopyCodeButton value={receipt.cardNo} strike />
              <span className="tabular-mono text-[12px] text-ink-2">
                状态：{receipt.status}
              </span>
            </div>
          </div>
        ) : null}

        {/* 右上角电子印章 */}
        <Seal
          text={receipt.sealText}
          tone={sealTone}
          className="absolute right-3 top-2"
        />
      </div>

      {/* 底部虚线撕边 */}
      <div className="mx-3 border-t border-dashed border-hairline py-1.5 flex items-center justify-between text-[11px] text-mist">
        <span>中州银行智能柜台电子凭证</span>
        <span className="tabular-mono">LEDGER</span>
      </div>
    </div>
  );
};
