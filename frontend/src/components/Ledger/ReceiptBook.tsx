import React from 'react';
import { FileCheck2 } from 'lucide-react';
import { ReceiptData } from '../../types/chat';
import { ReceiptCard } from '../receipts/ReceiptCard';

interface ReceiptBookProps {
  receipts: ReceiptData[];
}

export const ReceiptBook: React.FC<ReceiptBookProps> = ({ receipts }) => {
  if (receipts.length === 0) {
    return (
      <div className="py-12 px-4 text-center space-y-2 border border-dashed border-hairline rounded-[8px] bg-paper/50">
        <FileCheck2 className="w-6 h-6 text-mist mx-auto" />
        <div className="text-[14px] font-serif font-semibold text-ink">
          暂无电子凭证
        </div>
        <p className="text-[12px] text-ink-2">
          办理余额查询、交易流水、贷款申请、挂失或工单创建后，回单将自动归档于此。
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between text-[11px] text-ink-2">
        <span className="micro-label">SESSION ARCHIVE</span>
        <span className="tabular-mono">共 {receipts.length} 份</span>
      </div>

      <div className="space-y-3">
        {[...receipts].reverse().map((receipt) => (
          <ReceiptCard key={receipt.id} receipt={receipt} sealTone="ink" />
        ))}
      </div>
    </div>
  );
};
