import React from 'react';
import {
  CreditCard,
  FileText,
  Landmark,
  ListOrdered,
  MessageSquareWarning,
  Wallet,
} from 'lucide-react';

interface EmptyStateProps {
  disabled?: boolean;
  onSelectPrompt: (prompt: string) => void;
}

const WELCOME_CARDS = [
  {
    id: 'balance',
    title: '账户余额查询',
    prompt: '帮我查一下银行账户余额',
    icon: Wallet,
  },
  {
    id: 'transactions',
    title: '交易明细查询',
    prompt: '帮我查询账户 ACC0000000001 最近的交易流水',
    icon: ListOrdered,
  },
  {
    id: 'loan',
    title: '消费贷款申请',
    prompt: '我要申请消费贷款',
    icon: Landmark,
  },
  {
    id: 'loss',
    title: '信用卡挂失',
    prompt: '我的银行卡丢了，要办理紧急挂失',
    icon: CreditCard,
  },
  {
    id: 'ticket',
    title: '投诉建议工单',
    prompt: '我要投诉扣费异常，今天凌晨账户被莫名扣除了 20 元服务费',
    icon: MessageSquareWarning,
  },
  {
    id: 'wealth',
    title: '金融产品咨询',
    prompt: '你们有哪些稳健型的理财产品？收益率多少？',
    icon: FileText,
  },
];

export const EmptyState: React.FC<EmptyStateProps> = ({
  disabled = false,
  onSelectPrompt,
}) => {
  return (
    <div className="py-10 md:py-14 flex flex-col items-center">
      <div className="text-center max-w-[520px] space-y-2 mb-8">
        <span className="micro-label text-ink-2">ZHONGZHOU BANK · COUNTER</span>
        <h2 className="font-serif text-[24px] font-semibold tracking-tight text-ink">
          您好，欢迎来到智能柜台
        </h2>
        <p className="text-[14px] text-ink-2">
          可为您办理账户余额、交易流水、消费贷款、卡片挂失与投诉登记，亦支持实时产品与费率政策咨询。
        </p>
      </div>

      <div className="w-full grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {WELCOME_CARDS.map((item) => {
          const Icon = item.icon;
          return (
            <button
              key={item.id}
              type="button"
              disabled={disabled}
              onClick={() => onSelectPrompt(item.prompt)}
              className="group text-left bg-surface border border-hairline rounded-[8px] p-4 transition-all duration-150 hover:border-ink hover:-translate-y-[1px] disabled:opacity-50"
            >
              <div className="flex items-center gap-2 text-ink mb-2">
                <Icon className="w-4 h-4 text-ink-2 group-hover:text-ink transition-colors" />
                <span className="text-[14px] font-medium">{item.title}</span>
              </div>
              <p className="text-[12px] text-ink-2 line-clamp-2 leading-relaxed">
                {item.prompt}
              </p>
            </button>
          );
        })}
      </div>
    </div>
  );
};
