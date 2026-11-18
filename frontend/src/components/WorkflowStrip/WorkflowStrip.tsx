import React from 'react';
import { Pause, Play } from 'lucide-react';
import { WorkflowState } from '../../types/chat';

interface WorkflowStripProps {
  workflow: WorkflowState;
  disabled?: boolean;
  onResumeFlow: (flowName: string) => void;
}

export const WorkflowStrip: React.FC<WorkflowStripProps> = ({
  workflow,
  disabled = false,
  onResumeFlow,
}) => {
  const hasWorkflow = workflow.active !== null || workflow.paused.length > 0;

  return (
    <div className="min-h-[40px] bg-paper border-b border-hairline px-4 md:px-6 flex items-center justify-between gap-3 shrink-0 py-1.5">
      <div className="flex items-center flex-wrap gap-x-4 gap-y-1 min-w-0 text-[12px]">
        {!hasWorkflow ? (
          <span className="text-mist">当前没有进行中的业务</span>
        ) : (
          <>
            {workflow.active ? (
              <span className="inline-flex items-center gap-1.5 text-ink font-medium">
                <span className="w-2 h-2 rounded-full bg-ink shrink-0" />
                <span>
                  {workflow.active.flowName}
                  <span className="text-ink-2 font-normal">
                    （进行中
                    {workflow.active.awaiting
                      ? ` · 等待：${workflow.active.awaiting}`
                      : ''}
                    ）
                  </span>
                </span>
              </span>
            ) : null}

            {workflow.paused.map((flowName) => (
              <span
                key={flowName}
                className="inline-flex items-center gap-1.5 text-amber"
              >
                <Pause className="w-3 h-3 shrink-0" />
                <span>已暂停：{flowName}</span>
                <button
                  type="button"
                  disabled={disabled}
                  onClick={() => onResumeFlow(flowName)}
                  className="inline-flex items-center gap-0.5 text-celadon hover:underline font-medium disabled:opacity-50"
                  aria-label={`恢复 ${flowName}`}
                >
                  <Play className="w-3 h-3" />
                  <span>[恢复]</span>
                </button>
              </span>
            ))}
          </>
        )}
      </div>

      <span className="text-[11px] text-mist shrink-0 hidden sm:inline">
        根据会话事件推断
      </span>
    </div>
  );
};
