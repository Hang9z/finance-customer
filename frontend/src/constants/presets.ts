import { CustomerPreset, ScenarioPromptItem, WalletCard } from '../types/chat';

export const DEFAULT_CUSTOMER_ID = 'CUS00000001';
export const STORAGE_CUSTOMER_KEY = 'zhongzhou_active_customer_id';

export const OBJECT_SLOT_MAP: Record<string, string> = {
  account: 'account_no / card_no',
  card: 'card_no / account_no',
  loan_product: 'product_code',
  wealth_product: 'product_code',
  transaction: 'related_no',
  ticket: 'ticket_no / related_no',
  order: 'order_number',
  product: 'product_id',
};

export const COMMON_WEALTH_CARDS: WalletCard[] = [
  {
    type: 'wealth_product',
    id: 'WM_CASH_01',
    title: '中州现金管理01号',
    attributes: {
      riskLevel: 'R1',
      expectedYield: '1.83%–2.40%',
      redemption: 'T+1',
    },
    questionPrompt: '请介绍一下中州现金管理01号（WM_CASH_01）的收益率和赎回规则。',
  },
  {
    type: 'wealth_product',
    id: 'WM_FIXED_90_01',
    title: '中州90天固定收益01号',
    attributes: {
      riskLevel: 'R2',
      expectedYield: '3.23%–3.80%',
      term: '90 天',
    },
    questionPrompt: '请介绍一下中州90天固定收益01号（WM_FIXED_90_01）的风险等级与预期收益。',
  },
];

export const CUSTOMER_PRESETS: CustomerPreset[] = [
  {
    id: 'CUS00000001',
    name: '陈清远',
    subtitle: '储蓄与理财客户 · 持有活期与副账户',
    cards: [
      {
        type: 'account',
        id: 'ACC0000000001',
        title: '人民币活期结算账户',
        attributes: {
          balance: '2,125.00 CNY',
          status: '正常',
          product: 'ACC_DEMAND_CNY',
        },
        questionPrompt: '帮我查询账户 ACC0000000001 的余额和近期交易流水。',
      },
      {
        type: 'account',
        id: 'ACC0000049001',
        title: '个人储蓄副账户',
        attributes: {
          balance: '2,125.00 CNY',
          status: '正常',
        },
        questionPrompt: '帮我查询个人储蓄副账户 ACC0000049001 的余额。',
      },
      {
        type: 'transaction',
        id: 'TXN202611180001',
        title: '理财申购扣款 · 中州银行',
        attributes: {
          amount: '-1,001.00 CNY',
          time: '2026-11-18 10:00',
        },
        questionPrompt: '我想核实一笔交易记录 TXN202611180001（理财申购扣款 1,001.00 CNY）。',
      },
      {
        type: 'transaction',
        id: 'TXN202611170002',
        title: '商户消费转账 · 中州合作商户',
        attributes: {
          amount: '-23.00 CNY',
          time: '2026-11-17 10:00',
        },
        questionPrompt: '请帮我核查这笔商户消费转账 TXN202611170002。',
      },
    ],
  },
  {
    id: 'CUS00000031',
    name: '林致远',
    subtitle: '授信客户 · 额度 LMT0000000031（可用 255,000.00 CNY）',
    cards: [
      {
        type: 'account',
        id: 'ACC0000000031',
        title: '授信客户结算账户',
        attributes: {
          balance: '正常可用',
          status: '正常',
          limitNo: 'LMT0000000031',
        },
        questionPrompt: '帮我查一下账户 ACC0000000031 的余额。',
      },
      {
        type: 'loan_product',
        id: 'LOAN_BUSINESS_ECOM',
        title: '电商经营贷',
        attributes: {
          rate: '4.5%–12.0%',
          amountRange: '3万–120万',
          termRange: '3–36 期',
        },
        questionPrompt: '我要申请 50000 元贷款，分 12 期',
      },
      {
        type: 'loan_product',
        id: 'LOAN_CONSUMER_STD',
        title: '标准消费信用贷',
        attributes: {
          rate: '4.8%–10.8%',
          amountRange: '3千–30万',
          termRange: '3–36 期',
        },
        questionPrompt: '标准消费信用贷 LOAN_CONSUMER_STD 的利率和期限条件是什么？',
      },
    ],
  },
  {
    id: 'CUS00000002',
    name: '周砚书',
    subtitle: '挂失测试客户 · 持有中州银行标准白金卡',
    cards: [
      {
        type: 'card',
        id: 'ACC0000000002',
        title: '中州银行标准白金卡',
        attributes: {
          balance: '2,250.00 CNY',
          status: '正常',
        },
        questionPrompt: '我的中州银行标准白金卡 ACC0000000002 丢了，要办理紧急挂失。',
      },
    ],
  },
];

export const BUSINESS_SCENARIOS: ScenarioPromptItem[] = [
  {
    id: 'balance',
    title: '账户余额查询',
    prompt: '帮我查一下银行账户余额',
    description: '发起查余额流程，随后可递交账户卡片自动填槽',
  },
  {
    id: 'transactions',
    title: '交易明细查询',
    prompt: '帮我查询账户 ACC0000000001 最近的交易流水',
    description: '拉取中台实时流水明细并生成精排流水凭证',
  },
  {
    id: 'loan',
    title: '消费贷款申请',
    prompt: '我要申请消费贷款',
    description: '多轮收集贷款金额、还款期数并提交中台进件',
  },
  {
    id: 'card_loss',
    title: '银行卡紧急挂失',
    prompt: '我的银行卡丢了，要办理紧急挂失',
    description: '收集卡号与挂失原因，即时止付并出具确认书',
  },
  {
    id: 'ticket',
    title: '投诉建议工单',
    prompt: '我要投诉扣费异常，今天凌晨账户被莫名扣除了 20 元服务费',
    description: '登记投诉分类与事实描述，生成支持工单回执',
  },
];

export const KNOWLEDGE_SCENARIOS: ScenarioPromptItem[] = [
  {
    id: 'wealth_consult',
    title: '稳健理财咨询',
    prompt: '你们有哪些稳健型的理财产品？收益率多少？',
    description: '实时检索在售 R1/R2 理财产品目录与风险提示',
  },
  {
    id: 'credit_card_compare',
    title: '信用卡权益对比',
    prompt: '信用卡金卡和白金卡年费和权益有什么区别？',
    description: '对比年费减免条件、授信区间及商旅权益规则',
  },
  {
    id: 'prepay_policy',
    title: '提前还款政策',
    prompt: '贷款提前还款有什么政策？收违约金吗？',
    description: '解答消费贷与分期贷提前结清规则及费率标准',
  },
];

export function buildDemoScriptSteps(accountId: string): string[] {
  const safeAccount = accountId || 'ACC0000000001';
  return [
    '我要申请消费贷款',
    '50000',
    `先帮我查一下 ${safeAccount} 的余额`,
    '继续刚才的贷款申请',
    '12期',
  ];
}
