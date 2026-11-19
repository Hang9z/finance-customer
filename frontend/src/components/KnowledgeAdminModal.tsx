import React, { useState } from 'react';
import { ExternalLink, FileUp, MessageSquareText, ServerOff, X } from 'lucide-react';
import { ServiceHealthStatus } from '../types/chat';

interface KnowledgeAdminModalProps {
  isOpen: boolean;
  onClose: () => void;
  queryStatus: ServiceHealthStatus;
  importOnline: boolean;
  chatUrl: string;
  importUrl: string;
}

type WorkbenchTab = 'import' | 'chat';

export const KnowledgeAdminModal: React.FC<KnowledgeAdminModalProps> = ({
  isOpen,
  onClose,
  queryStatus,
  importOnline,
  chatUrl,
  importUrl,
}) => {
  const [activeTab, setActiveTab] = useState<WorkbenchTab>('import');

  if (!isOpen) {
    return null;
  }

  const currentUrl = activeTab === 'import' ? importUrl : chatUrl;
  const isCurrentOnline = activeTab === 'import' ? importOnline : queryStatus === 'online';
  const startupCommand =
    activeTab === 'import'
      ? 'Push-Location D:\\code\\finance_brain; .\\.venv\\Scripts\\python api/file_import_service.py'
      : 'Push-Location D:\\code\\finance_brain; .\\.venv\\Scripts\\python api/query_service.py';

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 backdrop-blur-[1px] p-4"
      role="dialog"
      aria-modal="true"
      aria-label="金融智脑 RAG 知识库工作台"
    >
      <div className="w-full max-w-[1040px] h-[85vh] bg-surface border border-hairline rounded-[14px] shadow-ledger flex flex-col overflow-hidden">
        {/* 顶栏 */}
        <div className="px-4 py-3 border-b border-hairline flex items-center justify-between gap-3 shrink-0 bg-paper">
          <div className="flex items-center gap-4 min-w-0">
            <h2 className="font-serif text-[15px] font-semibold text-ink whitespace-nowrap">
              金融智脑 · RAG 知识库工作台
            </h2>
            <div className="flex items-center gap-1.5 bg-surface border border-hairline rounded-[8px] p-0.5">
              <button
                type="button"
                onClick={() => setActiveTab('import')}
                className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-[6px] text-[12px] transition-colors ${
                  activeTab === 'import'
                    ? 'bg-ink text-white font-medium'
                    : 'text-ink-2 hover:text-ink'
                }`}
              >
                <FileUp className="w-3.5 h-3.5" />
                <span>文档导入入库 (:8002)</span>
              </button>
              <button
                type="button"
                onClick={() => setActiveTab('chat')}
                className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-[6px] text-[12px] transition-colors ${
                  activeTab === 'chat'
                    ? 'bg-ink text-white font-medium'
                    : 'text-ink-2 hover:text-ink'
                }`}
              >
                <MessageSquareText className="w-3.5 h-3.5" />
                <span>智脑检索调试 (:8001)</span>
              </button>
            </div>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <a
              href={currentUrl}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-[6px] border border-hairline text-[12px] text-ink-2 hover:text-ink hover:border-ink transition-colors"
            >
              <ExternalLink className="w-3.5 h-3.5" />
              <span>新窗口打开</span>
            </a>
            <button
              type="button"
              onClick={onClose}
              aria-label="关闭知识库工作台"
              className="p-1.5 rounded text-ink-2 hover:text-ink hover:bg-surface transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* 内容区 */}
        <div className="flex-1 min-h-0 bg-paper relative">
          {isCurrentOnline ? (
            <iframe
              key={currentUrl}
              src={currentUrl}
              title={activeTab === 'import' ? '金融智脑文档导入台' : '金融智脑深度问答页'}
              className="w-full h-full border-0 bg-white"
            />
          ) : (
            <div className="h-full flex flex-col items-center justify-center p-6 text-center space-y-3">
              <ServerOff className="w-8 h-8 text-seal" />
              <div className="text-[14px] font-medium text-ink">
                {activeTab === 'import'
                  ? '金融智脑文档导入服务 (:8002) 当前未启动'
                  : '金融智脑检索问答服务 (:8001) 当前未启动'}
              </div>
              <p className="text-[12px] text-ink-2 max-w-[520px] leading-relaxed">
                启动后即可在此直接上传 PDF / Markdown 金融制度文档到 Milvus 向量库，并在智能客服对话中实时召回与引用溯源。
              </p>
              <code className="tabular-mono text-[11px] bg-surface border border-hairline rounded px-3 py-2 text-ink max-w-full overflow-x-auto">
                {startupCommand}
              </code>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
