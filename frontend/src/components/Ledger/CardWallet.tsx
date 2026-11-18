import React, { useState } from 'react';
import { ChevronDown, ChevronUp, Plus, Send } from 'lucide-react';
import { ChatObject, ObjectCardType, WalletCard } from '../../types/chat';
import { PhysicalCardPreview } from '../cards/PhysicalCardPreview';

interface CardWalletProps {
  cards: WalletCard[];
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
  { value: 'wealth_product', label: '理财产品 (wealth_product)' },
  { value: 'transaction', label: '交易流水 (transaction)' },
  { value: 'ticket', label: '客服工单 (ticket)' },
];

export const CardWallet: React.FC<CardWalletProps> = ({
  cards,
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

  return (
    <div className="space-y-5">
      {awaitingAccountQuestion ? (
        <div className="bg-paper border border-seal/60 rounded-[8px] px-3 py-2 text-[12px] text-ink">
          <span className="font-medium text-seal">正在等待：</span>
          <span>{awaitingAccountQuestion}，点击卡片即可自动填写</span>
        </div>
      ) : null}

      {renderGroup('账户与银行卡', accountCards, true)}
      {renderGroup('贷款与理财产品', productCards, false)}
      {renderGroup('交易与工单', recordCards, false)}

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
