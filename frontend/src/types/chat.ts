export type ObjectCardType =
  | 'account'
  | 'card'
  | 'loan_product'
  | 'loan_application'
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

export interface ChatMessage {
  text?: string | null;
  object?: ChatObject | null;
}

export interface ChatResponse {
  sender_id: string;
  message_id: string;
  messages: ChatMessage[];
}

export interface HistoryMessageItem {
  role: 'user' | 'bot';
  text?: string | null;
  object?: ChatObject | null;
}

export interface HistoryResponse {
  sender_id: string;
  messages: HistoryMessageItem[];
}

export type ServiceHealthStatus = 'checking' | 'online' | 'offline';

export interface TaskEventInfo {
  kind: 'start' | 'switch' | 'resume' | 'cancel';
  flow: string;
  previousFlow?: string;
  rawText: string;
}

export interface WorkflowActiveState {
  flowName: string;
  awaiting: string | null;
  awaitingQuestion: string | null;
}

export interface WorkflowState {
  active: WorkflowActiveState | null;
  paused: string[];
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
