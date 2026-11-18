import React, { useEffect, useRef, useState } from 'react';
import {
  BookOpen,
  Briefcase,
  ChevronRight,
  CreditCard,
  Landmark,
  ListOrdered,
  MessageSquareWarning,
  Play,
  RotateCcw,
  StepForward,
  UserCheck,
  Users,
  Wallet,
  X,
} from 'lucide-react';
import {
  buildDemoScriptSteps,
  BUSINESS_SCENARIOS,
  CUSTOMER_PRESETS,
  KNOWLEDGE_SCENARIOS,
} from '../../constants/presets';
import { WalletCard } from '../../types/chat';

export type RailSection = 'customers' | 'business' | 'knowledge' | 'demo';

interface RailProps {
  customerId: string;
  walletCards: WalletCard[];
  isSending: boolean;
  onSwitchCustomer: (nextId: string) => void;
  onSendPrompt: (prompt: string) => Promise<boolean>;
}

const SCENARIO_ICON_MAP: Record<string, React.ComponentType<{ className?: string }>> = {
  balance: Wallet,
  transactions: ListOrdered,
  loan: Landmark,
  card_loss: CreditCard,
  ticket: MessageSquareWarning,
};

export const Rail: React.FC<RailProps> = ({
  customerId,
  walletCards,
  isSending,
  onSwitchCustomer,
  onSendPrompt,
}) => {
  const [pinnedOpen, setPinnedOpen] = useState(false);
  const [hoveredOpen, setHoveredOpen] = useState(false);
  const [activeSection, setActiveSection] = useState<RailSection>('customers');
  const [mobileDrawerOpen, setMobileDrawerOpen] = useState(false);
  const [customSenderInput, setCustomSenderInput] = useState('');

  // 演示脚本状态
  const [demoStepIndex, setDemoStepIndex] = useState(0);
  const [isAutoRunning, setIsAutoRunning] = useState(false);
  const autoCancelRef = useRef(false);

  const firstAccountCard = walletCards.find(
    (c) => c.type === 'account' || c.type === 'card',
  );
  const demoSteps = buildDemoScriptSteps(firstAccountCard?.id ?? 'ACC0000000001');

  useEffect(() => {
    autoCancelRef.current = true;
    setIsAutoRunning(false);
    setDemoStepIndex(0);
  }, [customerId]);

  const isExpanded = pinnedOpen || hoveredOpen;

  const handleToggleSection = (section: RailSection) => {
    if (pinnedOpen && activeSection === section) {
      setPinnedOpen(false);
      return;
    }
    setActiveSection(section);
    setPinnedOpen(true);
  };

  const handleMobileTab = (section: RailSection) => {
    if (mobileDrawerOpen && activeSection === section) {
      setMobileDrawerOpen(false);
      return;
    }
    setActiveSection(section);
    setMobileDrawerOpen(true);
  };

  const handleCustomSwitch = (e: React.FormEvent) => {
    e.preventDefault();
    const trimmed = customSenderInput.trim();
    if (!trimmed) {
      return;
    }
    onSwitchCustomer(trimmed);
    setCustomSenderInput('');
    setMobileDrawerOpen(false);
  };

  const handleStepSend = async () => {
    if (isSending || isAutoRunning || demoStepIndex >= demoSteps.length) {
      return;
    }
    const ok = await onSendPrompt(demoSteps[demoStepIndex]);
    if (ok) {
      setDemoStepIndex((prev) => prev + 1);
    }
  };

  const handleAutoDemo = async () => {
    if (isSending || isAutoRunning || demoStepIndex >= demoSteps.length) {
      return;
    }
    autoCancelRef.current = false;
    setIsAutoRunning(true);

    let cursor = demoStepIndex;
    while (cursor < demoSteps.length && !autoCancelRef.current) {
      const ok = await onSendPrompt(demoSteps[cursor]);
      if (!ok || autoCancelRef.current) {
        break;
      }
      cursor += 1;
      setDemoStepIndex(cursor);
      if (cursor < demoSteps.length) {
        await new Promise((resolve) => window.setTimeout(resolve, 600));
      }
    }
    setIsAutoRunning(false);
  };

  const handleResetDemo = () => {
    autoCancelRef.current = true;
    setIsAutoRunning(false);
    setDemoStepIndex(0);
  };

  const navItems: Array<{
    id: RailSection;
    label: string;
    icon: React.ComponentType<{ className?: string }>;
  }> = [
    { id: 'customers', label: '客户切换', icon: Users },
    { id: 'business', label: '业务场景', icon: Briefcase },
    { id: 'knowledge', label: '知识问答', icon: BookOpen },
    { id: 'demo', label: '演示脚本', icon: Play },
  ];

  const renderPanelContent = () => (
    <div className="flex-1 overflow-y-auto p-4 space-y-4">
      {activeSection === 'customers' ? (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-[11px] font-medium text-ink-2 tracking-wider uppercase">
              预设客户身份
            </h2>
            <span className="micro-label text-mist">PRESET</span>
          </div>

          <div className="space-y-2">
            {CUSTOMER_PRESETS.map((preset) => {
              const selected = preset.id === customerId;
              return (
                <button
                  key={preset.id}
                  type="button"
                  onClick={() => {
                    onSwitchCustomer(preset.id);
                    setMobileDrawerOpen(false);
                  }}
                  className={`relative w-full text-left p-3 rounded-[8px] border transition-colors ${
                    selected
                      ? 'bg-paper border-hairline border-l-2 border-l-seal'
                      : 'bg-surface border-hairline hover:border-ink'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="font-serif text-[14px] font-semibold text-ink">
                      {preset.name}
                    </span>
                    <span className="tabular-mono text-[11px] text-ink-2">
                      {preset.id}
                    </span>
                  </div>
                  <p className="text-[11px] text-ink-2 mt-1 leading-relaxed">
                    {preset.subtitle}
                  </p>
                </button>
              );
            })}
          </div>

          <form onSubmit={handleCustomSwitch} className="pt-3 border-t border-hairline space-y-2">
            <label className="block text-[11px] text-ink-2">
              自定义客户号（sender_id）
            </label>
            <div className="flex items-center gap-1.5">
              <input
                type="text"
                value={customSenderInput}
                onChange={(e) => setCustomSenderInput(e.target.value)}
                placeholder="例如 CUS00000005"
                className="flex-1 min-w-0 bg-paper border border-hairline rounded px-2.5 py-1.5 text-[12px] tabular-mono text-ink placeholder:text-mist"
              />
              <button
                type="submit"
                className="shrink-0 px-2.5 py-1.5 rounded bg-ink text-white text-[12px] font-medium hover:opacity-90"
              >
                切换
              </button>
            </div>
          </form>
        </div>
      ) : null}

      {activeSection === 'business' ? (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-[11px] font-medium text-ink-2 tracking-wider uppercase">
              五大核心业务场景
            </h2>
            <span className="micro-label text-mist">FLOW</span>
          </div>

          <div className="space-y-2">
            {BUSINESS_SCENARIOS.map((item) => {
              const Icon = SCENARIO_ICON_MAP[item.id] ?? Briefcase;
              return (
                <button
                  key={item.id}
                  type="button"
                  disabled={isSending}
                  onClick={() => {
                    void onSendPrompt(item.prompt);
                    setMobileDrawerOpen(false);
                  }}
                  className="w-full text-left p-3 rounded-[8px] bg-surface border border-hairline hover:border-ink transition-colors disabled:opacity-50"
                >
                  <div className="flex items-center gap-2 text-[14px] font-medium text-ink">
                    <Icon className="w-4 h-4 text-ink-2 shrink-0" />
                    <span>{item.title}</span>
                  </div>
                  <p className="text-[12px] text-ink-2 mt-1 line-clamp-2">
                    {item.prompt}
                  </p>
                </button>
              );
            })}
          </div>
        </div>
      ) : null}

      {activeSection === 'knowledge' ? (
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-[11px] font-medium text-ink-2 tracking-wider uppercase">
              金融知识问答
            </h2>
            <span className="micro-label text-mist">FAQ / RAG</span>
          </div>

          <div className="space-y-2">
            {KNOWLEDGE_SCENARIOS.map((item) => (
              <button
                key={item.id}
                type="button"
                disabled={isSending}
                onClick={() => {
                  void onSendPrompt(item.prompt);
                  setMobileDrawerOpen(false);
                }}
                className="w-full text-left p-3 rounded-[8px] bg-surface border border-hairline hover:border-ink transition-colors disabled:opacity-50"
              >
                <div className="text-[14px] font-medium text-ink">{item.title}</div>
                <p className="text-[12px] text-ink-2 mt-1">{item.prompt}</p>
              </button>
            ))}
          </div>
        </div>
      ) : null}

      {activeSection === 'demo' ? (
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-[11px] font-medium text-ink-2 tracking-wider uppercase">
              演示脚本 · 插队与恢复
            </h2>
            <span className="tabular-mono text-[11px] text-ink-2">
              {demoStepIndex}/{demoSteps.length}
            </span>
          </div>

          {/* 竖向时间线 */}
          <ol className="space-y-3">
            {demoSteps.map((stepText, idx) => {
              const isDone = idx < demoStepIndex;
              const isCurrent = idx === demoStepIndex;

              return (
                <li key={`${idx}_${stepText}`} className="flex gap-2.5">
                  <div className="flex flex-col items-center">
                    <span
                      className={`w-5 h-5 rounded-full border text-[11px] tabular-mono flex items-center justify-center shrink-0 ${
                        isDone
                          ? 'bg-celadon border-celadon text-white'
                          : isCurrent
                            ? 'bg-ink border-ink text-white'
                            : 'bg-surface border-hairline text-mist'
                      }`}
                    >
                      {idx + 1}
                    </span>
                    {idx < demoSteps.length - 1 ? (
                      <span className="w-px flex-1 bg-hairline mt-1" />
                    ) : null}
                  </div>
                  <div className="pb-2 min-w-0">
                    <div className="text-[11px] text-ink-2">
                      {isDone ? '已完成' : isCurrent ? '当前步骤' : '待执行'}
                    </div>
                    <div
                      className={`text-[12px] mt-0.5 break-words ${
                        isCurrent ? 'text-ink font-medium' : 'text-ink-2'
                      }`}
                    >
                      {stepText}
                    </div>
                  </div>
                </li>
              );
            })}
          </ol>

          <div className="flex items-center gap-2">
            <button
              type="button"
              disabled={isSending || isAutoRunning || demoStepIndex >= demoSteps.length}
              onClick={() => void handleStepSend()}
              className="flex-1 inline-flex items-center justify-center gap-1 px-2.5 py-1.5 rounded bg-ink text-white text-[12px] font-medium hover:opacity-90 disabled:bg-mist disabled:cursor-not-allowed"
            >
              <StepForward className="w-3.5 h-3.5" />
              <span>逐步发送</span>
            </button>

            <button
              type="button"
              disabled={isSending || isAutoRunning || demoStepIndex >= demoSteps.length}
              onClick={() => void handleAutoDemo()}
              className="flex-1 inline-flex items-center justify-center gap-1 px-2.5 py-1.5 rounded border border-ink text-ink text-[12px] font-medium hover:bg-paper disabled:border-hairline disabled:text-mist disabled:cursor-not-allowed"
            >
              <Play className="w-3.5 h-3.5" />
              <span>{isAutoRunning ? '演示中' : '自动演示'}</span>
            </button>

            <button
              type="button"
              onClick={handleResetDemo}
              aria-label="重置演示脚本"
              title="重置"
              className="p-1.5 rounded border border-hairline text-ink-2 hover:text-ink hover:border-ink"
            >
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
          </div>

          <p className="text-[11px] text-ink-2 leading-relaxed bg-paper border border-hairline rounded p-2.5">
            在 CUS00000001 下，最终提交会因为没有授信额度返回失败提示，但暂停/恢复过程完整可见；切换到 CUS00000031 并改用其账户，可以走完真实进件。
          </p>
        </div>
      ) : null}
    </div>
  );

  return (
    <>
      {/* 桌面端左侧轨 (>= 1024px) */}
      <aside
        onMouseEnter={() => setHoveredOpen(true)}
        onMouseLeave={() => setHoveredOpen(false)}
        className={`hidden lg:flex h-full bg-surface border-r border-hairline shrink-0 transition-[width] duration-200 overflow-hidden ${
          isExpanded ? 'w-[280px]' : 'w-[72px]'
        }`}
        aria-label="左侧导航轨"
      >
        {/* 72px 图标条 */}
        <div className="w-[72px] shrink-0 flex flex-col items-center py-4 gap-2 border-r border-hairline">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = activeSection === item.id;
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => handleToggleSection(item.id)}
                aria-label={item.label}
                title={item.label}
                className={`w-12 py-2.5 rounded-[8px] flex flex-col items-center gap-1 transition-colors ${
                  active
                    ? 'bg-paper text-ink border border-hairline'
                    : 'text-ink-2 hover:text-ink hover:bg-paper/60'
                }`}
              >
                <Icon className="w-4 h-4" />
                <span className="text-[11px] leading-none">{item.label.slice(0, 2)}</span>
              </button>
            );
          })}

          <div className="mt-auto pt-3 border-t border-hairline w-10 flex flex-col items-center gap-1">
            <UserCheck className="w-4 h-4 text-celadon" />
            <span className="tabular-mono text-[11px] text-ink-2">
              {customerId.slice(-4)}
            </span>
          </div>
        </div>

        {/* 展开面板内容 */}
        {isExpanded ? (
          <div className="w-[208px] flex flex-col min-w-0">
            <div className="px-4 py-3 border-b border-hairline flex items-center justify-between">
              <span className="text-[12px] font-medium text-ink">
                {navItems.find((n) => n.id === activeSection)?.label}
              </span>
              <button
                type="button"
                onClick={() => {
                  setPinnedOpen(false);
                  setHoveredOpen(false);
                }}
                aria-label="收起侧轨"
                className="p-1 rounded text-ink-2 hover:text-ink"
              >
                <ChevronRight className="w-3.5 h-3.5 rotate-180" />
              </button>
            </div>
            {renderPanelContent()}
          </div>
        ) : null}
      </aside>

      {/* 移动/平板端抽屉 (< 1024px) */}
      {mobileDrawerOpen ? (
        <div className="lg:hidden fixed inset-0 z-40 flex">
          <div
            className="fixed inset-0 bg-ink/20"
            onClick={() => setMobileDrawerOpen(false)}
            aria-hidden="true"
          />
          <aside className="relative z-50 w-[290px] max-w-[85vw] h-full bg-surface border-r border-hairline flex flex-col shadow-ledger">
            <div className="px-4 py-3 border-b border-hairline flex items-center justify-between">
              <span className="text-[14px] font-serif font-semibold text-ink">
                {navItems.find((n) => n.id === activeSection)?.label}
              </span>
              <button
                type="button"
                onClick={() => setMobileDrawerOpen(false)}
                aria-label="关闭侧栏"
                className="p-1.5 rounded text-ink-2 hover:text-ink"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            {renderPanelContent()}
          </aside>
        </div>
      ) : null}

      {/* 移动/平板端底部 Tab 栏 (< 1024px) */}
      <nav
        className="lg:hidden bg-surface border-t border-hairline grid grid-cols-4 shrink-0"
        aria-label="底部功能导航"
      >
        {navItems.map((item) => {
          const Icon = item.icon;
          const active = mobileDrawerOpen && activeSection === item.id;
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => handleMobileTab(item.id)}
              className={`py-2 flex flex-col items-center gap-1 text-[11px] ${
                active ? 'text-ink font-medium bg-paper' : 'text-ink-2'
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>
    </>
  );
};
