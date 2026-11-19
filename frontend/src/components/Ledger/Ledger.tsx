import React from 'react';
import { X } from 'lucide-react';
import { ChatObject, CustomerCreditLimit, ReceiptData, WalletCard } from '../../types/chat';
import { CardWallet } from './CardWallet';
import { ReceiptBook } from './ReceiptBook';

export type LedgerTab = 'wallet' | 'receipts';

interface LedgerProps {
  isOpen: boolean;
  activeTab: LedgerTab;
  onChangeTab: (tab: LedgerTab) => void;
  onCloseDrawer: () => void;
  flashHighlight: boolean;
  walletCards: WalletCard[];
  creditLimits: CustomerCreditLimit[];
  assetsSynced: boolean;
  receipts: ReceiptData[];
  awaitingSlot: string | null;
  awaitingAccountQuestion: string | null;
  isSending: boolean;
  onSubmitCard: (obj: ChatObject) => void;
  onAskAboutCard: (prompt: string) => void;
  onAddCustomCard: (card: WalletCard) => void;
}

export const Ledger: React.FC<LedgerProps> = ({
  isOpen,
  activeTab,
  onChangeTab,
  onCloseDrawer,
  flashHighlight,
  walletCards,
  creditLimits,
  assetsSynced,
  receipts,
  awaitingSlot,
  awaitingAccountQuestion,
  isSending,
  onSubmitCard,
  onAskAboutCard,
  onAddCustomCard,
}) => {
  const content = (
    <div className="h-full flex flex-col bg-surface">
      {/* 顶部标签栏 */}
      <div className="px-4 pt-3 pb-0 border-b border-hairline flex items-center justify-between gap-2 shrink-0">
        <div className="flex items-center gap-5" role="tablist" aria-label="凭证簿标签">
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === 'wallet'}
            onClick={() => onChangeTab('wallet')}
            className={`pb-2.5 text-[14px] font-medium border-b-2 transition-colors ${
              activeTab === 'wallet'
                ? 'border-ink text-ink'
                : 'border-transparent text-ink-2 hover:text-ink'
            }`}
          >
            卡包
          </button>

          <button
            type="button"
            role="tab"
            aria-selected={activeTab === 'receipts'}
            onClick={() => onChangeTab('receipts')}
            className={`pb-2.5 text-[14px] font-medium border-b-2 transition-colors inline-flex items-center gap-1.5 ${
              activeTab === 'receipts'
                ? 'border-ink text-ink'
                : 'border-transparent text-ink-2 hover:text-ink'
            }`}
          >
            <span>凭证</span>
            <span className="tabular-mono text-[11px] text-ink-2 bg-paper border border-hairline px-1.5 py-0.2 rounded">
              {receipts.length}
            </span>
          </button>
        </div>

        <button
          type="button"
          onClick={onCloseDrawer}
          aria-label="关闭凭证簿"
          className="xl:hidden p-1.5 rounded text-ink-2 hover:text-ink hover:bg-paper mb-1.5"
        >
          <X className="w-4 h-4" />
        </button>
      </div>

      {/* 内容区 */}
      <div className="flex-1 overflow-y-auto p-4">
        {activeTab === 'wallet' ? (
          <CardWallet
            cards={walletCards}
            creditLimits={creditLimits}
            assetsSynced={assetsSynced}
            awaitingSlot={awaitingSlot}
            awaitingAccountQuestion={awaitingAccountQuestion}
            isSending={isSending}
            onSubmitCard={onSubmitCard}
            onAskAboutCard={onAskAboutCard}
            onAddCustomCard={onAddCustomCard}
          />
        ) : (
          <ReceiptBook receipts={receipts} />
        )}
      </div>
    </div>
  );

  return (
    <>
      {/* 桌面端（>= 1280px）右侧固定栏（可收起） */}
      {isOpen ? (
        <aside
          className={`hidden xl:flex flex-col w-[360px] shrink-0 border-l transition-colors duration-300 ${
            flashHighlight ? 'border-seal ring-1 ring-seal' : 'border-hairline'
          }`}
          aria-label="凭证簿 Ledger"
        >
          {content}
        </aside>
      ) : null}

      {/* 平板及移动端（< 1280px）右侧抽屉 */}
      {isOpen ? (
        <div className="xl:hidden fixed inset-0 z-40 flex justify-end">
          <div
            className="fixed inset-0 bg-ink/20"
            onClick={onCloseDrawer}
            aria-hidden="true"
          />
          <aside
            className="relative z-50 w-full max-w-[360px] h-full border-l border-hairline shadow-ledger"
            aria-label="凭证簿抽屉"
          >
            {content}
          </aside>
        </div>
      ) : null}
    </>
  );
};
