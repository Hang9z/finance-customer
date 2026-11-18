import { TaskEventInfo, WorkflowState } from '../types/chat';

const SWITCH_RE = /^好的[,，]\s*现在把(.+?)暂停[,，]\s*现在开始执行(.+?)$/;
const START_RE = /^好的[,，]\s*现在开始执行(.+?)$/;
const RESUME_RE = /^好的[,，]\s*现在继续(.+?)$/;
const CANCEL_RE = /^好的[,，]\s*现在取消(.+?)$/;

const COMPLETION_RE = /成功|已为您|可用余额为|申请编号|工单编号|失败|格式有误/;
const AWAITING_START_RE = /^(?:请提供|请问|请详细|请告诉)/;

export function parseTaskEvent(text: string): TaskEventInfo | null {
  const trimmed = text.trim();
  if (!trimmed) {
    return null;
  }

  // 必须先于 start 规则匹配 switch
  const switchMatch = SWITCH_RE.exec(trimmed);
  if (switchMatch) {
    return {
      kind: 'switch',
      previousFlow: switchMatch[1].trim(),
      flow: switchMatch[2].trim(),
      rawText: trimmed,
    };
  }

  const startMatch = START_RE.exec(trimmed);
  if (startMatch) {
    return {
      kind: 'start',
      flow: startMatch[1].trim(),
      rawText: trimmed,
    };
  }

  const resumeMatch = RESUME_RE.exec(trimmed);
  if (resumeMatch) {
    return {
      kind: 'resume',
      flow: resumeMatch[1].trim(),
      rawText: trimmed,
    };
  }

  const cancelMatch = CANCEL_RE.exec(trimmed);
  if (cancelMatch) {
    return {
      kind: 'cancel',
      flow: cancelMatch[1].trim(),
      rawText: trimmed,
    };
  }

  return null;
}

function inferAwaitingLabel(question: string): string {
  if (question.includes('卡号') || question.includes('账户号')) {
    return '银行卡号 / 账户号';
  }
  if (question.includes('贷款金额')) {
    return '贷款金额';
  }
  if (question.includes('贷款期限')) {
    return '贷款期限';
  }
  if (question.includes('挂失') && question.includes('原因')) {
    return '挂失原因';
  }
  if (question.includes('问题类型')) {
    return '问题类型';
  }
  if (question.includes('详细描述') || question.includes('诉求')) {
    return '问题描述';
  }
  return question.replace(/[？?。]+$/, '').slice(0, 14);
}

function isAwaitingQuestion(text: string): boolean {
  const trimmed = text.trim();
  return trimmed.endsWith('？') || trimmed.endsWith('?') || AWAITING_START_RE.test(trimmed);
}

export function createInitialWorkflowState(): WorkflowState {
  return { active: null, paused: [] };
}

export function applyTurnTextsToWorkflow(
  current: WorkflowState,
  botTexts: string[],
): WorkflowState {
  let active = current.active ? { ...current.active } : null;
  let paused = [...current.paused];
  const nonEventTexts: string[] = [];

  for (const raw of botTexts) {
    const event = parseTaskEvent(raw);
    if (!event) {
      if (raw.trim()) {
        nonEventTexts.push(raw.trim());
      }
      continue;
    }

    if (event.kind === 'start') {
      active = { flowName: event.flow, awaiting: null, awaitingQuestion: null };
    } else if (event.kind === 'switch') {
      const prev = active?.flowName ?? event.previousFlow;
      if (prev && !paused.includes(prev)) {
        paused.push(prev);
      }
      paused = paused.filter((f) => f !== event.flow);
      active = { flowName: event.flow, awaiting: null, awaitingQuestion: null };
    } else if (event.kind === 'resume') {
      paused = paused.filter((f) => f !== event.flow);
      active = { flowName: event.flow, awaiting: null, awaitingQuestion: null };
    } else if (event.kind === 'cancel') {
      if (active?.flowName === event.flow) {
        active = null;
      } else {
        paused = paused.filter((f) => f !== event.flow);
      }
    }
  }

  const lastText = nonEventTexts[nonEventTexts.length - 1];
  if (lastText) {
    if (COMPLETION_RE.test(lastText)) {
      active = null;
    } else if (active && isAwaitingQuestion(lastText)) {
      active = {
        ...active,
        awaiting: inferAwaitingLabel(lastText),
        awaitingQuestion: lastText,
      };
    }
  }

  return { active, paused };
}
