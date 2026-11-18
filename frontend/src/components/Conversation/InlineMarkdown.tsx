import React, { useState } from 'react';
import ReactMarkdown, { Components } from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Check, Copy } from 'lucide-react';

const INLINE_TOKEN_RE =
  /(\b(?:LAP|TKT|ACC|TXN|LMT)[A-Z0-9]+\b|[\d,]+\.\d{2}\s*(?:CNY|RMB|USD|元)|\bloss_reported\b)/g;

const CopyTokenChip: React.FC<{ token: string }> = ({ token }) => {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    void navigator.clipboard?.writeText(token);
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1200);
  };

  return (
    <button
      type="button"
      onClick={handleCopy}
      title="点击复制"
      aria-label={`复制 ${token}`}
      className="inline-flex items-center gap-1 mx-0.5 px-1.5 py-0.2 rounded bg-paper border border-hairline tabular-mono text-[12px] text-ink hover:border-ink align-baseline transition-colors"
    >
      <span>{token}</span>
      {copied ? (
        <Check className="w-2.5 h-2.5 text-celadon" />
      ) : (
        <Copy className="w-2.5 h-2.5 text-mist" />
      )}
    </button>
  );
};

function decorateTextNodes(children: React.ReactNode): React.ReactNode {
  return React.Children.map(children, (child) => {
    if (typeof child !== 'string') {
      return child;
    }

    const parts = child.split(INLINE_TOKEN_RE);
    if (parts.length <= 1) {
      return child;
    }

    return parts.map((part, idx) => {
      if (!part) {
        return null;
      }
      if (idx % 2 === 1) {
        return <CopyTokenChip key={`${part}_${idx}`} token={part} />;
      }
      return part;
    });
  });
}

const markdownComponents: Components = {
  p: ({ children }) => <p className="mb-2 last:mb-0 leading-[1.7]">{decorateTextNodes(children)}</p>,
  li: ({ children }) => <li className="leading-[1.7]">{decorateTextNodes(children)}</li>,
  strong: ({ children }) => <strong className="font-semibold text-ink">{decorateTextNodes(children)}</strong>,
  em: ({ children }) => <em>{decorateTextNodes(children)}</em>,
  ul: ({ children }) => <ul className="list-disc pl-5 my-2 space-y-1">{children}</ul>,
  ol: ({ children }) => <ol className="list-decimal pl-5 my-2 space-y-1">{children}</ol>,
  table: ({ children }) => (
    <div className="overflow-x-auto my-2 border border-hairline rounded">
      <table className="w-full text-left border-collapse text-[12px]">{children}</table>
    </div>
  ),
  thead: ({ children }) => <thead className="bg-paper border-b border-hairline">{children}</thead>,
  th: ({ children }) => <th className="py-1.5 px-2.5 font-medium text-ink-2">{children}</th>,
  td: ({ children }) => (
    <td className="py-1.5 px-2.5 border-b border-hairline">{decorateTextNodes(children)}</td>
  ),
  code: ({ children }) => (
    <code className="px-1.5 py-0.5 rounded bg-paper border border-hairline tabular-mono text-[12px]">
      {children}
    </code>
  ),
};

interface InlineMarkdownProps {
  content: string;
}

export const InlineMarkdown: React.FC<InlineMarkdownProps> = ({ content }) => {
  return (
    <div className="text-[14px] text-ink break-words">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={markdownComponents}>
        {content}
      </ReactMarkdown>
    </div>
  );
};
