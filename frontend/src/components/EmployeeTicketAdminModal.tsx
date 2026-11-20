import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  CheckCircle2,
  ClipboardList,
  ExternalLink,
  RefreshCw,
  Search,
  Send,
  Star,
  UserCheck,
  X,
} from 'lucide-react';
import {
  AdminEmployeeOption,
  AdminTicketItem,
  fetchAdminTickets,
  handleAdminTicket,
} from '../services/api';

interface EmployeeTicketAdminModalProps {
  isOpen: boolean;
  onClose: () => void;
  currentCustomerId: string;
  onTicketHandled?: (customerNo: string) => void;
  fullPage?: boolean;
}

const STATUS_META: Record<string, { label: string; badgeClass: string }> = {
  submitted: {
    label: '待受理',
    badgeClass: 'bg-seal/10 text-seal border-seal/30',
  },
  processing: {
    label: '处理中',
    badgeClass: 'bg-amber/10 text-amber border-amber/30',
  },
  resolved: {
    label: '已解决',
    badgeClass: 'bg-celadon/10 text-celadon border-celadon/30',
  },
  closed: {
    label: '已完结',
    badgeClass: 'bg-paper text-ink-2 border-hairline',
  },
  rejected: {
    label: '已退回',
    badgeClass: 'bg-paper text-mist border-hairline',
  },
};

const QUICK_REPLY_TEMPLATES: Array<{ label: string; status: string; content: string }> = [
  {
    label: '扣费核查退还',
    status: 'resolved',
    content:
      '经核查，该笔异常扣费系系统计费延迟触发，已为您完成原路退回至扣款账户，请查收账户变动通知。',
  },
  {
    label: '转账已核实入账',
    status: 'resolved',
    content:
      '已为您核对跨行清算流水，该笔转账交易已成功清算入账，如收款方仍未更新余额请刷新网银查看。',
  },
  {
    label: '已升级专员核实',
    status: 'processing',
    content:
      '专席已受理您的诉求并调取后台交易日志核查中，预计将在 2 小时内向您同步最终处理结论。',
  },
  {
    label: '建议已采纳归档',
    status: 'closed',
    content:
      '感谢您对中州银行产品与服务的宝贵建议，您的反馈已记录并同步至产品研发团队评估优化。',
  },
];

const DEFAULT_EMPLOYEES: AdminEmployeeOption[] = [
  { employee_no: 'EMP000006', employee_name: '客服人员06', employee_role: 'customer_service' },
  { employee_no: 'EMP000005', employee_name: '运营人员05', employee_role: 'operator' },
  { employee_no: 'EMP000001', employee_name: '客户经理01', employee_role: 'relationship_manager' },
];

export const EmployeeTicketAdminModal: React.FC<EmployeeTicketAdminModalProps> = ({
  isOpen,
  onClose,
  currentCustomerId,
  onTicketHandled,
  fullPage = false,
}) => {
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [onlyCurrentCustomer, setOnlyCurrentCustomer] = useState<boolean>(false);
  const [keyword, setKeyword] = useState<string>('');
  const [searchInput, setSearchInput] = useState<string>('');
  const [tickets, setTickets] = useState<AdminTicketItem[]>([]);
  const [statusCounts, setStatusCounts] = useState<Record<string, number>>({});
  const [employees, setEmployees] = useState<AdminEmployeeOption[]>(DEFAULT_EMPLOYEES);
  const [operatorNo, setOperatorNo] = useState<string>('EMP000006');
  const [selectedTicketNo, setSelectedTicketNo] = useState<string>('');
  const [targetStatus, setTargetStatus] = useState<string>('resolved');
  const [handleResult, setHandleResult] = useState<string>('');
  const [notifyCustomer, setNotifyCustomer] = useState<boolean>(true);
  const [pushToChat, setPushToChat] = useState<boolean>(true);
  const [loading, setLoading] = useState<boolean>(false);
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [errorBanner, setErrorBanner] = useState<string | null>(null);
  const [successBanner, setSuccessBanner] = useState<string | null>(null);

  const loadTickets = useCallback(async () => {
    setLoading(true);
    setErrorBanner(null);
    try {
      const data = await fetchAdminTickets({
        ticket_status: statusFilter || undefined,
        customer_no: onlyCurrentCustomer ? currentCustomerId : undefined,
        keyword: keyword || undefined,
        operator_no: operatorNo,
        page_no: 1,
        page_size: 40,
      });
      setTickets(data.list ?? []);
      setStatusCounts(data.status_counts ?? {});
      if (data.employees && data.employees.length > 0) {
        setEmployees(data.employees);
      }
      setSelectedTicketNo((prev) => {
        if (prev && (data.list ?? []).some((t) => t.ticket_no === prev)) {
          return prev;
        }
        return data.list?.[0]?.ticket_no ?? '';
      });
    } catch (err) {
      setErrorBanner(err instanceof Error ? err.message : '加载工单列表失败');
    } finally {
      setLoading(false);
    }
  }, [currentCustomerId, keyword, onlyCurrentCustomer, operatorNo, statusFilter]);

  useEffect(() => {
    if (isOpen) {
      void loadTickets();
    }
  }, [isOpen, loadTickets]);

  const selectedTicket = useMemo(
    () => tickets.find((t) => t.ticket_no === selectedTicketNo) ?? null,
    [selectedTicketNo, tickets],
  );

  useEffect(() => {
    if (!selectedTicket) {
      return;
    }
    setSuccessBanner(null);
    setErrorBanner(null);
    setHandleResult(selectedTicket.handle_result ?? '');
    if (selectedTicket.ticket_status === 'submitted') {
      setTargetStatus('resolved');
    } else if (selectedTicket.ticket_status === 'processing') {
      setTargetStatus('resolved');
    } else {
      setTargetStatus(selectedTicket.ticket_status || 'resolved');
    }
  }, [selectedTicket]);

  if (!isOpen) {
    return null;
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedTicket) {
      return;
    }
    const cleanResult = handleResult.trim();
    if (!cleanResult) {
      setErrorBanner('请填写专席处理结果与客户反馈说明');
      return;
    }

    setSubmitting(true);
    setErrorBanner(null);
    setSuccessBanner(null);
    try {
      const res = await handleAdminTicket(selectedTicket.ticket_no, {
        ticket_status: targetStatus,
        handle_result: cleanResult,
        operator_no: operatorNo,
        notify_customer: notifyCustomer,
        push_to_chat: pushToChat,
      });
      const affectedCustomer =
        res.customer?.customer_no || selectedTicket.customer_no;
      setSuccessBanner(
        `工单 ${selectedTicket.ticket_no} 已更新为【${
          STATUS_META[targetStatus]?.label ?? targetStatus
        }】${pushToChat ? `，并已推送至客户 ${affectedCustomer} 对话窗` : ''}`,
      );
      await loadTickets();
      if (affectedCustomer) {
        onTicketHandled?.(affectedCustomer);
      }
    } catch (err) {
      setErrorBanner(err instanceof Error ? err.message : '工单提交处理失败');
    } finally {
      setSubmitting(false);
    }
  };

  const totalCount = Object.values(statusCounts).reduce((sum, n) => sum + n, 0);

  const panelBody = (
    <div
      className={
        fullPage
          ? 'w-full h-full bg-surface flex flex-col overflow-hidden'
          : 'w-full max-w-[1120px] h-[86vh] bg-surface border border-hairline rounded-[14px] shadow-ledger flex flex-col overflow-hidden'
      }
    >
      {/* 顶栏 */}
      <div className="px-4 py-3 border-b border-hairline flex flex-wrap items-center justify-between gap-3 shrink-0 bg-paper">
        <div className="flex items-center gap-2.5 min-w-0">
          <span className="inline-flex items-center justify-center w-7 h-7 rounded-[6px] bg-surface border border-hairline text-celadon shrink-0">
            <ClipboardList className="w-4 h-4" />
          </span>
          <div>
            <h2 className="font-serif text-[15px] font-semibold text-ink">
              中州银行 · 员工工单与投诉反馈处理台
            </h2>
            <p className="text-[11px] text-ink-2">
              专席受理投诉、建议及转人工跟进工单，处理结果实时同步站内通知与客户对话窗
            </p>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2 shrink-0">
          <label className="inline-flex items-center gap-1.5 text-[12px] text-ink-2 bg-surface border border-hairline rounded-[6px] px-2.5 py-1">
            <UserCheck className="w-3.5 h-3.5 text-celadon" />
            <span>经办专席：</span>
            <select
              value={operatorNo}
              onChange={(e) => setOperatorNo(e.target.value)}
              className="bg-transparent text-ink font-medium focus:outline-none"
            >
              {employees.map((emp) => (
                <option key={emp.employee_no} value={emp.employee_no}>
                  {emp.employee_name} ({emp.employee_no})
                </option>
              ))}
            </select>
          </label>

          {!fullPage ? (
            <a
              href="/?view=admin"
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-[6px] border border-hairline bg-surface text-[12px] text-ink-2 hover:text-ink hover:border-ink transition-colors"
            >
              <ExternalLink className="w-3.5 h-3.5" />
              <span>独立页面打开</span>
            </a>
          ) : (
            <a
              href="/"
              className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-[6px] border border-hairline bg-surface text-[12px] text-ink-2 hover:text-ink hover:border-ink transition-colors"
            >
              <span>返回客服柜台</span>
            </a>
          )}

          <button
            type="button"
            onClick={() => void loadTickets()}
            disabled={loading}
            className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-[6px] border border-hairline bg-surface text-[12px] text-ink-2 hover:text-ink hover:border-ink transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>刷新</span>
          </button>

          {!fullPage ? (
            <button
              type="button"
              onClick={onClose}
              aria-label="关闭员工工单台"
              className="p-1.5 rounded text-ink-2 hover:text-ink hover:bg-surface transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          ) : null}
        </div>
      </div>

      {/* 筛选栏 */}
      <div className="px-4 py-2.5 border-b border-hairline bg-surface flex flex-wrap items-center justify-between gap-3 shrink-0">
        <div className="flex flex-wrap items-center gap-1.5">
          {[
            { key: '', label: '全部', count: totalCount },
            { key: 'submitted', label: '待受理', count: statusCounts.submitted ?? 0 },
            { key: 'processing', label: '处理中', count: statusCounts.processing ?? 0 },
            { key: 'resolved', label: '已解决', count: statusCounts.resolved ?? 0 },
            { key: 'closed', label: '已完结', count: statusCounts.closed ?? 0 },
          ].map((tab) => {
            const active = statusFilter === tab.key;
            return (
              <button
                key={tab.key || 'all'}
                type="button"
                onClick={() => setStatusFilter(tab.key)}
                className={`px-2.5 py-1 rounded-[6px] text-[12px] border transition-colors inline-flex items-center gap-1.5 ${
                  active
                    ? 'bg-ink text-white border-ink'
                    : 'bg-paper text-ink-2 border-hairline hover:text-ink hover:border-ink'
                }`}
              >
                <span>{tab.label}</span>
                <span
                  className={`tabular-mono text-[10px] px-1 rounded ${
                    active ? 'bg-white/20 text-white' : 'bg-surface text-ink-2'
                  }`}
                >
                  {tab.count}
                </span>
              </button>
            );
          })}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <label className="inline-flex items-center gap-1.5 text-[12px] text-ink-2 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={onlyCurrentCustomer}
              onChange={(e) => setOnlyCurrentCustomer(e.target.checked)}
              className="accent-celadon"
            />
            <span>仅看当前客户 ({currentCustomerId})</span>
          </label>

          <form
            onSubmit={(e) => {
              e.preventDefault();
              setKeyword(searchInput.trim());
            }}
            className="flex items-center gap-1"
          >
            <div className="relative">
              <Search className="w-3.5 h-3.5 text-mist absolute left-2.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                placeholder="工单号 / 客户号 / 关键词"
                className="pl-7 pr-2.5 py-1 w-48 rounded-[6px] border border-hairline bg-paper text-[12px] text-ink placeholder:text-mist focus:outline-none focus:border-ink"
              />
            </div>
            <button
              type="submit"
              className="px-2.5 py-1 rounded-[6px] border border-hairline bg-paper text-[12px] text-ink hover:border-ink transition-colors"
            >
              筛选
            </button>
          </form>
        </div>
      </div>

      {/* 主体双栏 */}
      <div className="flex-1 min-h-0 flex flex-col md:flex-row bg-paper">
        {/* 左栏：工单队列 */}
        <div className="w-full md:w-[390px] shrink-0 border-b md:border-b-0 md:border-r border-hairline overflow-y-auto p-3 space-y-2">
          {tickets.length === 0 ? (
            <div className="py-12 text-center text-[12px] text-ink-2">
              {loading ? '正在加载工单队列...' : '当前筛选条件下暂无工单'}
            </div>
          ) : (
            tickets.map((tkt) => {
              const selected = tkt.ticket_no === selectedTicketNo;
              const meta = STATUS_META[tkt.ticket_status] ?? {
                label: tkt.ticket_status,
                badgeClass: 'bg-paper text-ink-2 border-hairline',
              };
              return (
                <button
                  key={tkt.ticket_no}
                  type="button"
                  onClick={() => setSelectedTicketNo(tkt.ticket_no)}
                  className={`w-full text-left p-3 rounded-[10px] border transition-colors space-y-1.5 ${
                    selected
                      ? 'bg-surface border-ink shadow-ledger'
                      : 'bg-surface/70 border-hairline hover:border-ink/60'
                  }`}
                >
                  <div className="flex items-center justify-between gap-2">
                    <span className="tabular-mono text-[11px] font-medium text-ink truncate">
                      {tkt.ticket_no}
                    </span>
                    <span
                      className={`px-1.5 py-0.5 rounded border text-[10px] font-medium shrink-0 ${meta.badgeClass}`}
                    >
                      {meta.label}
                    </span>
                  </div>
                  <div className="text-[13px] font-medium text-ink truncate">
                    [{tkt.ticket_type}] {tkt.ticket_title}
                  </div>
                  <div className="text-[11px] text-ink-2 line-clamp-2 leading-relaxed">
                    {tkt.ticket_content}
                  </div>
                  <div className="flex items-center justify-between text-[11px] text-mist pt-0.5">
                    <span>
                      {tkt.customer_name || '客户'} ({tkt.customer_no})
                    </span>
                    <span className="tabular-mono">
                      {tkt.submitted_at ? tkt.submitted_at.slice(0, 16) : '-'}
                    </span>
                  </div>
                </button>
              );
            })
          )}
        </div>

        {/* 右栏：工单详情与处理表单 */}
        <div className="flex-1 min-w-0 overflow-y-auto p-5">
          {errorBanner ? (
            <div className="mb-3 px-3 py-2 rounded-[8px] border border-seal/40 bg-seal/5 text-[12px] text-seal">
              {errorBanner}
            </div>
          ) : null}
          {successBanner ? (
            <div className="mb-3 px-3 py-2 rounded-[8px] border border-celadon/40 bg-celadon/10 text-[12px] text-celadon inline-flex items-center gap-1.5 w-full">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>{successBanner}</span>
            </div>
          ) : null}

          {!selectedTicket ? (
            <div className="h-full flex items-center justify-center text-[13px] text-ink-2">
              请从左侧队列选择一张工单进行受理与反馈
            </div>
          ) : (
            <form onSubmit={handleSubmit} className="space-y-4 max-w-[680px]">
              {/* 工单摘要卡片 */}
              <div className="bg-surface border border-hairline rounded-[12px] p-4 space-y-3">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <div>
                    <div className="tabular-mono text-[12px] text-ink-2">
                      工单编号：{selectedTicket.ticket_no}
                    </div>
                    <h3 className="font-serif text-[17px] font-semibold text-ink mt-0.5">
                      {selectedTicket.ticket_title}
                    </h3>
                  </div>
                  <span
                    className={`px-2 py-0.5 rounded border text-[11px] font-medium ${
                      (STATUS_META[selectedTicket.ticket_status] ?? STATUS_META.closed).badgeClass
                    }`}
                  >
                    {(STATUS_META[selectedTicket.ticket_status] ?? { label: selectedTicket.ticket_status }).label}
                  </span>
                </div>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[12px] bg-paper border border-hairline rounded-[8px] p-2.5">
                  <div>
                    <span className="text-[11px] text-ink-2 block">客户姓名</span>
                    <span className="text-ink font-medium">
                      {selectedTicket.customer_name || '-'}
                    </span>
                  </div>
                  <div>
                    <span className="text-[11px] text-ink-2 block">客户编号</span>
                    <span className="tabular-mono text-ink">{selectedTicket.customer_no}</span>
                  </div>
                  <div>
                    <span className="text-[11px] text-ink-2 block">问题类型</span>
                    <span className="text-ink">{selectedTicket.ticket_type}</span>
                  </div>
                  <div>
                    <span className="text-[11px] text-ink-2 block">当前专席</span>
                    <span className="text-ink">
                      {selectedTicket.assignee_name || selectedTicket.assignee_no || '待认领'}
                    </span>
                  </div>
                </div>

                <div>
                  <div className="text-[11px] text-ink-2 mb-1 font-medium">客户诉求详情</div>
                  <div className="bg-paper border border-hairline rounded-[8px] p-3 text-[13px] text-ink leading-relaxed whitespace-pre-wrap">
                    {selectedTicket.ticket_content}
                  </div>
                </div>

                {selectedTicket.feedback_no ? (
                  <div className="bg-celadon/5 border border-celadon/30 rounded-[8px] p-3 text-[12px] space-y-1">
                    <div className="flex items-center justify-between">
                      <span className="font-medium text-celadon">客户已确认并提交满意度反馈</span>
                      <span className="inline-flex items-center gap-0.5 text-amber font-medium">
                        <Star className="w-3.5 h-3.5 fill-amber" />
                        <span>{selectedTicket.satisfaction_score ?? 5} / 5 分</span>
                      </span>
                    </div>
                    <div className="text-ink-2">
                      评价内容：{selectedTicket.feedback_content || '已确认处理结果'}
                    </div>
                  </div>
                ) : null}
              </div>

              {/* 快捷处置模板 */}
              <div className="space-y-1.5">
                <div className="text-[12px] font-medium text-ink-2">常用专席处置话术模板</div>
                <div className="flex flex-wrap gap-1.5">
                  {QUICK_REPLY_TEMPLATES.map((tpl) => (
                    <button
                      key={tpl.label}
                      type="button"
                      onClick={() => {
                        setTargetStatus(tpl.status);
                        setHandleResult(tpl.content);
                      }}
                      className="px-2.5 py-1 rounded-full border border-hairline bg-surface text-[11px] text-ink-2 hover:text-ink hover:border-ink transition-colors"
                    >
                      {tpl.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* 处置动作与内容 */}
              <div className="bg-surface border border-hairline rounded-[12px] p-4 space-y-3">
                <div className="flex flex-wrap items-center gap-3">
                  <span className="text-[12px] font-medium text-ink">处理后状态：</span>
                  {[
                    { value: 'processing', label: '处理中' },
                    { value: 'resolved', label: '已解决' },
                    { value: 'closed', label: '已完结' },
                    { value: 'rejected', label: '驳回/退回' },
                  ].map((opt) => (
                    <label
                      key={opt.value}
                      className="inline-flex items-center gap-1.5 text-[12px] text-ink cursor-pointer"
                    >
                      <input
                        type="radio"
                        name="ticketStatus"
                        value={opt.value}
                        checked={targetStatus === opt.value}
                        onChange={(e) => setTargetStatus(e.target.value)}
                        className="accent-celadon"
                      />
                      <span>{opt.label}</span>
                    </label>
                  ))}
                </div>

                <div>
                  <label className="block text-[12px] font-medium text-ink mb-1">
                    专席处理结果与客户反馈内容
                  </label>
                  <textarea
                    rows={4}
                    value={handleResult}
                    onChange={(e) => setHandleResult(e.target.value)}
                    placeholder="请填写具体核查结论、资金退还/调账说明或后续指引，提交后将发送给客户..."
                    className="w-full rounded-[8px] border border-hairline bg-paper px-3 py-2 text-[13px] text-ink placeholder:text-mist focus:outline-none focus:border-ink"
                  />
                </div>

                <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
                  <div className="flex flex-wrap items-center gap-4 text-[12px] text-ink-2">
                    <label className="inline-flex items-center gap-1.5 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={pushToChat}
                        onChange={(e) => setPushToChat(e.target.checked)}
                        className="accent-celadon"
                      />
                      <span>同步推送回执至客户对话窗</span>
                    </label>
                    <label className="inline-flex items-center gap-1.5 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={notifyCustomer}
                        onChange={(e) => setNotifyCustomer(e.target.checked)}
                        className="accent-celadon"
                      />
                      <span>写入客户站内消息通知</span>
                    </label>
                  </div>

                  <button
                    type="submit"
                    disabled={submitting}
                    className="inline-flex items-center gap-1.5 px-4 py-2 rounded-[8px] bg-celadon text-white text-[13px] font-medium hover:opacity-90 disabled:opacity-50 transition-opacity"
                  >
                    <Send className="w-3.5 h-3.5" />
                    <span>{submitting ? '正在提交...' : '提交处理并反馈客户'}</span>
                  </button>
                </div>
              </div>
            </form>
          )}
        </div>
      </div>
    </div>
  );

  if (fullPage) {
    return <div className="h-screen w-screen bg-paper">{panelBody}</div>;
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 backdrop-blur-[1px] p-4"
      role="dialog"
      aria-modal="true"
      aria-label="员工工单与投诉反馈处理台"
    >
      {panelBody}
    </div>
  );
};
