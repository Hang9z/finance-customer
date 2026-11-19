import { ReceiptData, TransactionRow } from '../types/chat';

const BALANCE_RE =
  /账户\s*(\S+)\s*当前可用余额为\s*([\d,.]+)\s*(\w+)，冻结金额为\s*([\d,.]+)\s*\w+，账户状态：([^。]+)/;

const TX_HEADER_RE =
  /已为您查询到账户\s*(\S+)\s*的近期交易记录（共\s*(\d+)\s*笔[^）]*）[：:]?/;

const TX_LINE_RE =
  /^\d+\.\s*\[([^\]]+)\]\s+(\S+)\s+([\d,.]+)\s+(\S+)\s*\|\s*对象：([^|]+?)\s*\|\s*状态：(.+)$/;

const LOAN_RE =
  /申请编号为【(\w+)】，申请金额\s*([\d.]+)\s*元，期限\s*(\d+)\s*个月，当前状态为【(\w+)】/;

const TICKET_RE = /工单编号为【(\w+)】（问题类型：(.+?)）/;

const CARD_LOSS_RE = /【(\w+)】已成功办理紧急挂失（状态：(\w+)）/;

const LOAN_PROGRESS_RE =
  /贷款申请编号【(\w+)】申请金额\s*([\d,.]+)\s*元，期限\s*(\d+)\s*个月，当前审批状态为【([^】]+)】(?:，提交时间：([^。]+))?/;

const TICKET_PROGRESS_RE =
  /工单编号【(\w+)】（问题类型：(.+?)）当前处理状态为【([^】]+)】(?:，负责专席：([^，。]+))?(?:，提交时间：([^。]+))?/;

const CREDIT_TYPES = new Set([
  'deposit',
  'refund',
  'loan_disbursement',
  'wealth_redeem',
  'income_settle',
  'adjustment_credit',
]);

const TX_TYPE_LABELS: Record<string, string> = {
  payment: '消费',
  transfer: '转账',
  wealth_purchase: '理财申购',
  wealth_redeem: '理财赎回',
  loan_repayment: '贷款还款',
  loan_disbursement: '贷款放款',
  deposit: '存入',
  refund: '退款',
  income_settle: '收益结算',
  adjustment_credit: '调账入账',
  adjustment_debit: '调账扣款',
  fee: '手续费',
  withdrawal: '取现',
};

export function formatCardNoDisplay(rawId: string): string {
  const clean = rawId.replace(/\s+/g, '');
  if (clean.length <= 4) {
    return clean;
  }
  return clean.replace(/(.{4})(?=.)/g, '$1 ');
}

export function formatTimestampLabel(): string {
  const now = new Date();
  const hh = String(now.getHours()).padStart(2, '0');
  const mm = String(now.getMinutes()).padStart(2, '0');
  return `${hh}:${mm}`;
}

export interface ParsedReceiptsResult {
  cleanMarkdown: string;
  receipts: ReceiptData[];
  discoveredTickets: Array<{ ticketNo: string; category: string }>;
}

export function parseReceiptsAndCleanMarkdown(
  rawText: string,
  baseId: string,
): ParsedReceiptsResult {
  const receipts: ReceiptData[] = [];
  const discoveredTickets: Array<{ ticketNo: string; category: string }> = [];
  const createdAt = formatTimestampLabel();
  let cleanMarkdown = rawText;

  // 1. 余额回单
  const balMatch = BALANCE_RE.exec(rawText);
  if (balMatch) {
    receipts.push({
      id: `${baseId}_bal`,
      kind: 'balance',
      title: '余额回单',
      sealText: '已核验',
      accountNo: balMatch[1],
      availableBalance: balMatch[2],
      currency: balMatch[3],
      frozenAmount: balMatch[4],
      accountStatus: balMatch[5].trim(),
      createdAt,
    });
  }

  // 2. 交易流水单
  const txHeaderMatch = TX_HEADER_RE.exec(rawText);
  if (txHeaderMatch) {
    const lines = rawText.split(/\r?\n/);
    const rows: TransactionRow[] = [];
    const remainingLines: string[] = [];

    for (const line of lines) {
      const lineMatch = TX_LINE_RE.exec(line.trim());
      if (lineMatch) {
        const typeRaw = lineMatch[2].trim();
        rows.push({
          time: lineMatch[1].trim(),
          typeRaw,
          typeLabel: TX_TYPE_LABELS[typeRaw] ?? typeRaw,
          amount: lineMatch[3].trim(),
          currency: lineMatch[4].trim(),
          isCredit: CREDIT_TYPES.has(typeRaw),
          counterparty: lineMatch[5].trim(),
          status: lineMatch[6].trim(),
        });
      } else {
        remainingLines.push(line);
      }
    }

    if (rows.length > 0) {
      receipts.push({
        id: `${baseId}_tx`,
        kind: 'transactions',
        title: '交易流水单',
        sealText: '已核验',
        accountNo: txHeaderMatch[1],
        totalCount: Number.parseInt(txHeaderMatch[2], 10),
        rows,
        createdAt,
      });
      // Markdown 原列表不再重复显示，只保留首行说明
      cleanMarkdown = remainingLines.join('\n').trim();
    }
  }

  // 3. 贷款受理单
  const loanMatch = LOAN_RE.exec(rawText);
  if (loanMatch) {
    receipts.push({
      id: `${baseId}_loan`,
      kind: 'loan',
      title: '贷款受理单',
      sealText: '已受理',
      applicationNo: loanMatch[1],
      amount: loanMatch[2],
      termMonths: loanMatch[3],
      status: loanMatch[4],
      createdAt,
    });
  }

  // 4. 工单回执
  const ticketMatch = TICKET_RE.exec(rawText);
  if (ticketMatch) {
    const ticketNo = ticketMatch[1];
    const category = ticketMatch[2].trim();
    receipts.push({
      id: `${baseId}_tkt`,
      kind: 'ticket',
      title: '工单回执',
      sealText: '已登记',
      ticketNo,
      category,
      createdAt,
    });
    discoveredTickets.push({ ticketNo, category });
  }

  // 5. 挂失确认书
  const lossMatch = CARD_LOSS_RE.exec(rawText);
  if (lossMatch) {
    receipts.push({
      id: `${baseId}_loss`,
      kind: 'card_loss',
      title: '挂失确认书',
      sealText: '已止付',
      cardNo: lossMatch[1],
      status: lossMatch[2],
      createdAt,
    });
  }

  // 6. 贷款进度回执
  const loanProgressMatch = LOAN_PROGRESS_RE.exec(rawText);
  if (loanProgressMatch) {
    receipts.push({
      id: `${baseId}_loan_prog`,
      kind: 'loan_progress',
      title: '贷款进度回执',
      sealText: '已核验',
      applicationNo: loanProgressMatch[1],
      amount: loanProgressMatch[2],
      termMonths: loanProgressMatch[3],
      status: loanProgressMatch[4],
      submittedAt: (loanProgressMatch[5] ?? '-').trim(),
      createdAt,
    });
  }

  // 7. 工单进度回执
  const ticketProgressMatch = TICKET_PROGRESS_RE.exec(rawText);
  if (ticketProgressMatch) {
    receipts.push({
      id: `${baseId}_tkt_prog`,
      kind: 'ticket_progress',
      title: '工单进度回执',
      sealText: '已核验',
      ticketNo: ticketProgressMatch[1],
      category: ticketProgressMatch[2].trim(),
      status: ticketProgressMatch[3],
      handlerName: (ticketProgressMatch[4] ?? '专席客服').trim(),
      submittedAt: (ticketProgressMatch[5] ?? '-').trim(),
      createdAt,
    });
  }

  return { cleanMarkdown, receipts, discoveredTickets };
}
