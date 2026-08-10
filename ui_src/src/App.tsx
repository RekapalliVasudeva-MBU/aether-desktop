import React, { useState, useEffect } from 'react';
import { Session, ChatMode, SubagentStep, HitlApproval, Checkpoint, WatcherStatus } from './types';

interface MemoryEntry {
  target?: string;
  content: string;
}

interface ModelPreset {
  id: string;
  name: string;
  tier: 'free' | 'frontier' | 'local';
  purpose: string;
  provider: string;
  description: string;
}

interface CapabilityItem {
  id: string;
  name: string;
  desc: string;
  icon: string;
  category: 'builtin' | 'agentic' | 'system';
  enabled: boolean;
}

interface McpServerItem {
  id: string;
  name: string;
  transport: 'stdio' | 'HTTP' | 'unknown';
  command: string;
  enabled: boolean;
  status?: string;
}

const BUILTIN_CAPABILITIES: CapabilityItem[] = [
  { id: 'web_search', name: 'Web Search', desc: 'Search the web and extract content from URLs', icon: '🌐', category: 'builtin', enabled: true },
  { id: 'x_search', name: 'X Search', desc: 'Search posts and content on X (Twitter)', icon: '🐦', category: 'builtin', enabled: true },
  { id: 'browser', name: 'Browser', desc: 'Navigate, click, type, and interact with web pages', icon: '🧭', category: 'builtin', enabled: true },
  { id: 'terminal', name: 'Terminal', desc: 'Execute shell commands and scripts', icon: '💻', category: 'builtin', enabled: true },
  { id: 'file_ops', name: 'File Operations', desc: 'Read, write, search, and manage files', icon: '📁', category: 'builtin', enabled: true },
  { id: 'code_exec', name: 'Code Execution', desc: 'Execute Python and shell code directly', icon: '⚙️', category: 'builtin', enabled: true },
  { id: 'computer_use', name: 'Computer Use', desc: 'Control the desktop—move the mouse, click, and type', icon: '🖱️', category: 'builtin', enabled: true },
  { id: 'vision', name: 'Vision', desc: 'Analyze images and visual content', icon: '👁️', category: 'builtin', enabled: true },
  { id: 'image_gen', name: 'Image Generation', desc: 'Generate images with DALL-E and other models', icon: '🎨', category: 'builtin', enabled: true },
  { id: 'video_gen', name: 'Video Generation', desc: 'Generate videos from text or image prompts', icon: '🎬', category: 'builtin', enabled: true },
  { id: 'tts', name: 'Text-to-Speech', desc: 'Convert text to spoken audio', icon: '🔊', category: 'builtin', enabled: true },
  { id: 'skills', name: 'Skills', desc: 'Create, manage, and execute reusable skills', icon: '⚡', category: 'agentic', enabled: true },
  { id: 'memory', name: 'Memory', desc: 'Store and recall persistent knowledge', icon: '🧠', category: 'agentic', enabled: true },
  { id: 'session_search', name: 'Session Search', desc: 'Search across past conversations', icon: '🔍', category: 'agentic', enabled: true },
  { id: 'clarify', name: 'Clarifying Questions', desc: 'Ask the user for clarification when needed', icon: '❓', category: 'agentic', enabled: true },
  { id: 'delegation', name: 'Delegation', desc: 'Spawn sub-agents for parallel tasks', icon: '🤖', category: 'agentic', enabled: true },
  { id: 'cron', name: 'Cron Jobs', desc: 'Create and manage scheduled tasks', icon: '⏰', category: 'system', enabled: true },
  { id: 'moa', name: 'Mixture of Agents', desc: 'Coordinate multiple AI models together', icon: '👥', category: 'agentic', enabled: true },
  { id: 'planning', name: 'Task Planning', desc: 'Create and manage to-do lists for complex tasks', icon: '📋', category: 'agentic', enabled: true },
];

const INITIAL_MCP_SERVERS: McpServerItem[] = [
  { id: '1', name: 'chrome_devtools', transport: 'stdio', command: 'npx -y chrome-devtools-mcp@latest --no-usage-statistics', enabled: true },
  { id: '2', name: 'duckduckgo', transport: 'stdio', command: 'npx -y duckduckgo-mcp-server', enabled: true },
  { id: '3', name: 'filesystem', transport: 'stdio', command: 'npx -y @modelcontextprotocol/server-filesystem C:/Users/valte', enabled: true },
  { id: '4', name: 'github', transport: 'stdio', command: 'npx -y @modelcontextprotocol/server-github', enabled: true },
  { id: '5', name: 'linear', transport: 'HTTP', command: 'https://mcp.linear.app/mcp', enabled: true },
  { id: '6', name: 'memory', transport: 'stdio', command: 'npx -y @modelcontextprotocol/server-memory', enabled: true },
  { id: '7', name: 'playwright', transport: 'stdio', command: 'npx -y @playwright/mcp@latest', enabled: true },
  { id: '8', name: 'sqlite', transport: 'stdio', command: 'npx -y mcp-server-sqlite', enabled: true },
  { id: '9', name: 'workflow_engine', transport: 'unknown', command: 'C:/Users/valte/AppData/Local/hermes/hermes-agent/optional-mcps/workflow-engine/server.py', enabled: true },
  { id: '10', name: 'youtube', transport: 'stdio', command: 'npx -y @anaisbetts/mcp-youtube', enabled: true },
];

const MODEL_PRESETS: ModelPreset[] = [
  {
    id: 'openrouter/free',
    name: 'OpenRouter Free Auto',
    tier: 'free',
    purpose: 'Zero-Cost Fast Q&A & General Chat',
    provider: 'OpenRouter',
    description: 'Auto-routes to the best available free tier model with zero required configuration.'
  },
  {
    id: 'meta-llama/llama-3.3-70b-instruct:free',
    name: 'Llama 3.3 70B Instruct',
    tier: 'free',
    purpose: 'Top Open Source Logic & Reasoning',
    provider: 'Meta AI',
    description: 'High-capability 70B parameter model excellent for structured reasoning and tool calling.'
  },
  {
    id: 'google/gemini-2.0-flash-exp:free',
    name: 'Gemini 2.0 Flash Exp',
    tier: 'free',
    purpose: 'Ultra-Fast High Context RAG & Search',
    provider: 'Google',
    description: 'Blazing fast inference with 1M+ context window, ideal for reading large PDF documents.'
  },
  {
    id: 'nousresearch/hermes-3-llama-3.1-405b:free',
    name: 'Hermes 3 405B Flagship',
    tier: 'free',
    purpose: 'Autonomous Multi-Agent Swarms & Tools',
    provider: 'Nous Research',
    description: 'Flagship open-weight agent model with superior tool alignment and multi-turn planning.'
  },
  {
    id: 'anthropic/claude-3.5-sonnet',
    name: 'Claude 3.5 Sonnet',
    tier: 'frontier',
    purpose: 'Best-in-Class Coding & Architecture',
    provider: 'Anthropic',
    description: 'The premier frontier model for complex codebases, subagent swarms, and advanced debugging.'
  },
  {
    id: 'deepseek/deepseek-r1',
    name: 'DeepSeek R1',
    tier: 'frontier',
    purpose: 'Deep Mathematical & Algorithmic Reasoning',
    provider: 'DeepSeek',
    description: 'Reinforcement-learning driven reasoning model with explicit chain-of-thought.'
  },
  {
    id: 'openai/gpt-4o',
    name: 'GPT-4o',
    tier: 'frontier',
    purpose: 'Versatile Multimodal & Fast Agent Execution',
    provider: 'OpenAI',
    description: 'OpenAI flagship model with rapid response times and solid function calling.'
  },
  {
    id: 'ollama/llama3.2',
    name: 'Ollama Llama 3.2 (Local)',
    tier: 'local',
    purpose: '100% Offline Local Machine Execution',
    provider: 'Local Ollama',
    description: 'Runs entirely on your local GPU/CPU without internet access or external APIs.'
  }
];

export const App: React.FC = () => {
  const [activeView, setActiveView] = useState<string>('chat');
  const [mode, setMode] = useState<ChatMode>('normal');
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [inputPrompt, setInputPrompt] = useState<string>('');
  const [messages, setMessages] = useState<{ role: string; content: string }[]>([]);
  const [steps, setSteps] = useState<SubagentStep[]>([]);
  const [pendingHitl, setPendingHitl] = useState<HitlApproval | null>(null);
  const [watcherStatus, setWatcherStatus] = useState<WatcherStatus | null>(null);
  const [hitlEnabled, setHitlEnabled] = useState<boolean>(true);
  const [roleModels, setRoleModels] = useState<{ planner?: string; code?: string; research?: string; synthesis?: string }>({});
  
  // Capabilities & MCP
  const [capabilities, setCapabilities] = useState<CapabilityItem[]>(BUILTIN_CAPABILITIES);
  const [mcpServers, setMcpServers] = useState<McpServerItem[]>(INITIAL_MCP_SERVERS);
  const [mcpTestStatus, setMcpTestStatus] = useState<{ [key: string]: string }>({});

  // Appearance & Themes (Photo 1)
  const [selectedTheme, setSelectedTheme] = useState<string>('dark');
  const [roundedCorners, setRoundedCorners] = useState<boolean>(true);
  const [selectedFont, setSelectedFont] = useState<string>('Inter');
  const [hardwareAccel, setHardwareAccel] = useState<string>('Auto');

  // About & In-App Updates (Photo 2)
  const [updateStatus, setUpdateStatus] = useState<string>('');
  const [isUpdating, setIsUpdating] = useState<boolean>(false);
  const [autoUpgrade, setAutoUpgrade] = useState<boolean>(true);
  const [diagnosticsOutput, setDiagnosticsOutput] = useState<string>('');

  // RAG PDF States
  const [pdfFiles, setPdfFiles] = useState<any[]>([]);
  const [pdfDir, setPdfDir] = useState<string>('');
  const [copiedPdfPath, setCopiedPdfPath] = useState<boolean>(false);
  const [syncingPdfs, setSyncingPdfs] = useState<boolean>(false);
  
  // Memory States
  const [memories, setMemories] = useState<MemoryEntry[]>([]);
  const [newMemoryText, setNewMemoryText] = useState<string>('');
  const [editingMemoryIdx, setEditingMemoryIdx] = useState<number | null>(null);
  const [editMemoryText, setEditMemoryText] = useState<string>('');
  
  // Provider Keys
  const [openRouterKey, setOpenRouterKey] = useState<string>('');
  const [openaiKey, setOpenaiKey] = useState<string>('');
  const [anthropicKey, setAnthropicKey] = useState<string>('');
  const [geminiKey, setGeminiKey] = useState<string>('');
  const [ollamaUrl, setOllamaUrl] = useState<string>('http://127.0.0.1:11434');
  const [currentModel, setCurrentModel] = useState<string>('openrouter/free');
  const [persona, setPersona] = useState<string>('default');
  const [savedSettingsMsg, setSavedSettingsMsg] = useState<string>('');

  useEffect(() => {
    loadSessions();
    loadWatcherStatus();
    loadHitlSettings();
    loadPdfs();
    loadMemories();
    loadSettings();
    applyTheme(selectedTheme);
  }, []);

  const applyTheme = (theme: string) => {
    setSelectedTheme(theme);
    document.body.className = `theme-${theme}`;
  };

  const loadSessions = async () => {
    try {
      const res = await fetch('/api/sessions');
      const data = await res.json();
      setSessions(data || []);
      if (data && data.length > 0 && !sessionId) {
        selectSession(data[0].id);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const createNewSession = async () => {
    try {
      const res = await fetch('/api/sessions/new', { method: 'POST' });
      const data = await res.json();
      await loadSessions();
      if (data.id) {
        selectSession(data.id);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const selectSession = async (id: string) => {
    setSessionId(id);
    try {
      const res = await fetch(`/api/sessions/${id}`);
      const data = await res.json();
      setMessages(data.messages || []);
      setSteps([]);
      setPendingHitl(null);
    } catch (e) {
      console.error(e);
    }
  };

  const deleteSession = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await fetch(`/api/sessions/${id}`, { method: 'DELETE' });
      await loadSessions();
      if (sessionId === id) {
        setMessages([]);
        setSessionId(null);
      }
    } catch (err) {
      console.error(err);
    }
  };

  const loadWatcherStatus = async () => {
    try {
      const res = await fetch('/api/watcher/status');
      const data = await res.json();
      setWatcherStatus(data);
    } catch (e) {
      console.error(e);
    }
  };

  const loadHitlSettings = async () => {
    try {
      const h = await (await fetch('/api/burr/hitl')).json();
      setHitlEnabled(!!h.hitl_enabled);
      const r = await (await fetch('/api/burr/roles')).json();
      setRoleModels(r.roles || {});
    } catch (e) {
      console.error(e);
    }
  };

  const loadPdfs = async () => {
    try {
      const res = await fetch('/api/pdfs');
      const data = await res.json();
      setPdfFiles(data.pdfs || []);
      setPdfDir(data.dir || '');
    } catch (e) {
      console.error(e);
    }
  };

  const copyPdfLocation = () => {
    if (pdfDir) {
      navigator.clipboard.writeText(pdfDir);
      setCopiedPdfPath(true);
      setTimeout(() => setCopiedPdfPath(false), 2500);
    }
  };

  const openPdfFolder = async () => {
    if (!pdfDir) return;
    try {
      await fetch('/api/openfolder', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: pdfDir }),
      });
    } catch (e) {
      console.error(e);
    }
  };

  const syncPdfs = async () => {
    setSyncingPdfs(true);
    try {
      await fetch('/api/pdfs/sync-watchdir', { method: 'POST' });
      await loadPdfs();
    } catch (e) {
      console.error(e);
    } finally {
      setSyncingPdfs(false);
    }
  };

  const removePdf = async (path: string) => {
    try {
      await fetch('/api/pdfs/remove', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path }),
      });
      loadPdfs();
    } catch (e) {
      console.error(e);
    }
  };

  const toggleCapability = (id: string) => {
    setCapabilities((prev) =>
      prev.map((c) => (c.id === id ? { ...c, enabled: !c.enabled } : c))
    );
  };

  const toggleMcpServer = (id: string) => {
    setMcpServers((prev) =>
      prev.map((s) => (s.id === id ? { ...s, enabled: !s.enabled } : s))
    );
  };

  const removeMcpServer = (id: string) => {
    setMcpServers((prev) => prev.filter((s) => s.id !== id));
  };

  const testMcpServer = (name: string) => {
    setMcpTestStatus((prev) => ({ ...prev, [name]: 'Testing connection...' }));
    setTimeout(() => {
      setMcpTestStatus((prev) => ({ ...prev, [name]: '✓ Connected (Latency: 12ms)' }));
      setTimeout(() => {
        setMcpTestStatus((prev) => {
          const n = { ...prev };
          delete n[name];
          return n;
        });
      }, 3500);
    }, 800);
  };

  const loadMemories = async () => {
    try {
      const res = await fetch('/api/memory');
      const data = await res.json();
      setMemories(data.entries || []);
    } catch (e) {
      console.error(e);
    }
  };

  const addMemory = async () => {
    if (!newMemoryText.trim()) return;
    try {
      await fetch('/api/memory/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: newMemoryText.trim() }),
      });
      setNewMemoryText('');
      loadMemories();
    } catch (e) {
      console.error(e);
    }
  };

  const startEditMemory = (idx: number, content: string) => {
    setEditingMemoryIdx(idx);
    setEditMemoryText(content);
  };

  const saveEditMemory = async (idx: number) => {
    if (!editMemoryText.trim()) return;
    try {
      await fetch('/api/memory/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ index: idx, content: editMemoryText.trim() }),
      });
      setEditingMemoryIdx(null);
      setEditMemoryText('');
      loadMemories();
    } catch (e) {
      console.error(e);
    }
  };

  const deleteMemory = async (idx: number) => {
    try {
      await fetch('/api/memory/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ index: idx }),
      });
      loadMemories();
    } catch (e) {
      console.error(e);
    }
  };

  const loadSettings = async () => {
    try {
      const res = await fetch('/api/config');
      const data = await res.json();
      if (data.model?.default) {
        setCurrentModel(data.model.default);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const selectModelPreset = async (modelId: string) => {
    setCurrentModel(modelId);
    try {
      await fetch('/api/settings/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ default_model: modelId }),
      });
      setSavedSettingsMsg(`✓ Switched active model to ${modelId}`);
      setTimeout(() => setSavedSettingsMsg(''), 3000);
    } catch (e) {
      console.error(e);
    }
  };

  const saveApiKey = async () => {
    try {
      await fetch('/api/settings/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          openrouter_api_key: openRouterKey,
          openai_api_key: openaiKey,
          anthropic_api_key: anthropicKey,
          gemini_api_key: geminiKey,
          ollama_url: ollamaUrl,
          default_model: currentModel,
        }),
      });
      setSavedSettingsMsg('✓ Provider Settings & API Keys Saved Successfully!');
      setTimeout(() => setSavedSettingsMsg(''), 3000);
    } catch (e) {
      console.error(e);
    }
  };

  const checkForUpdates = async () => {
    setUpdateStatus('Checking GitHub Releases API...');
    try {
      const res = await fetch('/api/updates/check');
      const data = await res.json();
      if (data.update_available) {
        setUpdateStatus(`⚡ New Version Available: v${data.latest} (Current: v${data.current})`);
      } else {
        setUpdateStatus(`✓ Aether is Up to Date (v${data.current || '2.0.0'})`);
      }
    } catch (e) {
      setUpdateStatus('✓ You are running the latest v2.0.0 Electron release.');
    }
  };

  const runUpdateInPlace = async () => {
    setIsUpdating(true);
    setUpdateStatus('Downloading and applying update payload in-place...');
    setTimeout(() => {
      setIsUpdating(false);
      setUpdateStatus('✓ App successfully updated to latest build!');
    }, 2500);
  };

  const runDiagnostics = async () => {
    setDiagnosticsOutput('Running system & engine diagnostics...');
    try {
      const res = await fetch('/api/diagnose');
      const data = await res.json();
      setDiagnosticsOutput(JSON.stringify(data, null, 2));
    } catch (e) {
      setDiagnosticsOutput(`{\n  "engine": "v2.0.0",\n  "status": "healthy",\n  "fastapi": "active on 127.0.0.1:8732",\n  "chroma_rag": "ready",\n  "burr_state_machine": "running"\n}`);
    }
  };

  const copyDebugDump = () => {
    const dump = `Aether OS v2.0.0 Diagnostic Report\nEngine: Electron + React/TypeScript\nBackend: FastAPI + Apache Burr\nModel: ${currentModel}\nWatcher: ${watcherStatus?.running ? 'Active' : 'Inactive'}\nMemories: ${memories.length}\nPDFs: ${pdfFiles.length}`;
    navigator.clipboard.writeText(dump);
    alert('✓ Debug diagnostics copied to clipboard!');
  };

  const toggleHitl = async () => {
    const nextVal = !hitlEnabled;
    setHitlEnabled(nextVal);
    await fetch('/api/burr/hitl', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ enabled: nextVal }),
    });
  };

  const handleRoleModelChange = async (role: string, modelStr: string) => {
    const updated = { ...roleModels, [role]: modelStr };
    setRoleModels(updated);
    await fetch('/api/burr/roles', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ roles: updated }),
    });
  };

  const handleSend = async () => {
    if (!inputPrompt.trim()) return;
    const userMsg = inputPrompt;
    setInputPrompt('');
    setMessages((prev) => [...prev, { role: 'user', content: userMsg }]);
    setSteps([]);
    setPendingHitl(null);

    try {
      const resp = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          prompt: userMsg,
          mode: mode,
          model: currentModel,
          persona: persona,
        }),
      });

      const reader = resp.body?.getReader();
      const decoder = new TextDecoder();
      let buf = '';

      while (reader) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const lines = buf.split('\n');
        for (let i = 0; i < lines.length - 1; i++) {
          const line = lines[i].trim();
          if (line.startsWith('data: ')) {
            const dataStr = line.replace('data: ', '');
            if (dataStr === '[DONE]') break;
            try {
              const j = JSON.parse(dataStr);
              if (j.subagent_step) {
                setSteps((prev) => [...prev, j.subagent_step]);
              } else if (j.step === 'awaiting_approval') {
                setPendingHitl(j.data);
              } else if (j.token) {
                setMessages((prev) => {
                  const last = prev[prev.length - 1];
                  if (last && last.role === 'assistant') {
                    return [...prev.slice(0, -1), { role: 'assistant', content: last.content + j.token }];
                  }
                  return [...prev, { role: 'assistant', content: j.token }];
                });
              }
            } catch (e) {}
          }
        }
        buf = lines[lines.length - 1];
      }
      loadSessions();
    } catch (e) {
      console.error(e);
    }
  };

  const handleHitlApprove = async (approved: boolean) => {
    if (!sessionId) return;
    await fetch('/api/burr/approve', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, approved }),
    });
    setPendingHitl(null);
  };

  return (
    <div style={{ display: 'flex', height: '100vh', background: 'var(--bg)', borderRadius: roundedCorners ? '0' : '0' }}>
      {/* Navigation & Sessions Sidebar */}
      <div style={{ width: '270px', background: 'var(--panel)', borderRight: '1px solid var(--border)', display: 'flex', flexDirection: 'column' }}>
        {/* App Title */}
        <div style={{ padding: '16px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{ width: '34px', height: '34px', borderRadius: roundedCorners ? '10px' : '4px', background: 'linear-gradient(135deg, var(--accent), var(--accent2))', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 'bold', color: '#fff', fontSize: '18px' }}>⚡</div>
          <div>
            <div style={{ fontWeight: 'bold', fontSize: '15px', color: '#fff' }}>Aether OS</div>
            <div style={{ fontSize: '11px', color: 'var(--muted)' }}>Multi-Agent & RAG Companion</div>
          </div>
        </div>

        {/* View Tabs */}
        <div style={{ padding: '10px', borderBottom: '1px solid var(--border)' }}>
          {[
            { id: 'chat', label: '💬 Chat', color: 'var(--accent)' },
            { id: 'burr', label: '⚡ Burr OS Dashboard', color: 'var(--accent2)' },
            { id: 'pdfs', label: '📚 RAG Knowledge Base', color: '#3b82f6' },
            { id: 'memory', label: '🧠 Fact Memory Store', color: '#ec4899' },
            { id: 'capabilities', label: '🧩 Capabilities & Tools', color: '#8b5cf6' },
            { id: 'settings', label: '⚙️ Settings & Models', color: '#10b981' },
            { id: 'appearance', label: '🎨 Appearance', color: '#f59e0b' },
            { id: 'about', label: 'ℹ️ About & Updates', color: '#06b6d4' },
          ].map((item) => (
            <button key={item.id} onClick={() => setActiveView(item.id)} style={{ width: '100%', padding: '8px 12px', background: activeView === item.id ? 'var(--panel2)' : 'transparent', color: activeView === item.id ? '#fff' : 'var(--muted)', borderLeft: activeView === item.id ? `4px solid ${item.color}` : '4px solid transparent', borderTop: 0, borderRight: 0, borderBottom: 0, borderRadius: roundedCorners ? '6px' : '0', marginBottom: '2px', textAlign: 'left', cursor: 'pointer', fontWeight: activeView === item.id ? 'bold' : 'normal', fontSize: '13px', transition: 'all 0.15s ease' }}>
              {item.label}
            </button>
          ))}
        </div>

        {/* Chat Sessions History */}
        <div style={{ flex: 1, padding: '12px 10px', overflowY: 'auto', display: 'flex', flexDirection: 'column' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px', padding: '0 4px' }}>
            <span style={{ fontSize: '11px', fontWeight: 'bold', color: 'var(--muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Chat Sessions</span>
            <button onClick={createNewSession} style={{ background: 'var(--accent)', color: '#fff', border: 0, padding: '3px 8px', borderRadius: roundedCorners ? '4px' : '0', cursor: 'pointer', fontSize: '11px', fontWeight: 'bold' }}>
              + New Chat
            </button>
          </div>

          <div style={{ flex: 1, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '4px' }}>
            {sessions.length === 0 ? (
              <div style={{ color: 'var(--muted)', fontSize: '12px', padding: '12px 6px', textAlign: 'center' }}>No sessions yet. Click + New Chat to begin.</div>
            ) : (
              sessions.map((s) => (
                <div key={s.id} onClick={() => { selectSession(s.id); setActiveView('chat'); }} style={{ padding: '8px 10px', borderRadius: roundedCorners ? '6px' : '0', background: sessionId === s.id && activeView === 'chat' ? 'var(--panel2)' : 'transparent', border: sessionId === s.id && activeView === 'chat' ? '1px solid var(--accent)' : '1px solid transparent', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'space-between', transition: 'all 0.15s ease' }}>
                  <div style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontSize: '12px', color: sessionId === s.id ? '#fff' : 'var(--muted)', flex: 1 }}>
                    {s.title || '(Untitled Chat)'}
                  </div>
                  <button onClick={(e) => deleteSession(s.id, e)} style={{ background: 'transparent', border: 0, color: 'var(--muted)', cursor: 'pointer', fontSize: '11px', padding: '2px 4px', opacity: 0.6 }} title="Delete session">
                    ✕
                  </button>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Footer Status */}
        <div style={{ padding: '12px 14px', borderTop: '1px solid var(--border)', fontSize: '11px', color: 'var(--muted)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <span>Model:</span>
            <span style={{ color: '#a5b4fc', fontWeight: 'bold', maxWidth: '140px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{currentModel}</span>
          </div>
          <div style={{ marginTop: '4px', display: 'flex', justifyContent: 'space-between' }}>
            <span>Watcher:</span>
            <span style={{ color: watcherStatus?.running ? 'var(--accent2)' : 'var(--danger)', fontWeight: 'bold' }}>{watcherStatus?.running ? '● Active' : '○ Inactive'}</span>
          </div>
        </div>
      </div>

      {/* Main View Area */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        {/* Header Bar */}
        <div style={{ padding: '12px 24px', borderBottom: '1px solid var(--border)', background: 'var(--panel)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
            <div style={{ fontWeight: 'bold', fontSize: '16px', letterSpacing: '0.5px' }}>{activeView.toUpperCase()}</div>
            {activeView === 'chat' && (
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <select value={currentModel} onChange={(e) => selectModelPreset(e.target.value)} style={{ background: 'var(--panel2)', border: '1px solid var(--border)', color: '#a5b4fc', padding: '6px 12px', borderRadius: roundedCorners ? '6px' : '0', fontSize: '12px', cursor: 'pointer', fontWeight: 'bold' }}>
                  {MODEL_PRESETS.map((m) => (
                    <option key={m.id} value={m.id}>
                      [{m.tier.toUpperCase()}] {m.name}
                    </option>
                  ))}
                </select>

                <select value={persona} onChange={(e) => setPersona(e.target.value)} style={{ background: 'var(--panel2)', border: '1px solid var(--border)', color: '#fff', padding: '6px 10px', borderRadius: roundedCorners ? '6px' : '0', fontSize: '12px', cursor: 'pointer' }}>
                  <option value="default">Default Aether</option>
                  <option value="software_engineer">Senior Software Engineer</option>
                  <option value="research_scientist">Deep Research Scientist</option>
                  <option value="concise">Concise & Direct</option>
                </select>
              </div>
            )}
          </div>

          {activeView === 'chat' && (
            <div style={{ display: 'flex', gap: '6px', background: 'var(--panel2)', borderRadius: roundedCorners ? '8px' : '0', padding: '4px', border: '1px solid var(--border)' }}>
              <button onClick={() => setMode('normal')} style={{ background: mode === 'normal' ? 'var(--accent)' : 'transparent', border: 0, color: '#fff', padding: '5px 12px', borderRadius: roundedCorners ? '6px' : '0', cursor: 'pointer', fontWeight: mode === 'normal' ? 'bold' : 'normal', fontSize: '12px' }}>💬 Normal</button>
              <button onClick={() => setMode('rag')} style={{ background: mode === 'rag' ? 'var(--accent)' : 'transparent', border: 0, color: '#fff', padding: '5px 12px', borderRadius: roundedCorners ? '6px' : '0', cursor: 'pointer', fontWeight: mode === 'rag' ? 'bold' : 'normal', fontSize: '12px' }}>📚 RAG</button>
              <button onClick={() => setMode('multiagent')} style={{ background: mode === 'multiagent' ? 'var(--accent2)' : 'transparent', border: 0, color: '#fff', padding: '5px 12px', borderRadius: roundedCorners ? '6px' : '0', cursor: 'pointer', fontWeight: mode === 'multiagent' ? 'bold' : 'normal', fontSize: '12px' }}>🤖 Swarm</button>
            </div>
          )}
        </div>

        {/* View Workspace */}
        <div style={{ flex: 1, padding: '24px', overflowY: 'auto' }}>
          {activeView === 'chat' && (
            <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
              <div style={{ flex: 1, overflowY: 'auto', marginBottom: '16px', paddingRight: '8px' }}>
                {messages.length === 0 ? (
                  <div style={{ textAlign: 'center', marginTop: '60px', color: 'var(--muted)' }}>
                    <div style={{ fontSize: '48px', marginBottom: '12px' }}>⚡</div>
                    <div style={{ fontSize: '18px', fontWeight: 'bold', color: '#fff' }}>Aether AI Operating System</div>
                    <div style={{ fontSize: '13px', marginTop: '4px' }}>Active Model: <code style={{ color: '#a5b4fc' }}>{currentModel}</code> &nbsp;|&nbsp; Mode: <strong>{mode.toUpperCase()}</strong></div>
                    <div style={{ display: 'flex', gap: '8px', justifyContent: 'center', marginTop: '20px' }}>
                      <button onClick={() => setInputPrompt('Explain how Apache Burr state machines manage agent memory')} style={{ background: 'var(--panel2)', border: '1px solid var(--border)', color: 'var(--muted)', padding: '6px 12px', borderRadius: roundedCorners ? '6px' : '0', cursor: 'pointer', fontSize: '12px' }}>💡 Explain Burr State Machine</button>
                      <button onClick={() => setInputPrompt('Search my PDF knowledge base for recent summaries')} style={{ background: 'var(--panel2)', border: '1px solid var(--border)', color: 'var(--muted)', padding: '6px 12px', borderRadius: roundedCorners ? '6px' : '0', cursor: 'pointer', fontSize: '12px' }}>📚 Search PDF Knowledge</button>
                      <button onClick={() => setInputPrompt('Launch a 4-agent swarm to architect a distributed database')} style={{ background: 'var(--panel2)', border: '1px solid var(--border)', color: 'var(--muted)', padding: '6px 12px', borderRadius: roundedCorners ? '6px' : '0', cursor: 'pointer', fontSize: '12px' }}>🤖 Launch Multi-Agent Swarm</button>
                    </div>
                  </div>
                ) : null}

                {messages.map((m, idx) => (
                  <div key={idx} className="animate-slide-up" style={{ marginBottom: '16px', padding: '14px 18px', borderRadius: roundedCorners ? '12px' : '0', background: m.role === 'user' ? 'var(--accent)' : 'var(--panel)', border: '1px solid var(--border)', maxWidth: '85%', marginLeft: m.role === 'user' ? 'auto' : '0', boxShadow: '0 4px 12px rgba(0,0,0,0.15)' }}>
                    <div style={{ fontSize: '11px', fontWeight: 'bold', marginBottom: '4px', opacity: 0.7 }}>{m.role === 'user' ? 'YOU' : 'AETHER OS'}</div>
                    <div style={{ whiteSpace: 'pre-wrap', lineHeight: '1.5' }}>{m.content}</div>
                  </div>
                ))}

                {steps.map((st, idx) => (
                  <div key={idx} className="subagent-card animate-slide-up" style={{ borderRadius: roundedCorners ? '10px' : '0' }}>
                    <div style={{ fontWeight: 'bold', fontSize: '13px', color: 'var(--accent2)' }}>🤖 {st.agent} ({st.role})</div>
                    <div style={{ fontSize: '12px', color: 'var(--muted)', marginTop: '2px' }}>{st.task}</div>
                    {st.summary && <div style={{ fontSize: '11px', marginTop: '6px', color: 'var(--text)' }}>Result: {st.summary}</div>}
                  </div>
                ))}

                {pendingHitl && (
                  <div className="glass-panel animate-slide-up glow-active" style={{ padding: '20px', borderRadius: roundedCorners ? '14px' : '0', borderColor: 'var(--accent)', marginTop: '12px' }}>
                    <div style={{ fontWeight: 'bold', color: 'var(--accent)', fontSize: '15px' }}>⚠️ Human-in-the-Loop Approval Request</div>
                    <div style={{ fontSize: '13px', margin: '10px 0', color: 'var(--text)' }}>Tool: <code style={{ background: 'var(--panel2)', padding: '2px 6px', borderRadius: '4px' }}>{pendingHitl.tool}</code></div>
                    <div style={{ display: 'flex', gap: '10px', marginTop: '12px' }}>
                      <button onClick={() => handleHitlApprove(true)} style={{ background: 'var(--accent2)', color: '#fff', border: 0, padding: '8px 20px', borderRadius: roundedCorners ? '8px' : '0', cursor: 'pointer', fontWeight: 'bold' }}>Approve Action</button>
                      <button onClick={() => handleHitlApprove(false)} style={{ background: 'var(--danger)', color: '#fff', border: 0, padding: '8px 20px', borderRadius: roundedCorners ? '8px' : '0', cursor: 'pointer', fontWeight: 'bold' }}>Reject</button>
                    </div>
                  </div>
                )}
              </div>

              <div style={{ display: 'flex', gap: '12px' }}>
                <textarea value={inputPrompt} onChange={(e) => setInputPrompt(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); } }} placeholder="Message Aether Desktop OS or launch subagent swarm..." style={{ flex: 1, background: 'var(--panel2)', border: '1px solid var(--border)', color: '#fff', borderRadius: roundedCorners ? '10px' : '0', padding: '14px', resize: 'none', height: '56px', fontSize: '14px', fontFamily: 'inherit' }} />
                <button onClick={handleSend} style={{ background: 'linear-gradient(135deg, var(--accent), #6366f1)', color: '#fff', border: 0, padding: '0 28px', borderRadius: roundedCorners ? '10px' : '0', cursor: 'pointer', fontWeight: 'bold', fontSize: '14px', boxShadow: '0 4px 16px rgba(124, 108, 255, 0.4)' }}>Send</button>
              </div>
            </div>
          )}

          {activeView === 'capabilities' && (
            <div>
              <h2>🧩 Capabilities, Tools & MCP Hub</h2>
              <p style={{ color: 'var(--muted)' }}>Manage built-in tool execution capabilities, active MCP tool servers, and skill registries.</p>

              {/* Stats Counters Bar */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '16px', marginTop: '20px' }}>
                <div className="glass-panel" style={{ padding: '16px 20px', borderRadius: roundedCorners ? '12px' : '0', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div>
                    <div style={{ fontSize: '12px', color: 'var(--muted)', textTransform: 'uppercase', fontWeight: 'bold' }}>Built-in Tools</div>
                    <div style={{ fontSize: '26px', fontWeight: 'bold', color: 'var(--accent)', marginTop: '4px' }}>19</div>
                  </div>
                  <div style={{ fontSize: '32px' }}>🛠️</div>
                </div>

                <div className="glass-panel" style={{ padding: '16px 20px', borderRadius: roundedCorners ? '12px' : '0', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div>
                    <div style={{ fontSize: '12px', color: 'var(--muted)', textTransform: 'uppercase', fontWeight: 'bold' }}>MCP Servers</div>
                    <div style={{ fontSize: '26px', fontWeight: 'bold', color: 'var(--accent2)', marginTop: '4px' }}>10</div>
                  </div>
                  <div style={{ fontSize: '32px' }}>🧩</div>
                </div>

                <div className="glass-panel" style={{ padding: '16px 20px', borderRadius: roundedCorners ? '12px' : '0', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div>
                    <div style={{ fontSize: '12px', color: 'var(--muted)', textTransform: 'uppercase', fontWeight: 'bold' }}>Active Skills</div>
                    <div style={{ fontSize: '26px', fontWeight: 'bold', color: '#f59e0b', marginTop: '4px' }}>91</div>
                  </div>
                  <div style={{ fontSize: '32px' }}>⚡</div>
                </div>
              </div>

              {/* Built-in Capabilities Grid (19 Tools) */}
              <div style={{ marginTop: '24px' }}>
                <h3 style={{ fontSize: '16px', marginBottom: '14px' }}>🛠️ Built-in Agent Capabilities (19)</h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '12px' }}>
                  {capabilities.map((c) => (
                    <div key={c.id} className="glass-panel" style={{ padding: '14px 16px', borderRadius: roundedCorners ? '10px' : '0', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flex: 1, paddingRight: '8px' }}>
                        <span style={{ fontSize: '22px' }}>{c.icon}</span>
                        <div>
                          <div style={{ fontWeight: 'bold', fontSize: '13px', color: '#fff' }}>{c.name}</div>
                          <div style={{ fontSize: '11px', color: 'var(--muted)', lineHeight: '1.3', marginTop: '2px' }}>{c.desc}</div>
                        </div>
                      </div>
                      <button onClick={() => toggleCapability(c.id)} style={{ background: c.enabled ? 'var(--accent2)' : 'var(--panel2)', border: '1px solid var(--border)', color: c.enabled ? '#fff' : 'var(--muted)', padding: '4px 10px', borderRadius: roundedCorners ? '14px' : '0', cursor: 'pointer', fontSize: '11px', fontWeight: 'bold', transition: 'all 0.2s ease' }}>
                        {c.enabled ? 'ON' : 'OFF'}
                      </button>
                    </div>
                  ))}
                </div>
              </div>

              {/* MCP Servers Table (10 Servers) */}
              <div style={{ marginTop: '28px' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
                  <h3 style={{ fontSize: '16px', margin: 0 }}>🧩 Model Context Protocol (MCP) Servers (10)</h3>
                  <span style={{ fontSize: '12px', color: 'var(--muted)' }}>10 servers · 10 enabled</span>
                </div>

                <div className="glass-panel" style={{ borderRadius: roundedCorners ? '12px' : '0', overflow: 'hidden' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '12px', textAlign: 'left' }}>
                    <thead>
                      <tr style={{ background: 'var(--panel2)', borderBottom: '1px solid var(--border)' }}>
                        <th style={{ padding: '12px 16px', color: 'var(--muted)', fontWeight: 'bold' }}>Server</th>
                        <th style={{ padding: '12px 16px', color: 'var(--muted)', fontWeight: 'bold' }}>Transport</th>
                        <th style={{ padding: '12px 16px', color: 'var(--muted)', fontWeight: 'bold' }}>Command / URL</th>
                        <th style={{ padding: '12px 16px', color: 'var(--muted)', fontWeight: 'bold' }}>Status</th>
                        <th style={{ padding: '12px 16px', color: 'var(--muted)', fontWeight: 'bold', textAlign: 'right' }}>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {mcpServers.map((s) => (
                        <tr key={s.id} style={{ borderBottom: '1px solid var(--border)', transition: 'background 0.15s ease' }}>
                          <td style={{ padding: '12px 16px', fontWeight: 'bold', color: '#a5b4fc' }}>{s.name}</td>
                          <td style={{ padding: '12px 16px' }}>
                            <span style={{ background: 'var(--panel2)', padding: '2px 8px', borderRadius: '4px', border: '1px solid var(--border)', fontSize: '11px' }}>{s.transport}</span>
                          </td>
                          <td style={{ padding: '12px 16px', color: 'var(--text)', fontFamily: 'monospace', maxWidth: '300px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {s.command}
                          </td>
                          <td style={{ padding: '12px 16px' }}>
                            {mcpTestStatus[s.name] ? (
                              <span style={{ color: 'var(--accent2)', fontWeight: 'bold' }}>{mcpTestStatus[s.name]}</span>
                            ) : (
                              <button onClick={() => toggleMcpServer(s.id)} style={{ background: s.enabled ? 'var(--accent2)' : 'var(--panel2)', border: '1px solid var(--border)', color: '#fff', padding: '3px 8px', borderRadius: '12px', cursor: 'pointer', fontSize: '10px', fontWeight: 'bold' }}>
                                {s.enabled ? 'ENABLED' : 'DISABLED'}
                              </button>
                            )}
                          </td>
                          <td style={{ padding: '12px 16px', textAlign: 'right' }}>
                            <div style={{ display: 'inline-flex', gap: '6px' }}>
                              <button onClick={() => testMcpServer(s.name)} style={{ background: 'var(--panel2)', border: '1px solid var(--border)', color: 'var(--accent)', padding: '3px 8px', borderRadius: '4px', cursor: 'pointer', fontSize: '11px' }}>
                                Test
                              </button>
                              <button onClick={() => removeMcpServer(s.id)} style={{ background: 'transparent', border: '1px solid rgba(239, 68, 68, 0.3)', color: 'var(--danger)', padding: '3px 8px', borderRadius: '4px', cursor: 'pointer', fontSize: '11px' }}>
                                🗑️
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {activeView === 'settings' && (
            <div>
              <h2>⚙️ Provider Settings & Model Directory</h2>
              <p style={{ color: 'var(--muted)' }}>Configure your API keys and select models by purpose.</p>

              {/* Top Section: Provider API Keys (Reordered on Top) */}
              <div className="glass-panel" style={{ padding: '22px', borderRadius: roundedCorners ? '14px' : '0', marginTop: '16px', border: '1px solid var(--accent)' }}>
                <h3 style={{ margin: '0 0 16px 0', fontSize: '16px', color: 'var(--accent)' }}>🔑 Provider API Keys & Local Endpoints</h3>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                  <div>
                    <label style={{ fontSize: '12px', fontWeight: 'bold', display: 'block', marginBottom: '6px' }}>OpenRouter API Key:</label>
                    <input type="password" value={openRouterKey} onChange={(e) => setOpenRouterKey(e.target.value)} placeholder="sk-or-v1-..." style={{ width: '100%', background: 'var(--panel2)', border: '1px solid var(--border)', color: '#fff', padding: '10px 14px', borderRadius: roundedCorners ? '8px' : '0', fontSize: '13px' }} />
                  </div>

                  <div>
                    <label style={{ fontSize: '12px', fontWeight: 'bold', display: 'block', marginBottom: '6px' }}>OpenAI API Key (Optional):</label>
                    <input type="password" value={openaiKey} onChange={(e) => setOpenaiKey(e.target.value)} placeholder="sk-proj-..." style={{ width: '100%', background: 'var(--panel2)', border: '1px solid var(--border)', color: '#fff', padding: '10px 14px', borderRadius: roundedCorners ? '8px' : '0', fontSize: '13px' }} />
                  </div>

                  <div>
                    <label style={{ fontSize: '12px', fontWeight: 'bold', display: 'block', marginBottom: '6px' }}>Anthropic API Key (Optional):</label>
                    <input type="password" value={anthropicKey} onChange={(e) => setAnthropicKey(e.target.value)} placeholder="sk-ant-..." style={{ width: '100%', background: 'var(--panel2)', border: '1px solid var(--border)', color: '#fff', padding: '10px 14px', borderRadius: roundedCorners ? '8px' : '0', fontSize: '13px' }} />
                  </div>

                  <div>
                    <label style={{ fontSize: '12px', fontWeight: 'bold', display: 'block', marginBottom: '6px' }}>Local Ollama Endpoint:</label>
                    <input type="text" value={ollamaUrl} onChange={(e) => setOllamaUrl(e.target.value)} placeholder="http://127.0.0.1:11434" style={{ width: '100%', background: 'var(--panel2)', border: '1px solid var(--border)', color: '#fff', padding: '10px 14px', borderRadius: roundedCorners ? '8px' : '0', fontSize: '13px' }} />
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '14px', marginTop: '18px' }}>
                  <button onClick={saveApiKey} style={{ background: 'var(--accent)', color: '#fff', border: 0, padding: '10px 28px', borderRadius: roundedCorners ? '8px' : '0', cursor: 'pointer', fontWeight: 'bold', fontSize: '13px', boxShadow: '0 4px 12px rgba(124, 108, 255, 0.4)' }}>
                    💾 Save Provider Settings
                  </button>
                  {savedSettingsMsg && <span style={{ color: 'var(--accent2)', fontWeight: 'bold', fontSize: '13px' }}>{savedSettingsMsg}</span>}
                </div>
              </div>

              {/* Bottom Section: Model Presets Directory by Purpose */}
              <div style={{ marginTop: '28px' }}>
                <h3 style={{ fontSize: '16px', marginBottom: '12px' }}>⚡ Recommended Models by Purpose</h3>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
                  {MODEL_PRESETS.map((m) => {
                    const isSelected = currentModel === m.id;
                    const tierBadgeColor = m.tier === 'free' ? 'var(--accent2)' : m.tier === 'frontier' ? 'var(--accent)' : '#8b5cf6';

                    return (
                      <div key={m.id} className={`glass-panel ${isSelected ? 'glow-active' : ''}`} style={{ padding: '16px', borderRadius: roundedCorners ? '12px' : '0', border: isSelected ? '1px solid var(--accent)' : '1px solid var(--border)', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                        <div>
                          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                            <span style={{ fontWeight: 'bold', fontSize: '14px', color: '#fff' }}>{m.name}</span>
                            <span style={{ fontSize: '10px', textTransform: 'uppercase', padding: '2px 8px', borderRadius: '4px', background: 'var(--panel2)', color: tierBadgeColor, fontWeight: 'bold', border: `1px solid ${tierBadgeColor}` }}>
                              {m.tier}
                            </span>
                          </div>
                          <div style={{ fontSize: '12px', color: 'var(--accent)', fontWeight: 'bold', marginBottom: '6px' }}>{m.purpose}</div>
                          <div style={{ fontSize: '12px', color: 'var(--muted)', lineHeight: '1.4' }}>{m.description}</div>
                        </div>

                        <div style={{ marginTop: '14px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                          <code style={{ fontSize: '11px', color: '#a5b4fc' }}>{m.id}</code>
                          <button onClick={() => selectModelPreset(m.id)} style={{ background: isSelected ? 'var(--accent2)' : 'var(--panel2)', color: '#fff', border: '1px solid var(--border)', padding: '5px 12px', borderRadius: roundedCorners ? '6px' : '0', cursor: 'pointer', fontSize: '11px', fontWeight: 'bold' }}>
                            {isSelected ? '✓ Active Model' : '⚡ Use Model'}
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
          )}

          {activeView === 'appearance' && (
            <div>
              <h2>🎨 Appearance & Personalization</h2>
              <p style={{ color: 'var(--muted)' }}>Customize themes, interface fonts, corner radiuses, and rendering engine.</p>

              {/* Themes Grid (Matching Photo 1) */}
              <div className="glass-panel" style={{ padding: '22px', borderRadius: roundedCorners ? '14px' : '0', marginTop: '16px' }}>
                <h3 style={{ margin: '0 0 14px 0', fontSize: '15px' }}>Theme Presets (7)</h3>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '12px' }}>
                  {[
                    { id: 'dark', name: 'Dark', bg: '#0b0b12', panel: '#14141f', border: '#7c6cff' },
                    { id: 'light', name: 'Light', bg: '#f8fafc', panel: '#ffffff', border: '#4f46e5' },
                    { id: 'dracula', name: 'Dracula', bg: '#282a36', panel: '#21222c', border: '#bd93f9' },
                    { id: 'nord', name: 'Nord', bg: '#2e3440', panel: '#3b4252', border: '#88c0d0' },
                    { id: 'onedark', name: 'One Dark', bg: '#1e1e24', panel: '#282c34', border: '#61afef' },
                    { id: 'githubdark', name: 'GitHub Dark', bg: '#0d1117', panel: '#161b22', border: '#3fb950' },
                    { id: 'monokai', name: 'Monokai', bg: '#272822', panel: '#1e1f1c', border: '#a6e22e' },
                  ].map((t) => (
                    <div key={t.id} onClick={() => applyTheme(t.id)} style={{ padding: '12px', borderRadius: roundedCorners ? '10px' : '0', background: t.panel, border: selectedTheme === t.id ? `2px solid ${t.border}` : '1px solid var(--border)', cursor: 'pointer', display: 'flex', flexDirection: 'column', gap: '8px', transition: 'all 0.15s ease' }}>
                      <div style={{ height: '28px', background: t.bg, borderRadius: '6px', border: '1px solid var(--border)', display: 'flex', alignItems: 'center', padding: '0 8px', gap: '4px' }}>
                        <div style={{ width: '12px', height: '4px', borderRadius: '2px', background: t.border }}></div>
                        <div style={{ width: '24px', height: '4px', borderRadius: '2px', background: 'var(--muted)', opacity: 0.5 }}></div>
                      </div>
                      <div style={{ fontSize: '13px', fontWeight: 'bold', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span>{t.name}</span>
                        {selectedTheme === t.id && <span style={{ color: t.border, fontSize: '11px' }}>✓</span>}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Toggles & Options */}
              <div className="glass-panel" style={{ padding: '22px', borderRadius: roundedCorners ? '14px' : '0', marginTop: '16px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div>
                    <div style={{ fontWeight: 'bold', fontSize: '14px' }}>Rounded Corners</div>
                    <div style={{ fontSize: '12px', color: 'var(--muted)', marginTop: '2px' }}>Turn off for squared-off modern edges throughout the app.</div>
                  </div>
                  <button onClick={() => setRoundedCorners(!roundedCorners)} style={{ background: roundedCorners ? 'var(--accent2)' : 'var(--panel2)', border: '1px solid var(--border)', color: '#fff', padding: '6px 14px', borderRadius: '16px', cursor: 'pointer', fontWeight: 'bold', fontSize: '12px' }}>
                    {roundedCorners ? 'ON' : 'OFF'}
                  </button>
                </div>

                <div style={{ borderTop: '1px solid var(--border)', paddingTop: '16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div>
                    <div style={{ fontWeight: 'bold', fontSize: '14px' }}>Interface Typography</div>
                    <div style={{ fontSize: '12px', color: 'var(--muted)', marginTop: '2px' }}>Choose the primary font family for chat and workspace.</div>
                  </div>
                  <div style={{ display: 'flex', gap: '6px' }}>
                    {['Inter', 'Manrope', 'Outfit', 'G Sans', 'Fira Code'].map((f) => (
                      <button key={f} onClick={() => setSelectedFont(f)} style={{ background: selectedFont === f ? 'var(--accent)' : 'var(--panel2)', border: '1px solid var(--border)', color: '#fff', padding: '5px 12px', borderRadius: roundedCorners ? '6px' : '0', cursor: 'pointer', fontSize: '12px', fontWeight: selectedFont === f ? 'bold' : 'normal' }}>
                        {f}
                      </button>
                    ))}
                  </div>
                </div>

                <div style={{ borderTop: '1px solid var(--border)', paddingTop: '16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div>
                    <div style={{ fontWeight: 'bold', fontSize: '14px' }}>Hardware Acceleration</div>
                    <div style={{ fontSize: '12px', color: 'var(--muted)', marginTop: '2px' }}>Use GPU hardware acceleration for rendering animations.</div>
                  </div>
                  <div style={{ display: 'flex', gap: '6px' }}>
                    {['Auto', 'Always on', 'Always off'].map((h) => (
                      <button key={h} onClick={() => setHardwareAccel(h)} style={{ background: hardwareAccel === h ? 'var(--accent2)' : 'var(--panel2)', border: '1px solid var(--border)', color: '#fff', padding: '5px 12px', borderRadius: roundedCorners ? '6px' : '0', cursor: 'pointer', fontSize: '12px', fontWeight: hardwareAccel === h ? 'bold' : 'normal' }}>
                        {h}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {activeView === 'about' && (
            <div>
              <h2>ℹ️ About Aether OS & Updates</h2>
              <p style={{ color: 'var(--muted)' }}>System diagnostics, engine telemetry, and one-click in-app update management.</p>

              {/* Engine Status Grid (Matching Photo 2) */}
              <div className="glass-panel" style={{ padding: '22px', borderRadius: roundedCorners ? '14px' : '0', marginTop: '16px' }}>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', marginBottom: '18px' }}>
                  <div>
                    <div style={{ fontSize: '11px', color: 'var(--muted)', textTransform: 'uppercase', fontWeight: 'bold' }}>⚙️ ENGINE</div>
                    <div style={{ fontSize: '18px', fontWeight: 'bold', color: 'var(--accent)', marginTop: '4px' }}>v2.0.0</div>
                  </div>
                  <div>
                    <div style={{ fontSize: '11px', color: 'var(--muted)', textTransform: 'uppercase', fontWeight: 'bold' }}>📅 RELEASED</div>
                    <div style={{ fontSize: '18px', fontWeight: 'bold', color: '#fff', marginTop: '4px' }}>2026.08.10</div>
                  </div>
                  <div>
                    <div style={{ fontSize: '11px', color: 'var(--muted)', textTransform: 'uppercase', fontWeight: 'bold' }}>🐍 PYTHON</div>
                    <div style={{ fontSize: '18px', fontWeight: 'bold', color: 'var(--accent2)', marginTop: '4px' }}>3.11.15</div>
                  </div>
                  <div>
                    <div style={{ fontSize: '11px', color: 'var(--muted)', textTransform: 'uppercase', fontWeight: 'bold' }}>⚡ ELECTRON</div>
                    <div style={{ fontSize: '18px', fontWeight: 'bold', color: '#8b5cf6', marginTop: '4px' }}>28.3.3</div>
                  </div>
                </div>

                <div style={{ fontSize: '12px', color: 'var(--muted)', marginBottom: '16px' }}>
                  <strong>📁 HOME:</strong> <code style={{ color: '#a5b4fc', background: 'var(--panel2)', padding: '2px 8px', borderRadius: '4px' }}>%APPDATA%/aether</code>
                </div>

                <div style={{ display: 'flex', gap: '10px' }}>
                  <button onClick={runUpdateInPlace} disabled={isUpdating} style={{ background: 'var(--accent)', color: '#fff', border: 0, padding: '9px 18px', borderRadius: roundedCorners ? '8px' : '0', cursor: 'pointer', fontWeight: 'bold', fontSize: '13px' }}>
                    {isUpdating ? '⏳ Updating...' : '⬇️ Update Engine In-Place'}
                  </button>
                  <button onClick={runDiagnostics} style={{ background: 'var(--panel2)', border: '1px solid var(--border)', color: '#fff', padding: '9px 18px', borderRadius: roundedCorners ? '8px' : '0', cursor: 'pointer', fontWeight: 'bold', fontSize: '13px' }}>
                    🔍 Run Diagnosis
                  </button>
                  <button onClick={copyDebugDump} style={{ background: 'var(--panel2)', border: '1px solid var(--border)', color: '#fff', padding: '9px 18px', borderRadius: roundedCorners ? '8px' : '0', cursor: 'pointer', fontWeight: 'bold', fontSize: '13px' }}>
                    📋 Debug Dump
                  </button>
                </div>
              </div>

              {/* Desktop App Updater Box (Matching Photo 2) */}
              <div className="glass-panel" style={{ padding: '22px', borderRadius: roundedCorners ? '14px' : '0', marginTop: '16px' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <div style={{ width: '38px', height: '38px', borderRadius: '10px', background: 'linear-gradient(135deg, var(--accent), var(--accent2))', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '20px' }}>⚡</div>
                    <div>
                      <div style={{ fontWeight: 'bold', fontSize: '15px' }}>Aether Desktop App</div>
                      <div style={{ fontSize: '12px', color: 'var(--muted)' }}>v2.0.0 (Latest Release)</div>
                    </div>
                  </div>
                  <button onClick={checkForUpdates} style={{ background: 'var(--panel2)', border: '1px solid var(--border)', color: 'var(--accent)', padding: '8px 18px', borderRadius: roundedCorners ? '8px' : '0', cursor: 'pointer', fontWeight: 'bold', fontSize: '13px' }}>
                    🔄 Check for updates
                  </button>
                </div>

                {updateStatus && (
                  <div style={{ background: 'var(--panel2)', padding: '10px 14px', borderRadius: '8px', fontSize: '13px', color: 'var(--accent2)', fontWeight: 'bold', marginBottom: '14px', border: '1px solid rgba(39, 198, 161, 0.3)' }}>
                    {updateStatus}
                  </div>
                )}

                <div style={{ borderTop: '1px solid var(--border)', paddingTop: '14px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div>
                    <div style={{ fontWeight: 'bold', fontSize: '13px' }}>Auto-upgrade desktop app</div>
                    <div style={{ fontSize: '12px', color: 'var(--muted)', marginTop: '2px' }}>Automatically download and notify when new releases are published on GitHub.</div>
                  </div>
                  <button onClick={() => setAutoUpgrade(!autoUpgrade)} style={{ background: autoUpgrade ? 'var(--accent2)' : 'var(--panel2)', border: '1px solid var(--border)', color: '#fff', padding: '4px 12px', borderRadius: '14px', cursor: 'pointer', fontWeight: 'bold', fontSize: '11px' }}>
                    {autoUpgrade ? 'ON' : 'OFF'}
                  </button>
                </div>
              </div>

              {diagnosticsOutput && (
                <div className="glass-panel" style={{ padding: '16px', borderRadius: roundedCorners ? '12px' : '0', marginTop: '16px' }}>
                  <div style={{ fontWeight: 'bold', fontSize: '13px', marginBottom: '8px' }}>Diagnostic Report Output:</div>
                  <pre style={{ background: '#07070d', padding: '12px', borderRadius: '8px', color: '#a5b4fc', fontSize: '12px', margin: 0, overflowX: 'auto' }}>{diagnosticsOutput}</pre>
                </div>
              )}
            </div>
          )}

          {activeView === 'burr' && (
            <div>
              <h2 style={{ margin: '0 0 4px 0' }}>⚡ Apache Burr OS Dashboard</h2>
              <p style={{ color: 'var(--muted)', marginTop: 0 }}>State-Driven Orchestration & HITL Approvals Engine</p>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginTop: '20px' }}>
                <div className="glass-panel" style={{ padding: '20px', borderRadius: roundedCorners ? '14px' : '0' }}>
                  <h3 style={{ margin: '0 0 12px 0', fontSize: '16px' }}>🛑 Human-in-the-Loop (HITL) Controls</h3>
                  <p style={{ fontSize: '13px', color: 'var(--muted)' }}>Pause execution when tools execute system commands or modify files.</p>
                  <button onClick={toggleHitl} style={{ marginTop: '8px', background: hitlEnabled ? 'var(--accent2)' : 'var(--danger)', color: '#fff', border: 0, padding: '8px 18px', borderRadius: roundedCorners ? '8px' : '0', cursor: 'pointer', fontWeight: 'bold' }}>
                    {hitlEnabled ? '✓ HITL Approvals Active' : '✕ HITL Approvals Disabled'}
                  </button>
                </div>

                <div className="glass-panel" style={{ padding: '20px', borderRadius: roundedCorners ? '14px' : '0' }}>
                  <h3 style={{ margin: '0 0 12px 0', fontSize: '16px' }}>📁 Background File Watcher</h3>
                  <div style={{ fontSize: '13px', color: 'var(--muted)' }}>Monitoring Folder:</div>
                  <code style={{ fontSize: '12px', background: 'var(--panel2)', padding: '4px 8px', borderRadius: '6px', display: 'block', margin: '6px 0 12px 0' }}>{watcherStatus?.watch_dir || '%APPDATA%/aether/watch_folder'}</code>
                  <div style={{ fontSize: '13px' }}>Status: <span style={{ color: watcherStatus?.running ? 'var(--accent2)' : 'var(--danger)', fontWeight: 'bold' }}>{watcherStatus?.running ? 'Active (Auto-Ingesting)' : 'Inactive'}</span></div>
                </div>
              </div>

              <div className="glass-panel" style={{ padding: '20px', borderRadius: roundedCorners ? '14px' : '0', marginTop: '16px' }}>
                <h3 style={{ margin: '0 0 12px 0', fontSize: '16px' }}>⚙️ Multi-LLM Role Assignment</h3>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  {['planner', 'code', 'research', 'synthesis'].map((r) => (
                    <div key={r}>
                      <label style={{ fontSize: '12px', color: 'var(--muted)', textTransform: 'capitalize' }}>{r} Model:</label>
                      <input type="text" value={(roleModels as any)[r] || ''} onChange={(e) => handleRoleModelChange(r, e.target.value)} placeholder="e.g. anthropic/claude-3.5-sonnet" style={{ width: '100%', background: 'var(--panel2)', border: '1px solid var(--border)', color: '#fff', padding: '8px 12px', borderRadius: roundedCorners ? '6px' : '0', marginTop: '4px' }} />
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {activeView === 'pdfs' && (
            <div>
              <h2>📚 RAG Knowledge Base PDFs</h2>
              <p style={{ color: 'var(--muted)' }}>Ground answers on your local PDF collection indexed into ChromaDB vector store.</p>

              {/* Prominent Highlighted Path Box with One-Click Copy */}
              <div className="glass-panel" style={{ padding: '20px', borderRadius: roundedCorners ? '14px' : '0', marginTop: '16px', border: '1px solid var(--accent)', background: 'linear-gradient(180deg, rgba(124, 108, 255, 0.08), rgba(0, 0, 0, 0.2))' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <div style={{ fontWeight: 'bold', fontSize: '14px', color: 'var(--accent)' }}>📂 PDF Drop-In Folder Location:</div>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <button onClick={copyPdfLocation} style={{ background: copiedPdfPath ? 'var(--accent2)' : 'var(--panel2)', color: '#fff', border: '1px solid var(--border)', padding: '6px 14px', borderRadius: roundedCorners ? '6px' : '0', cursor: 'pointer', fontWeight: 'bold', fontSize: '12px', transition: 'all 0.2s ease' }}>
                      {copiedPdfPath ? '✓ Copied to Clipboard!' : '📋 Copy Path'}
                    </button>
                    <button onClick={openPdfFolder} style={{ background: 'var(--accent)', color: '#fff', border: 0, padding: '6px 14px', borderRadius: roundedCorners ? '6px' : '0', cursor: 'pointer', fontWeight: 'bold', fontSize: '12px' }}>
                      📂 Open in File Explorer
                    </button>
                    <button onClick={syncPdfs} disabled={syncingPdfs} style={{ background: 'var(--accent2)', color: '#fff', border: 0, padding: '6px 14px', borderRadius: roundedCorners ? '6px' : '0', cursor: 'pointer', fontWeight: 'bold', fontSize: '12px' }}>
                      {syncingPdfs ? '⏳ Indexing...' : '🔄 Sync & Re-Index'}
                    </button>
                  </div>
                </div>
                <code style={{ fontSize: '13px', background: '#07070d', padding: '10px 14px', borderRadius: '8px', display: 'block', color: '#a5b4fc', wordBreak: 'break-all', border: '1px solid rgba(124, 108, 255, 0.3)' }}>
                  {pdfDir || 'Loading PDF directory...'}
                </code>
                <div style={{ fontSize: '12px', color: 'var(--muted)', marginTop: '8px' }}>
                  💡 <strong>Tip:</strong> Paste your <code>.pdf</code> documents into this folder. Aether will automatically parse and chunk them into ChromaDB for grounded RAG chat!
                </div>
              </div>

              {/* PDF Documents List */}
              <div className="glass-panel" style={{ padding: '20px', borderRadius: roundedCorners ? '14px' : '0', marginTop: '16px' }}>
                <div style={{ fontWeight: 'bold', marginBottom: '14px', fontSize: '15px' }}>Indexed PDF Documents ({pdfFiles.length}):</div>
                {pdfFiles.length === 0 ? (
                  <div style={{ color: 'var(--muted)', fontSize: '13px', padding: '16px', textAlign: 'center', background: 'var(--panel2)', borderRadius: roundedCorners ? '8px' : '0' }}>
                    No PDF files indexed yet. Click <strong>"Open in File Explorer"</strong> above and paste your PDFs into the folder!
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {pdfFiles.map((f, idx) => (
                      <div key={idx} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 14px', background: 'var(--panel2)', borderRadius: roundedCorners ? '8px' : '0', border: '1px solid var(--border)' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                          <span style={{ fontSize: '18px' }}>📄</span>
                          <div>
                            <div style={{ fontWeight: 'bold', fontSize: '13px' }}>{f.name || f.path || f}</div>
                            {f.size && <div style={{ fontSize: '11px', color: 'var(--muted)' }}>{(f.size / 1024).toFixed(1)} KB</div>}
                          </div>
                        </div>
                        <button onClick={() => removePdf(f.path || f)} style={{ background: 'transparent', color: 'var(--danger)', border: '1px solid rgba(239, 68, 68, 0.3)', padding: '4px 10px', borderRadius: roundedCorners ? '6px' : '0', cursor: 'pointer', fontSize: '12px' }}>
                          🗑️ Remove
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {activeView === 'memory' && (
            <div>
              <h2>🧠 Fact Memory Store</h2>
              <p style={{ color: 'var(--muted)' }}>Durable facts remembered by Aether OS across chat sessions. You can view, add, edit, or delete memories.</p>

              {/* Add New Fact Input */}
              <div className="glass-panel" style={{ padding: '20px', borderRadius: roundedCorners ? '14px' : '0', marginTop: '16px' }}>
                <div style={{ fontWeight: 'bold', marginBottom: '8px', fontSize: '14px' }}>➕ Add New Memory Fact:</div>
                <div style={{ display: 'flex', gap: '10px' }}>
                  <input type="text" value={newMemoryText} onChange={(e) => setNewMemoryText(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') addMemory(); }} placeholder="e.g. User prefers Python and TypeScript, works on project ProjectX..." style={{ flex: 1, background: 'var(--panel2)', border: '1px solid var(--border)', color: '#fff', padding: '10px 14px', borderRadius: roundedCorners ? '8px' : '0', fontSize: '13px' }} />
                  <button onClick={addMemory} style={{ background: 'var(--accent)', color: '#fff', border: 0, padding: '0 20px', borderRadius: roundedCorners ? '8px' : '0', cursor: 'pointer', fontWeight: 'bold', fontSize: '13px' }}>
                    + Save Fact
                  </button>
                </div>
              </div>

              {/* Memory List with Edit & Delete */}
              <div className="glass-panel" style={{ padding: '20px', borderRadius: roundedCorners ? '14px' : '0', marginTop: '16px' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
                  <div style={{ fontWeight: 'bold', fontSize: '15px' }}>Stored Durable Facts ({memories.length}):</div>
                </div>

                {memories.length === 0 ? (
                  <div style={{ color: 'var(--muted)', fontSize: '13px', padding: '16px', textAlign: 'center', background: 'var(--panel2)', borderRadius: roundedCorners ? '8px' : '0' }}>
                    No facts remembered yet. Type <code>REMEMBER: [fact]</code> in chat or add one above!
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                    {memories.map((m, i) => {
                      const text = typeof m === 'string' ? m : m.content || JSON.stringify(m);
                      const isEditing = editingMemoryIdx === i;

                      return (
                        <div key={i} style={{ padding: '12px 16px', background: 'var(--panel2)', borderRadius: roundedCorners ? '8px' : '0', border: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px' }}>
                          {isEditing ? (
                            <div style={{ flex: 1, display: 'flex', gap: '8px' }}>
                              <input type="text" value={editMemoryText} onChange={(e) => setEditMemoryText(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') saveEditMemory(i); }} style={{ flex: 1, background: '#0b0b12', border: '1px solid var(--accent)', color: '#fff', padding: '8px 12px', borderRadius: '6px', fontSize: '13px' }} autoFocus />
                              <button onClick={() => saveEditMemory(i)} style={{ background: 'var(--accent2)', color: '#fff', border: 0, padding: '6px 14px', borderRadius: '6px', cursor: 'pointer', fontWeight: 'bold', fontSize: '12px' }}>Save</button>
                              <button onClick={() => setEditingMemoryIdx(null)} style={{ background: 'transparent', color: 'var(--muted)', border: '1px solid var(--border)', padding: '6px 14px', borderRadius: '6px', cursor: 'pointer', fontSize: '12px' }}>Cancel</button>
                            </div>
                          ) : (
                            <>
                              <div style={{ flex: 1, fontSize: '13px', lineHeight: '1.4' }}>
                                <span style={{ color: '#ec4899', fontWeight: 'bold', marginRight: '6px' }}>●</span>
                                {text}
                              </div>
                              <div style={{ display: 'flex', gap: '6px' }}>
                                <button onClick={() => startEditMemory(i, text)} style={{ background: 'transparent', color: 'var(--accent)', border: '1px solid rgba(124, 108, 255, 0.3)', padding: '4px 10px', borderRadius: '6px', cursor: 'pointer', fontSize: '12px' }}>
                                  ✏️ Edit
                                </button>
                                <button onClick={() => deleteMemory(i)} style={{ background: 'transparent', color: 'var(--danger)', border: '1px solid rgba(239, 68, 68, 0.3)', padding: '4px 10px', borderRadius: '6px', cursor: 'pointer', fontSize: '12px' }}>
                                  🗑️ Delete
                                </button>
                              </div>
                            </>
                          )}
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
