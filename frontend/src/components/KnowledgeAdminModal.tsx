import React from 'react';
import { ExternalLink, FileUp, ServerOff, X } from 'lucide-react';

interface KnowledgeAdminModalProps {
  isOpen: boolean;
  onClose: () => void;
  importOnline: boolean;
  importUrl: string;
}

export const KnowledgeAdminModal: React.FC<KnowledgeAdminModalProps> = ({
  isOpen,
  onClose,
  importOnline,
  importUrl,
}) => {
  if (!isOpen) {
    return null;
  }

  const startupCommand =
    'Push-Location D:\\code\\finance_brain; .\\.venv\\Scripts\\python api/file_import_service.py';

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 backdrop-blur-[1px] p-4"
      role="dialog"
      aria-modal="true"
      aria-label="知识库文档导入工作台"
    >
      <div className="w-full max-w-[960px] h-[82vh] bg-surface border border-hairline rounded-[14px] shadow-ledger flex flex-col overflow-hidden">
        {/* 顶栏 */}
        <div className="px-4 py-3 border-b border-hairline flex items-center justify-between gap-3 shrink-0 bg-paper">
          <div className="flex items-center gap-2.5 min-w-0">
            <span className="inline-flex items-center justify-center w-6 h-6 rounded-[6px] bg-surface border border-hairline text-celadon shrink-0">
              <FileUp className="w-3.5 h-3.5" />
            </span>
            <h2 className="font-serif text-[15px] font-semibold text-ink whitespace-nowrap">
              知识库 · 文档导入入库
            </h2>
            <span className="hidden sm:inline-flex items-center gap-1.5 text-[11px] text-ink-2 bg-surface border border-hairline rounded px-2 py-0.5 tabular-mono">
              <span
                className={`w-1.5 h-1.5 rounded-full ${
                  importOnline ? 'bg-celadon' : 'bg-seal'
                }`}
              />
              {importOnline ? ':8002 在线' : ':8002 离线'}
            </span>
          </div>

          <div className="flex items-center gap-2 shrink-0">
            <a
              href={importUrl}
              target="_blank"
              rel="noreferrer"
              className="inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-[6px] border border-hairline bg-surface text-[12px] text-ink-2 hover:text-ink hover:border-ink transition-colors"
            >
              <ExternalLink className="w-3.5 h-3.5" />
              <span>新窗口打开</span>
            </a>
            <button
              type="button"
              onClick={onClose}
              aria-label="关闭知识库导入弹窗"
              className="p-1.5 rounded text-ink-2 hover:text-ink hover:bg-surface transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* 内容区 */}
        <div className="flex-1 min-h-0 bg-paper relative">
          {importOnline ? (
            <iframe
              key={importUrl}
              src={importUrl}
              title="知识库文档导入台"
              className="w-full h-full border-0 bg-paper"
            />
          ) : (
            <div className="h-full flex flex-col items-center justify-center p-6 text-center space-y-3">
              <ServerOff className="w-8 h-8 text-seal" />
              <div className="text-[14px] font-medium text-ink">
                金融智脑文档导入服务 (:8002) 当前未启动
              </div>
              <p className="text-[12px] text-ink-2 max-w-[520px] leading-relaxed">
                启动后即可在此直接上传 PDF / Word / Markdown 金融制度与财报文档到 Milvus 向量库，并在智能客服对话中实时召回与引用溯源。
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
