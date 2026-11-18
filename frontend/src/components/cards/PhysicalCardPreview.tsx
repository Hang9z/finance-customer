import React from 'react';
import { formatCardNoDisplay } from '../../lib/receipts';
import { WalletCard } from '../../types/chat';

interface PhysicalCardPreviewProps {
  card: WalletCard;
  compact?: boolean;
  recommended?: boolean;
}

export const PhysicalCardPreview: React.FC<PhysicalCardPreviewProps> = ({
  card,
  compact = false,
  recommended = false,
}) => {
  const formattedId = formatCardNoDisplay(card.id);

  if (card.type === 'account') {
    const balance = card.attributes.balance ?? '';
    return (
      <div
        className={`relative w-full aspect-[1.586/1] rounded-[10px] bg-ink text-white flex flex-col justify-between border ${
          recommended ? 'border-seal' : 'border-ink'
        } ${compact ? 'p-3 max-w-[230px]' : 'p-4'}`}
      >
        <div className="flex items-start justify-between gap-2">
          {/* 细线金属芯片 */}
          <svg
            width={compact ? 24 : 28}
            height={compact ? 18 : 20}
            viewBox="0 0 28 20"
            fill="none"
            aria-hidden="true"
          >
            <rect
              x="0.75"
              y="0.75"
              width="26.5"
              height="18.5"
              rx="3"
              stroke="#9AA0A8"
              strokeWidth="1"
            />
            <line x1="9" y1="1" x2="9" y2="19" stroke="#9AA0A8" strokeWidth="0.75" />
            <line x1="19" y1="1" x2="19" y2="19" stroke="#9AA0A8" strokeWidth="0.75" />
            <line x1="1" y1="10" x2="27" y2="10" stroke="#9AA0A8" strokeWidth="0.75" />
          </svg>
          <span className="micro-label text-mist">ACCOUNT</span>
        </div>

        <div className="space-y-1">
          <div className="text-[11px] text-mist truncate">{card.title}</div>
          <div
            className={`tabular-mono tracking-wider text-paper ${
              compact ? 'text-[12px]' : 'text-[14px]'
            }`}
          >
            {formattedId}
          </div>
        </div>

        <div className="flex items-end justify-between text-[11px]">
          <span className="text-mist">{card.attributes.status ?? '正常'}</span>
          {balance ? (
            <span className="tabular-mono text-white font-medium">{balance}</span>
          ) : null}
        </div>
      </div>
    );
  }

  if (card.type === 'card') {
    const balance = card.attributes.balance ?? '';
    return (
      <div
        className={`relative w-full aspect-[1.586/1] rounded-[10px] bg-paper text-ink flex flex-col justify-between border ${
          recommended ? 'border-seal' : 'border-seal/70'
        } ${compact ? 'p-3 max-w-[230px]' : 'p-4'}`}
      >
        <div className="flex items-start justify-between gap-2">
          <svg
            width={compact ? 24 : 28}
            height={compact ? 18 : 20}
            viewBox="0 0 28 20"
            fill="none"
            aria-hidden="true"
          >
            <rect
              x="0.75"
              y="0.75"
              width="26.5"
              height="18.5"
              rx="3"
              stroke="#5B616B"
              strokeWidth="1"
            />
            <line x1="9" y1="1" x2="9" y2="19" stroke="#5B616B" strokeWidth="0.75" />
            <line x1="19" y1="1" x2="19" y2="19" stroke="#5B616B" strokeWidth="0.75" />
            <line x1="1" y1="10" x2="27" y2="10" stroke="#5B616B" strokeWidth="0.75" />
          </svg>
          <span className="font-serif text-[12px] font-semibold text-seal">白金卡</span>
        </div>

        <div className="space-y-1">
          <div className="text-[11px] text-ink-2 truncate">{card.title}</div>
          <div
            className={`tabular-mono tracking-wider text-ink ${
              compact ? 'text-[12px]' : 'text-[14px]'
            }`}
          >
            {formattedId}
          </div>
        </div>

        <div className="flex items-end justify-between text-[11px]">
          <span className="text-ink-2">{card.attributes.status ?? '正常'}</span>
          {balance ? (
            <span className="tabular-mono text-ink font-medium">{balance}</span>
          ) : null}
        </div>
      </div>
    );
  }

  if (card.type === 'loan_product' || card.type === 'wealth_product') {
    const isLoan = card.type === 'loan_product';
    const riskLevel = card.attributes.riskLevel ?? '';
    const stripeClass = isLoan
      ? 'bg-ink'
      : riskLevel === 'R1'
        ? 'bg-celadon'
        : 'bg-amber';
    const mainMetric = isLoan
      ? card.attributes.rate ?? '—'
      : card.attributes.expectedYield ?? '—';
    const metricLabel = isLoan ? '年化利率' : '预期年化';

    return (
      <div
        className={`relative w-full rounded-[8px] bg-surface border border-hairline overflow-hidden flex ${
          compact ? 'max-w-[260px]' : ''
        }`}
      >
        <div className={`w-1 shrink-0 ${stripeClass}`} />
        <div className="flex-1 p-3 flex items-center justify-between gap-3">
          <div className="min-w-0 space-y-1">
            <div className="flex items-center gap-2">
              <span className="micro-label text-ink-2">
                {isLoan ? 'LOAN' : riskLevel || 'WEALTH'}
              </span>
              <span className="tabular-mono text-[11px] text-mist truncate">{card.id}</span>
            </div>
            <div className="text-[14px] font-medium text-ink truncate">{card.title}</div>
            <div className="flex flex-wrap gap-1.5 text-[11px] text-ink-2">
              {card.attributes.amountRange ? (
                <span className="px-1.5 py-0.5 bg-paper border border-hairline rounded">
                  额度 {card.attributes.amountRange}
                </span>
              ) : null}
              {card.attributes.termRange ? (
                <span className="px-1.5 py-0.5 bg-paper border border-hairline rounded">
                  {card.attributes.termRange}
                </span>
              ) : null}
              {card.attributes.redemption ? (
                <span className="px-1.5 py-0.5 bg-paper border border-hairline rounded">
                  赎回 {card.attributes.redemption}
                </span>
              ) : null}
              {card.attributes.term ? (
                <span className="px-1.5 py-0.5 bg-paper border border-hairline rounded">
                  期限 {card.attributes.term}
                </span>
              ) : null}
            </div>
          </div>

          <div className="text-right shrink-0">
            <div className="text-[11px] text-ink-2">{metricLabel}</div>
            <div className="tabular-mono text-[16px] font-semibold text-ink">
              {mainMetric}
            </div>
          </div>
        </div>
      </div>
    );
  }

  // transaction / ticket / fallback 票据样式（左侧打孔圆点装饰）
  const isTicket = card.type === 'ticket';
  return (
    <div
      className={`relative w-full rounded-[8px] bg-surface border border-hairline p-3 pl-5 ${
        compact ? 'max-w-[260px]' : ''
      }`}
    >
      {/* 左侧打孔圆点装饰 */}
      <div
        className="absolute left-1.5 top-2.5 bottom-2.5 flex flex-col justify-between"
        aria-hidden="true"
      >
        <span className="w-1.5 h-1.5 rounded-full bg-paper border border-hairline" />
        <span className="w-1.5 h-1.5 rounded-full bg-paper border border-hairline" />
        <span className="w-1.5 h-1.5 rounded-full bg-paper border border-hairline" />
      </div>

      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span className="micro-label text-ink-2">
              {isTicket ? 'TICKET' : 'TXN'}
            </span>
            <span className="tabular-mono text-[11px] text-mist truncate">{card.id}</span>
          </div>
          <div className="text-[14px] text-ink font-medium truncate mt-0.5">
            {card.title}
          </div>
        </div>
        {card.attributes.amount ? (
          <div className="tabular-mono text-[12px] font-medium text-ink shrink-0">
            {card.attributes.amount}
          </div>
        ) : null}
      </div>

      <div className="mt-1.5 flex items-center justify-between text-[11px] text-ink-2">
        <span>{card.attributes.category ?? card.attributes.time ?? '凭证记录'}</span>
        <span>{card.attributes.status ?? ''}</span>
      </div>
    </div>
  );
};
