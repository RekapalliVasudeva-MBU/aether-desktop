export type ChatMode = 'normal' | 'rag' | 'multiagent';

export interface Session {
  id: string;
  title: string;
  preview: string;
  pinned: boolean;
  chars: number;
  files: string[];
  mode: ChatMode;
}

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
  citations?: any[];
}

export interface SubagentStep {
  id: string;
  agent: string;
  role: string;
  task: string;
  status: 'running' | 'completed' | 'failed';
  summary?: string;
}

export interface HitlApproval {
  tool: string;
  args: Record<string, any>;
  subagent: string;
  reason: string;
}

export interface Checkpoint {
  id: string;
  timestamp: number;
  status: string;
  step_index: number;
}

export interface WatcherEvent {
  id: string;
  timestamp: number;
  filename: string;
  path: string;
  status: 'processing' | 'completed' | 'error' | 'ignored';
  details?: string;
}

export interface WatcherStatus {
  running: boolean;
  watch_dir: string;
  total_events: number;
  recent_events: WatcherEvent[];
}

export interface RoleModelMapping {
  planner?: string;
  code?: string;
  research?: string;
  synthesis?: string;
}
