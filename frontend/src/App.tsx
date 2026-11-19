import React, { useRef, useState } from 'react';
import { Composer } from './components/Composer/Composer';
import { Conversation } from './components/Conversation/Conversation';
import { Header } from './components/Header/Header';
import { KnowledgeAdminModal } from './components/KnowledgeAdminModal';
import { Ledger, LedgerTab } from './components/Ledger/Ledger';
import { Rail } from './components/Rail/Rail';
import { WorkflowStrip } from './components/WorkflowStrip/WorkflowStrip';
import { useChat } from './hooks/useChat';

export const App: React.FC = () => {
  const {
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
    refreshHistory,
    reconnectEngine,
    clearLocalView,
    sendText,
    sendObject,
    retryFailedMessage,
    addCustomCard,
  } = useChat();

  const [composerText, setComposerText] = useState('');
  const [ledgerOpen, setLedgerOpen] = useState(() =>
    typeof window !== 'undefined' ? window.innerWidth >= 1280 : true,
  );
  const [ledgerTab, setLedgerTab] = useState<LedgerTab>('wallet');
  const [flashLedgerBorder, setFlashLedgerBorder] = useState(false);
  const [kbAdminOpen, setKbAdminOpen] = useState(false);

  const composerInputRef = useRef<HTMLTextAreaElement>(null);

  const handleOpenWalletFromComposer = () => {
    setLedgerTab('wallet');
    setLedgerOpen(true);

    // 桌面端让凭证簿边框闪一次朱砂色描边作为提示
    setFlashLedgerBorder(true);
    window.setTimeout(() => setFlashLedgerBorder(false), 850);
  };

  const handleAskAboutCard = (prompt: string) => {
    setComposerText(prompt);
    window.requestAnimationFrame(() => {
      composerInputRef.current?.focus();
    });
  };

  return (
    <div className="h-screen w-screen overflow-hidden bg-paper text-ink flex flex-col lg:flex-row">
      {/* 桌面端在左侧，移动端渲染到底部 Tab 栏 */}
      <div className="order-2 lg:order-1 shrink-0 lg:h-full">
        <Rail
          customerId={customerId}
          walletCards={walletCards}
          isSending={isSending}
          onSwitchCustomer={switchCustomer}
          onSendPrompt={sendText}
        />
      </div>

      {/* 中间对话主栏 + 右侧凭证簿 */}
      <div className="order-1 lg:order-2 flex-1 min-w-0 min-h-0 flex">
        <main className="flex-1 min-w-0 flex flex-col bg-paper">
          <Header
            customerId={customerId}
            engineStatus={engineStatus}
            financeStatus={financeStatus}
            ragStatus={ragStatus}
            isLedgerOpen={ledgerOpen}
            isRefreshing={isLoadingHistory}
            onRefreshHistory={() => void refreshHistory()}
            onClearLocalView={clearLocalView}
            onToggleLedger={() => setLedgerOpen((prev) => !prev)}
            onOpenKnowledgeAdmin={() => setKbAdminOpen(true)}
          />

          <WorkflowStrip
            workflow={workflow}
            disabled={isSending}
            onResumeFlow={(flowName) => void sendText(`继续${flowName}`)}
          />

          <Conversation
            timeline={timeline}
            workflow={workflow}
            quickReplies={quickReplies}
            streamStageLabel={streamStageLabel}
            isLoadingHistory={isLoadingHistory}
            isSending={isSending}
            engineOfflineBanner={engineOfflineBanner}
            onReconnect={() => void reconnectEngine()}
            onSelectPrompt={(prompt) => void sendText(prompt)}
            onRetryMessage={(id) => void retryFailedMessage(id)}
          />

          <Composer
            value={composerText}
            onChange={setComposerText}
            onSend={(text) => void sendText(text)}
            onOpenWallet={handleOpenWalletFromComposer}
            workflow={workflow}
            isSending={isSending}
            inputRef={composerInputRef}
          />
        </main>

        <Ledger
          isOpen={ledgerOpen}
          activeTab={ledgerTab}
          onChangeTab={setLedgerTab}
          onCloseDrawer={() => setLedgerOpen(false)}
          flashHighlight={flashLedgerBorder}
          walletCards={walletCards}
          creditLimits={creditLimits}
          assetsSynced={assetsSynced}
          receipts={receipts}
          awaitingSlot={awaitingSlot}
          awaitingAccountQuestion={awaitingAccountQuestion}
          isSending={isSending}
          onSubmitCard={(obj) => void sendObject(obj)}
          onAskAboutCard={handleAskAboutCard}
          onAddCustomCard={addCustomCard}
        />
      </div>

      <KnowledgeAdminModal
        isOpen={kbAdminOpen}
        onClose={() => setKbAdminOpen(false)}
        importOnline={ragEndpoints.importOnline}
        importUrl={ragEndpoints.importUrl}
      />
    </div>
  );
};

export default App;
