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

const CARD_LOSS_RE = /【([\w*]+)】已成功办理紧急挂失（状态：(\w+)）/;

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

const MASKED_PAN_RE = /^(\d{4})\*+(\d{4})$/;

export function formatCardNoDisplay(rawId: string): string {
  const clean = rawId.replace(/[\s-]+/g, '');
  if (!clean) {
    return '';
  }
  const maskedMatch = MASKED_PAN_RE.exec(clean);
  if (maskedMatch) {
    return `${maskedMatch[1]} **** **** ${maskedMatch[2]}`;
  }
  if (/^\d{12,19}$/.test(clean)) {
    return `${clean.slice(0, 4)} **** **** ${clean.slice(-4)}`;
  }
  if (clean.startsWith('ACC') && clean.length >= 10 && !clean.includes('*')) {
    return `${clean.slice(0, 3)}****${clean.slice(-4)}`;
  }
  return clean;
}

function readStr(obj: Record<string, unknown>, key: string, fallback = ''): string {
  const val = obj[key];
  return typeof val === 'string' || typeof val === 'number' ? String(val) : fallback;
}

export function normalizeServerReceipt(
  raw: Record<string, unknown> | null | undefined,
  id: string,
): ReceiptData | null {
  if (!raw || typeof raw !== 'object') {
    return null;
  }
  const kind = readStr(raw, 'kind');
  const createdAt = readStr(raw, 'createdAt') || formatTimestampLabel();

  if (kind === 'balance') {
    return {
      id,
      kind: 'balance',
      title: '余额回单',
      sealText: '已核验',
      accountNo: readStr(raw, 'accountNo'),
      availableBalance: readStr(raw, 'availableBalance', '0.00'),
      currency: readStr(raw, 'currency', 'CNY'),
      frozenAmount: readStr(raw, 'frozenAmount', '0.00'),
      accountStatus: readStr(raw, 'accountStatus', '正常'),
      createdAt,
    };
  }
  if (kind === 'transactions') {
    const rawRows = Array.isArray(raw.rows) ? raw.rows : [];
    const rows: TransactionRow[] = rawRows
      .filter((item): item is Record<string, unknown> => Boolean(item && typeof item === 'object'))
      .map((item) => {
        const typeRaw = readStr(item, 'typeRaw', 'payment');
        return {
          time: readStr(item, 'time', '-'),
          typeRaw,
          typeLabel: readStr(item, 'typeLabel') || TX_TYPE_LABELS[typeRaw] || typeRaw,
          amount: readStr(item, 'amount', '0.00'),
          currency: readStr(item, 'currency', 'CNY'),
          isCredit: typeof item.isCredit === 'boolean' ? item.isCredit : CREDIT_TYPES.has(typeRaw),
          counterparty: readStr(item, 'counterparty', '-'),
          status: readStr(item, 'status', '-'),
        };
      });
    return {
      id,
      kind: 'transactions',
      title: '交易流水单',
      sealText: '已核验',
      accountNo: readStr(raw, 'accountNo'),
      totalCount: typeof raw.totalCount === 'number' ? raw.totalCount : rows.length,
      rows,
      createdAt,
    };
  }
  if (kind === 'loan') {
    return {
      id,
      kind: 'loan',
      title: '贷款受理单',
      sealText: '已受理',
      applicationNo: readStr(raw, 'applicationNo'),
      amount: readStr(raw, 'amount', '0.00'),
      termMonths: readStr(raw, 'termMonths', '-'),
      status: readStr(raw, 'status', 'submitted'),
      createdAt,
    };
  }
  if (kind === 'ticket') {
    return {
      id,
      kind: 'ticket',
      title: '工单回执',
      sealText: '已登记',
      ticketNo: readStr(raw, 'ticketNo'),
      category: readStr(raw, 'category', '客服工单'),
      createdAt,
    };
  }
  if (kind === 'card_loss') {
    return {
      id,
      kind: 'card_loss',
      title: '挂失确认书',
      sealText: '已止付',
      cardNo: readStr(raw, 'cardNo'),
      status: readStr(raw, 'status', 'loss_reported'),
      createdAt,
    };
  }
  if (kind === 'loan_progress') {
    return {
      id,
      kind: 'loan_progress',
      title: '贷款进度回执',
      sealText: '已核验',
      applicationNo: readStr(raw, 'applicationNo'),
      amount: readStr(raw, 'amount', '0.00'),
      termMonths: readStr(raw, 'termMonths', '-'),
      status: readStr(raw, 'status', '-'),
      submittedAt: readStr(raw, 'submittedAt', '-'),
      createdAt,
    };
  }
  if (kind === 'ticket_progress') {
    const rawTitle = readStr(raw, 'title');
    return {
      id,
      kind: 'ticket_progress',
      title: rawTitle === '专席反馈凭证' ? '专席反馈凭证' : '工单进度回执',
      sealText: readStr(raw, 'sealText') || '已核验',
      ticketNo: readStr(raw, 'ticketNo'),
      category: readStr(raw, 'category', '客服工单'),
      status: readStr(raw, 'status', '-'),
      handlerName: readStr(raw, 'handlerName', '专席客服'),
      processResult: readStr(raw, 'processResult'),
      submittedAt: readStr(raw, 'submittedAt', '-'),
      handledAt: readStr(raw, 'handledAt'),
      createdAt,
    };
  }
  if (kind === 'credit_limit') {
    const rawItems = Array.isArray(raw.items) ? raw.items : [];
    const items = rawItems
      .filter((item): item is Record<string, unknown> => Boolean(item && typeof item === 'object'))
      .map((item) => ({
        limitNo: readStr(item, 'limitNo', '-'),
        productCode: readStr(item, 'productCode', 'LOAN'),
        totalAmount: readStr(item, 'totalAmount', '0.00'),
        availableAmount: readStr(item, 'availableAmount', '0.00'),
        frozenAmount: readStr(item, 'frozenAmount', '0.00'),
        validTo: readStr(item, 'validTo', '-'),
      }));
    return {
      id,
      kind: 'credit_limit',
      title: '授信额度凭证',
      sealText: '已核验',
      customerNo: readStr(raw, 'customerNo'),
      items,
      createdAt,
    };
  }
  if (kind === 'repayment_plan') {
    const rawBills = Array.isArray(raw.bills) ? raw.bills : [];
    const bills = rawBills
      .filter((item): item is Record<string, unknown> => Boolean(item && typeof item === 'object'))
      .map((item) => ({
        billNo: readStr(item, 'billNo', '-'),
        outstandingAmount: readStr(item, 'outstandingAmount', '0.00'),
        paidAmount: readStr(item, 'paidAmount', '0.00'),
        status: readStr(item, 'status', '待还款'),
      }));
    return {
      id,
      kind: 'repayment_plan',
      title: '还款账单凭证',
      sealText: '已核验',
      scopeLabel: readStr(raw, 'scopeLabel'),
      billCount: typeof raw.billCount === 'number' ? raw.billCount : bills.length,
      overdueCount: typeof raw.overdueCount === 'number' ? raw.overdueCount : 0,
      bills,
      createdAt,
    };
  }
  if (kind === 'loan_repayment') {
    return {
      id,
      kind: 'loan_repayment',
      title: '贷款还款回执',
      sealText: '已入账',
      repaymentNo: readStr(raw, 'repaymentNo'),
      billNo: readStr(raw, 'billNo'),
      accountNo: readStr(raw, 'accountNo'),
      amount: readStr(raw, 'amount', '0.00'),
      status: readStr(raw, 'status', 'success'),
      createdAt,
    };
  }
  return null;
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
