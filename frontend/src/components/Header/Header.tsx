import React from 'react';
import {
  BookOpen,
  ClipboardList,
  Eraser,
  PanelRightClose,
  PanelRightOpen,
  RefreshCw,
} from 'lucide-react';
import { CUSTOMER_PRESETS } from '../../constants/presets';
import { ServiceHealthStatus } from '../../types/chat';

interface HeaderProps {
  customerId: string;
  engineStatus: ServiceHealthStatus;
  financeStatus: ServiceHealthStatus;
  ragStatus: ServiceHealthStatus;
  isLedgerOpen: boolean;
  isRefreshing: boolean;
  onRefreshHistory: () => void;
  onClearLocalView: () => void;
  onToggleLedger: () => void;
  onOpenKnowledgeAdmin: () => void;
  onOpenTicketAdmin: () => void;
}

const HealthIndicator: React.FC<{
  label: string;
  status: ServiceHealthStatus;
}> = ({ label, status }) => {
  const dotClass =
    status === 'online'
      ? 'bg-celadon animate-status-breathe'
      : status === 'offline'
        ? 'bg-seal'
        : 'bg-mist';

  return (
    <div
      className="inline-flex items-center gap-1.5 text-[12px] text-ink-2 whitespace-nowrap"
      title={`${label}：${status === 'online' ? '在线' : status === 'offline' ? '离线' : '检测中'}`}
    >
      <span className={`w-2 h-2 rounded-full shrink-0 ${dotClass}`} />
      <span>{label}</span>
    </div>
  );
};

export const Header: React.FC<HeaderProps> = ({
  customerId,
  engineStatus,
  financeStatus,
  ragStatus,
  isLedgerOpen,
  isRefreshing,
  onRefreshHistory,
  onClearLocalView,
  onToggleLedger,
  onOpenKnowledgeAdmin,
  onOpenTicketAdmin,
}) => {
  const preset = CUSTOMER_PRESETS.find((c) => c.id === customerId);
  const displayName = preset?.name ?? '自定义客户';

  return (
    <header className="h-14 bg-surface border-b border-hairline px-4 md:px-6 flex items-center justify-between gap-4 shrink-0">
      {/* 左侧品牌 + 当前客户 */}
      <div className="flex items-center gap-3 min-w-0">
        <h1 className="font-serif text-[16px] font-semibold tracking-tight text-ink whitespace-nowrap">
          中州银行 · 智能柜台
        </h1>
        <span className="h-4 w-px bg-hairline hidden sm:inline-block" aria-hidden="true" />
        <div className="hidden sm:flex items-center gap-2 min-w-0">
          <span className="text-[12px] text-ink font-medium truncate">
            {displayName}
          </span>
          <span className="tabular-mono text-[11px] text-ink-2 bg-paper border border-hairline px-1.5 py-0.5 rounded">
            {customerId}
          </span>
        </div>
      </div>

      {/* 右侧状态点 + 操作按钮 */}
      <div className="flex items-center gap-3 md:gap-4 shrink-0">
        <div className="hidden md:flex items-center gap-4">
          <HealthIndicator label="客服引擎 :18082" status={engineStatus} />
          <HealthIndicator label="金融中台 :8000" status={financeStatus} />
          <HealthIndicator label="金融智脑 :8001" status={ragStatus} />
        </div>

        <div className="flex items-center gap-1 border-l border-hairline pl-2 md:pl-3">
          <button
            type="button"
            onClick={onOpenTicketAdmin}
            aria-label="打开员工工单后台"
            title="员工后台：处理投诉与反馈工单"
            className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded text-[12px] text-ink-2 hover:text-ink hover:bg-paper transition-colors"
          >
            <ClipboardList className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">员工工单台</span>
          </button>
          <button
            type="button"
            onClick={onOpenKnowledgeAdmin}
            aria-label="打开金融智脑知识库"
            title="知识库管理 (:8002 / :8001)"
            className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded text-[12px] text-ink-2 hover:text-ink hover:bg-paper transition-colors"
          >
            <BookOpen className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">知识库</span>
          </button>
          <button
            type="button"
            onClick={onRefreshHistory}
            disabled={isRefreshing}
            aria-label="刷新对话历史"
            title="刷新历史"
            className="p-2 rounded text-ink-2 hover:text-ink hover:bg-paper transition-colors disabled:opacity-50"
          >
            <RefreshCw
              className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`}
            />
          </button>

          <button
            type="button"
            onClick={onClearLocalView}
            aria-label="清空本地视图"
            title="清空本地视图"
            className="p-2 rounded text-ink-2 hover:text-ink hover:bg-paper transition-colors"
          >
            <Eraser className="w-4 h-4" />
          </button>

          <button
            type="button"
            onClick={onToggleLedger}
            aria-label={isLedgerOpen ? '收起凭证簿' : '展开凭证簿'}
            title={isLedgerOpen ? '收起凭证簿' : '展开凭证簿'}
            className="p-2 rounded text-ink-2 hover:text-ink hover:bg-paper transition-colors"
          >
            {isLedgerOpen ? (
              <PanelRightClose className="w-4 h-4" />
            ) : (
              <PanelRightOpen className="w-4 h-4" />
            )}
          </button>
        </div>
      </div>
    </header>
  );
};
