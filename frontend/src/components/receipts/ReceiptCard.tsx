import React, { useState } from 'react';
import { Check, CheckCircle2, Copy, Star } from 'lucide-react';
import { formatCardNoDisplay } from '../../lib/receipts';
import { submitCustomerTicketFeedback } from '../../services/api';
import { ReceiptData } from '../../types/chat';
import { Seal } from '../Seal';

interface ReceiptCardProps {
  receipt: ReceiptData;
  sealTone?: 'seal' | 'ink';
  customerId?: string;
}

const TicketProgressBody: React.FC<{
  receipt: Extract<ReceiptData, { kind: 'ticket_progress' }>;
  customerId?: string;
}> = ({ receipt, customerId }) => {
  const [score, setScore] = useState(5);
  const [note, setNote] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [submittedText, setSubmittedText] = useState<string | null>(null);
  const [errorText, setErrorText] = useState<string | null>(null);

  const canEvaluate =
    Boolean(customerId) &&
    (receipt.status.includes('解决') ||
      receipt.status.includes('完结') ||
      receipt.status.includes('处理中'));

  const handleConfirmFeedback = async () => {
    if (!customerId || !receipt.ticketNo) {
      return;
    }
    setSubmitting(true);
    setErrorText(null);
    try {
      await submitCustomerTicketFeedback(receipt.ticketNo, {
        customer_no: customerId,
        confirm_status: 'confirmed',
        satisfaction_score: score,
        feedback_content: note.trim() || '客户已确认处理结果',
      });
      setSubmittedText(`已确认结果并提交 ${score} 星评价`);
    } catch (err) {
      setErrorText(err instanceof Error ? err.message : '提交评价失败，请稍后重试');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-2.5">
      <div className="flex items-baseline justify-between gap-2">
        <span className="text-[16px] font-serif font-semibold text-ink">
          {receipt.category}
        </span>
        <span className="text-[13px] font-medium text-celadon">
          {receipt.status}
        </span>
      </div>
      <div className="flex flex-wrap items-center gap-3 text-[12px]">
        <div>
          <span className="text-ink-2 mr-1.5">工单编号</span>
          <CopyCodeButton value={receipt.ticketNo} />
        </div>
        <span className="text-[11px] text-ink-2">
          专席：{receipt.handlerName}
        </span>
        {receipt.handledAt ? (
          <span className="tabular-mono text-[11px] text-mist">
            处理：{receipt.handledAt}
          </span>
        ) : null}
      </div>
      {receipt.processResult ? (
        <div className="rounded-[8px] border border-hairline bg-paper px-3 py-2 text-[12px] text-ink leading-relaxed">
          <div className="text-[11px] text-ink-2 mb-0.5 font-medium">专席处理反馈</div>
          <div className="whitespace-pre-wrap break-words">{receipt.processResult}</div>
        </div>
      ) : null}
      {canEvaluate ? (
        <div className="pt-1 border-t border-hairline/70 space-y-2">
          {submittedText ? (
            <div className="inline-flex items-center gap-1.5 text-[11px] text-celadon font-medium">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>{submittedText}</span>
            </div>
          ) : (
            <div className="space-y-1.5">
              <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="inline-flex items-center gap-1 text-[11px] text-ink-2">
                  <span>满意度：</span>
                  {[1, 2, 3, 4, 5].map((starVal) => (
                    <button
                      key={starVal}
                      type="button"
                      onClick={() => setScore(starVal)}
                      className="p-0.5 hover:scale-110 transition-transform"
                      title={`${starVal} 星`}
                    >
                      <Star
                        className={`w-3.5 h-3.5 ${
                          starVal <= score ? 'text-amber fill-amber' : 'text-mist'
                        }`}
                      />
                    </button>
                  ))}
                </div>
                <button
                  type="button"
                  disabled={submitting}
                  onClick={() => void handleConfirmFeedback()}
                  className="px-2.5 py-1 rounded-[6px] bg-celadon text-white text-[11px] font-medium hover:opacity-90 disabled:opacity-50 transition-opacity"
                >
                  {submitting ? '提交中...' : '确认处理结果'}
                </button>
              </div>
              <input
                type="text"
                value={note}
                onChange={(e) => setNote(e.target.value)}
                placeholder="可选：填写补充评价或回访意见..."
                className="w-full px-2.5 py-1 rounded-[6px] border border-hairline bg-paper text-[11px] text-ink placeholder:text-mist focus:outline-none focus:border-ink"
              />
              {errorText ? (
                <div className="text-[11px] text-seal">{errorText}</div>
              ) : null}
            </div>
          )}
        </div>
      ) : null}
    </div>
  );
};

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
  customerId,
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

        {receipt.kind === 'loan_progress' ? (
          <div className="space-y-3">
            <div>
              <div className="text-[11px] text-ink-2">审批状态 / 申请额度</div>
              <div className="flex items-baseline gap-2.5 mt-0.5">
                <span className="text-[20px] font-serif font-semibold text-ink">
                  {receipt.status}
                </span>
                <span className="tabular-mono text-[13px] text-ink-2">
                  {receipt.amount} 元 · {receipt.termMonths} 期
                </span>
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-3 text-[12px]">
              <div>
                <span className="text-ink-2 mr-1.5">申请编号</span>
                <CopyCodeButton value={receipt.applicationNo} />
              </div>
              <span className="tabular-mono text-[11px] text-ink-2">
                提交：{receipt.submittedAt}
              </span>
            </div>
          </div>
        ) : null}

        {receipt.kind === 'ticket_progress' ? (
          <TicketProgressBody receipt={receipt} customerId={customerId} />
        ) : null}

        {receipt.kind === 'credit_limit' ? (
          <div className="space-y-2.5">
            <div className="text-[11px] text-ink-2">客户可用授信额度</div>
            {receipt.items.map((item) => (
              <div
                key={item.limitNo}
                className="flex items-center justify-between gap-2 border border-hairline rounded px-2.5 py-2 bg-paper text-[12px]"
              >
                <div className="min-w-0">
                  <div className="tabular-mono font-medium text-ink truncate">
                    {item.productCode}
                  </div>
                  <div className="text-[11px] text-ink-2 tabular-mono">
                    {item.limitNo} · 至 {item.validTo}
                  </div>
                </div>
                <div className="text-right shrink-0 tabular-mono">
                  <div className="font-semibold text-ink">
                    可用 {item.availableAmount} 元
                  </div>
                  <div className="text-[11px] text-ink-2">
                    总额 {item.totalAmount} 元
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : null}

        {receipt.kind === 'repayment_plan' ? (
          <div className="space-y-2.5">
            <div className="flex items-center justify-between text-[12px]">
              <span className="text-ink font-medium">{receipt.scopeLabel}</span>
              <span
                className={`text-[11px] tabular-mono ${
                  receipt.overdueCount > 0 ? 'text-seal font-medium' : 'text-celadon'
                }`}
              >
                {receipt.overdueCount > 0
                  ? `存在 ${receipt.overdueCount} 笔逾期`
                  : '无逾期记录'}
              </span>
            </div>
            {receipt.bills.length > 0 ? (
              <div className="space-y-1.5">
                {receipt.bills.slice(0, 4).map((bill) => (
                  <div
                    key={bill.billNo}
                    className="flex items-center justify-between gap-2 bg-paper border border-hairline rounded px-2.5 py-1.5 text-[12px]"
                  >
                    <CopyCodeButton value={bill.billNo} />
                    <span className="tabular-mono text-ink">
                      待还 {bill.outstandingAmount} 元 · {bill.status}
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-[12px] text-ink-2">当前暂无待还账单</div>
            )}
          </div>
        ) : null}

        {receipt.kind === 'loan_repayment' ? (
          <div className="space-y-3">
            <div>
              <div className="text-[11px] text-ink-2">本次还款金额</div>
              <div className="tabular-mono text-[24px] leading-tight font-semibold text-ink mt-0.5">
                {receipt.amount}{' '}
                <span className="text-[14px] font-normal text-ink-2">元</span>
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-3 text-[12px]">
              <div>
                <span className="text-ink-2 mr-1.5">还款流水</span>
                <CopyCodeButton value={receipt.repaymentNo} />
              </div>
              <div>
                <span className="text-ink-2 mr-1.5">账单号</span>
                <CopyCodeButton value={receipt.billNo} />
              </div>
              <span className="tabular-mono text-ink-2">
                扣款：{receipt.accountNo}
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
