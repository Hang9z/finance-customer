import React, { useState } from 'react';
import { ChevronDown, ChevronUp, Plus, RefreshCw, Send } from 'lucide-react';
import {
  ChatObject,
  CustomerCreditLimit,
  ObjectCardType,
  WalletCard,
} from '../../types/chat';
import { PhysicalCardPreview } from '../cards/PhysicalCardPreview';

interface CardWalletProps {
  cards: WalletCard[];
  creditLimits: CustomerCreditLimit[];
  assetsSynced: boolean;
  awaitingSlot: string | null;
  awaitingAccountQuestion: string | null;
  isSending: boolean;
  onSubmitCard: (obj: ChatObject) => void;
  onAskAboutCard: (prompt: string) => void;
  onAddCustomCard: (card: WalletCard) => void;
}

const CUSTOM_TYPE_OPTIONS: Array<{ value: ObjectCardType; label: string }> = [
  { value: 'account', label: '账户 (account)' },
  { value: 'card', label: '银行卡 (card)' },
  { value: 'loan_product', label: '贷款产品 (loan_product)' },
  { value: 'loan_application', label: '贷款申请 (loan_application)' },
  { value: 'wealth_product', label: '理财产品 (wealth_product)' },
  { value: 'transaction', label: '交易流水 (transaction)' },
  { value: 'ticket', label: '客服工单 (ticket)' },
];

export const CardWallet: React.FC<CardWalletProps> = ({
  cards,
  creditLimits,
  assetsSynced,
  awaitingSlot,
  awaitingAccountQuestion,
  isSending,
  onSubmitCard,
  onAskAboutCard,
  onAddCustomCard,
}) => {
  const [showCustomForm, setShowCustomForm] = useState(false);
  const [customType, setCustomType] = useState<ObjectCardType>('account');
  const [customId, setCustomId] = useState('');
  const [customTitle, setCustomTitle] = useState('');

  const accountCards = cards.filter((c) => c.type === 'account' || c.type === 'card');
  const productCards = cards.filter(
    (c) => c.type === 'loan_product' || c.type === 'wealth_product',
  );
  const recordCards = cards.filter(
    (c) => c.type !== 'account' && c.type !== 'card' && c.type !== 'loan_product' && c.type !== 'wealth_product',
  );

  const handleCreateCustomCard = (e: React.FormEvent) => {
    e.preventDefault();
    const idTrimmed = customId.trim();
    if (!idTrimmed) {
      return;
    }
    const titleTrimmed = customTitle.trim() || `${customType} · ${idTrimmed}`;
    onAddCustomCard({
      type: customType,
      id: idTrimmed,
      title: titleTrimmed,
      attributes: { status: '自定义' },
      questionPrompt: `请帮我查询或办理 ${titleTrimmed}（${idTrimmed}）相关业务。`,
    });
    setCustomId('');
    setCustomTitle('');
    setShowCustomForm(false);
  };

  const renderGroup = (
    groupTitle: string,
    items: WalletCard[],
    allowRecommend: boolean,
  ) => {
    if (items.length === 0) {
      return null;
    }
    return (
      <section className="space-y-3">
        <div className="flex items-center gap-2">
          <h3 className="text-[11px] font-medium text-ink-2 tracking-wider uppercase whitespace-nowrap">
            {groupTitle}
          </h3>
          <div className="flex-1 h-px bg-hairline" />
        </div>

        <div className="space-y-3">
          {items.map((card, idx) => {
            const isRecommended =
              allowRecommend && awaitingAccountQuestion !== null;
            const showSealTag = isRecommended && idx === 0;

            return (
              <div
                key={`${card.type}_${card.id}`}
                className={`rounded-[10px] p-2 border bg-surface transition-colors ${
                  isRecommended ? 'border-seal' : 'border-hairline'
                }`}
              >
                {showSealTag ? (
                  <div className="mb-1.5 flex items-center justify-between">
                    <span className="text-[11px] font-medium text-seal">
                      推荐递交
                    </span>
                    <span className="micro-label text-mist">AUTO FILL</span>
                  </div>
                ) : null}

                <PhysicalCardPreview card={card} recommended={isRecommended} />

                <div className="mt-2 flex items-center justify-between gap-2">
                  <button
                    type="button"
                    disabled={isSending}
                    onClick={() =>
                      onSubmitCard({
                        type: card.type,
                        id: card.id,
                        title: card.title,
                        attributes: card.attributes,
                      })
                    }
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-[6px] bg-ink text-white text-[12px] font-medium hover:opacity-90 transition-opacity disabled:bg-mist disabled:cursor-not-allowed"
                  >
                    <Send className="w-3 h-3" />
                    <span>递交卡片</span>
                  </button>

                  <button
                    type="button"
                    onClick={() => onAskAboutCard(card.questionPrompt)}
                    className="text-[12px] text-ink-2 hover:text-ink hover:underline underline-offset-4 px-2 py-1"
                  >
                    就此提问
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      </section>
    );
  };

  const recommendAccountGroup =
    awaitingAccountQuestion !== null ||
    awaitingSlot === 'account_no' ||
    awaitingSlot === 'card_no';
  const recommendRecordGroup =
    awaitingSlot === 'application_no' || awaitingSlot === 'ticket_no';

  return (
    <div className="space-y-5">
      {assetsSynced ? (
        <div className="flex items-center justify-between text-[11px] text-ink-2 px-1">
          <span className="inline-flex items-center gap-1 text-celadon font-medium">
            <RefreshCw className="w-3 h-3" />
            <span>中台实时同步</span>
          </span>
          <span>余额与额度来自真实中台</span>
        </div>
      ) : null}

      {creditLimits.length > 0 ? (
        <div className="bg-paper border border-hairline rounded-[8px] px-3 py-2.5 space-y-1.5">
          <div className="flex items-center justify-between text-[11px]">
            <span className="font-medium text-ink">名下有效授信额度</span>
            <span className="text-mist tabular-mono">{creditLimits.length} 笔</span>
          </div>
          {creditLimits.map((limit) => (
            <div
              key={limit.limit_no}
              className="flex items-center justify-between gap-2 text-[11px] border-t border-hairline pt-1.5 first:border-t-0 first:pt-0"
            >
              <div className="min-w-0">
                <div className="tabular-mono text-ink font-medium truncate">
                  {limit.product_code}
                </div>
                <div className="text-mist tabular-mono">
                  有效期至 {limit.valid_to}
                </div>
              </div>
              <div className="text-right shrink-0 tabular-mono">
                <div className="text-ink font-semibold">
                  可用 {limit.available_limit_amount} 元
                </div>
                <div className="text-mist">总额 {limit.total_limit_amount} 元</div>
              </div>
            </div>
          ))}
        </div>
      ) : null}

      {awaitingAccountQuestion ? (
        <div className="bg-paper border border-seal/60 rounded-[8px] px-3 py-2 text-[12px] text-ink">
          <span className="font-medium text-seal">正在等待：</span>
          <span>{awaitingAccountQuestion}，点击卡片即可自动填写</span>
        </div>
      ) : recommendRecordGroup ? (
        <div className="bg-paper border border-seal/60 rounded-[8px] px-3 py-2 text-[12px] text-ink">
          <span className="font-medium text-seal">正在等待单号：</span>
          <span>点击下方贷款申请或工单卡片即可自动填槽查询进度</span>
        </div>
      ) : null}

      {renderGroup('账户与银行卡', accountCards, recommendAccountGroup)}
      {renderGroup('贷款与理财产品', productCards, false)}
      {renderGroup('交易与工单', recordCards, recommendRecordGroup)}

      {/* 可折叠自定义卡片表单 */}
      <div className="pt-2 border-t border-hairline">
        <button
          type="button"
          onClick={() => setShowCustomForm((prev) => !prev)}
          className="w-full flex items-center justify-between text-[12px] text-ink-2 hover:text-ink py-1.5"
          aria-expanded={showCustomForm}
        >
          <span className="inline-flex items-center gap-1.5 font-medium">
            <Plus className="w-3.5 h-3.5" />
            <span>自定义卡片</span>
          </span>
          {showCustomForm ? (
            <ChevronUp className="w-3.5 h-3.5" />
          ) : (
            <ChevronDown className="w-3.5 h-3.5" />
          )}
        </button>

        {showCustomForm ? (
          <form onSubmit={handleCreateCustomCard} className="mt-2 space-y-2.5 bg-paper p-3 rounded-[8px] border border-hairline">
            <div>
              <label className="block text-[11px] text-ink-2 mb-1">卡片类型</label>
              <select
                value={customType}
                onChange={(e) => setCustomType(e.target.value as ObjectCardType)}
                className="w-full bg-surface border border-hairline rounded px-2.5 py-1.5 text-[12px] text-ink"
              >
                {CUSTOM_TYPE_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-[11px] text-ink-2 mb-1">对象编号 (id)</label>
              <input
                type="text"
                required
                value={customId}
                onChange={(e) => setCustomId(e.target.value)}
                placeholder="例如 ACC0000000001"
                className="w-full bg-surface border border-hairline rounded px-2.5 py-1.5 text-[12px] tabular-mono text-ink placeholder:text-mist"
              />
            </div>
            <div>
              <label className="block text-[11px] text-ink-2 mb-1">显示标题 (title)</label>
              <input
                type="text"
                value={customTitle}
                onChange={(e) => setCustomTitle(e.target.value)}
                placeholder="例如 测试银行卡"
                className="w-full bg-surface border border-hairline rounded px-2.5 py-1.5 text-[12px] text-ink placeholder:text-mist"
              />
            </div>
            <button
              type="submit"
              className="w-full py-1.5 rounded bg-ink text-white text-[12px] font-medium hover:opacity-90 transition-opacity"
            >
              加入卡包
            </button>
          </form>
        ) : null}
      </div>
    </div>
  );
};
