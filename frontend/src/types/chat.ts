export type ObjectCardType =
  | 'account'
  | 'card'
  | 'loan_product'
  | 'loan_application'
  | 'loan_contract'
  | 'repayment_bill'
  | 'wealth_product'
  | 'transaction'
  | 'ticket';

export interface ChatObject {
  type: string;
  id: string;
  title?: string | null;
  attributes?: Record<string, unknown>;
}

export interface ChatRequest {
  sender_id: string;
  text?: string | null;
  object?: ChatObject | null;
  message_id?: string | null;
}

export interface QuickReplyOption {
  label: string;
  value: string;
  variant?: 'primary' | 'danger' | 'secondary';
}

export interface KnowledgeCitation {
  source: string;
  section?: string;
  score?: number | null;
  sourceType?: string;
  url?: string;
  snippet?: string;
}

export interface RagStatusResponse {
  enabled: boolean;
  query_online: boolean;
  import_online: boolean;
  query_url: string;
  chat_url: string;
  import_url: string;
}

export interface ChatMessage {
  text?: string | null;
  object?: ChatObject | null;
  receipt?: Record<string, unknown> | null;
  event?: TaskEventInfo | null;
  citations?: KnowledgeCitation[] | null;
}

export interface ServerWorkflowActive {
  flowId: string;
  flowName: string;
  stepId?: string | null;
  awaiting: string | null;
  awaitingSlot?: string | null;
  awaitingQuestion: string | null;
  awaitingConfirmation?: boolean;
  riskLevel?: string | null;
}

export interface ServerPausedTask {
  taskId: string;
  flowId: string;
  flowName: string;
}

export interface ServerWorkflowState {
  active: ServerWorkflowActive | null;
  paused: ServerPausedTask[];
  source?: 'server' | 'inferred';
}

export interface ChatResponse {
  sender_id: string;
  message_id: string;
  messages: ChatMessage[];
  workflow_state?: ServerWorkflowState | null;
  quick_replies?: QuickReplyOption[];
}

export interface HistoryMessageItem {
  role: 'user' | 'bot';
  text?: string | null;
  object?: ChatObject | null;
  receipt?: Record<string, unknown> | null;
  event?: TaskEventInfo | null;
  citations?: KnowledgeCitation[] | null;
}

export interface HistoryResponse {
  sender_id: string;
  messages: HistoryMessageItem[];
  workflow_state?: ServerWorkflowState | null;
  quick_replies?: QuickReplyOption[];
}

export interface CustomerAssetAccount {
  account_no: string;
  masked_account_no: string;
  balance_amount: string;
  currency_code: string;
  account_product?: {
    product_code?: string;
    product_name?: string;
  };
}

export interface CustomerCreditLimit {
  limit_no: string;
  product_code: string;
  total_limit_amount: string;
  available_limit_amount: string;
  frozen_limit_amount: string;
  valid_to: string;
}

export interface CustomerAssetsResponse {
  customer_no: string;
  customer_name?: string | null;
  risk_level?: {
    risk_level_code?: string;
    risk_level_name?: string;
  } | null;
  accounts: CustomerAssetAccount[];
  credit_limits: CustomerCreditLimit[];
  wealth_positions: Array<Record<string, unknown>>;
  synced: boolean;
}

export type ServiceHealthStatus = 'checking' | 'online' | 'offline';

export interface TaskEventInfo {
  kind: 'start' | 'switch' | 'resume' | 'cancel';
  flow: string;
  previousFlow?: string;
  rawText: string;
}

export interface WorkflowActiveState {
  flowId?: string;
  flowName: string;
  awaiting: string | null;
  awaitingSlot?: string | null;
  awaitingQuestion: string | null;
  awaitingConfirmation?: boolean;
  riskLevel?: string | null;
}

export interface WorkflowState {
  active: WorkflowActiveState | null;
  paused: string[];
  source?: 'server' | 'inferred';
}

export interface TransactionRow {
  time: string;
  typeRaw: string;
  typeLabel: string;
  amount: string;
  currency: string;
  isCredit: boolean;
  counterparty: string;
  status: string;
}

export type ReceiptData =
  | {
      id: string;
      kind: 'balance';
      title: '余额回单';
      sealText: '已核验';
      accountNo: string;
      availableBalance: string;
      currency: string;
      frozenAmount: string;
      accountStatus: string;
      createdAt: string;
    }
  | {
      id: string;
      kind: 'transactions';
      title: '交易流水单';
      sealText: '已核验';
      accountNo: string;
      totalCount: number;
      rows: TransactionRow[];
      createdAt: string;
    }
  | {
      id: string;
      kind: 'loan';
      title: '贷款受理单';
      sealText: '已受理';
      applicationNo: string;
      amount: string;
      termMonths: string;
      status: string;
      createdAt: string;
    }
  | {
      id: string;
      kind: 'ticket';
      title: '工单回执';
      sealText: '已登记';
      ticketNo: string;
      category: string;
      createdAt: string;
    }
  | {
      id: string;
      kind: 'card_loss';
      title: '挂失确认书';
      sealText: '已止付';
      cardNo: string;
      status: string;
      createdAt: string;
    }
  | {
      id: string;
      kind: 'loan_progress';
      title: '贷款进度回执';
      sealText: '已核验';
      applicationNo: string;
      amount: string;
      termMonths: string;
      status: string;
      submittedAt: string;
      createdAt: string;
    }
  | {
      id: string;
      kind: 'ticket_progress';
      title: '工单进度回执';
      sealText: '已核验';
      ticketNo: string;
      category: string;
      status: string;
      handlerName: string;
      submittedAt: string;
      createdAt: string;
    }
  | {
      id: string;
      kind: 'credit_limit';
      title: '授信额度凭证';
      sealText: '已核验';
      customerNo: string;
      items: Array<{
        limitNo: string;
        productCode: string;
        totalAmount: string;
        availableAmount: string;
        frozenAmount: string;
        validTo: string;
      }>;
      createdAt: string;
    }
  | {
      id: string;
      kind: 'repayment_plan';
      title: '还款账单凭证';
      sealText: '已核验';
      scopeLabel: string;
      billCount: number;
      overdueCount: number;
      bills: Array<{
        billNo: string;
        outstandingAmount: string;
        paidAmount: string;
        status: string;
      }>;
      createdAt: string;
    }
  | {
      id: string;
      kind: 'loan_repayment';
      title: '贷款还款回执';
      sealText: '已入账';
      repaymentNo: string;
      billNo: string;
      accountNo: string;
      amount: string;
      status: string;
      createdAt: string;
    };

export type TimelineItem =
  | {
      id: string;
      kind: 'user';
      messageId: string;
      text?: string | null;
      object?: ChatObject | null;
      status?: 'sent' | 'failed';
    }
  | {
      id: string;
      kind: 'event';
      event: TaskEventInfo;
    }
  | {
      id: string;
      kind: 'bot';
      text: string;
      receipts: ReceiptData[];
      citations?: KnowledgeCitation[];
      streaming?: boolean;
    };

export interface WalletCard {
  type: ObjectCardType | string;
  id: string;
  title: string;
  attributes: Record<string, string>;
  questionPrompt: string;
  isSessionTicket?: boolean;
}

export interface CustomerPreset {
  id: string;
  name: string;
  subtitle: string;
  cards: WalletCard[];
}

export interface ScenarioPromptItem {
  id: string;
  title: string;
  prompt: string;
  description: string;
}
