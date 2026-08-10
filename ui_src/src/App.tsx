import React, { useState, useEffect } from 'react';
import { Session, ChatMode, SubagentStep, HitlApproval, Checkpoint, WatcherStatus } from './types';

interface MemoryEntry {
  target?: string;
  content: string;
}

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
  const [checkpoints, setCheckpoints] = useState<Checkpoint[]>([]);
  const [hitlEnabled, setHitlEnabled] = useState<boolean>(true);
  const [roleModels, setRoleModels] = useState<{ planner?: string; code?: string; research?: string; synthesis?: string }>({});
  
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
  
  // MCP & Settings
  const [mcpServers, setMcpServers] = useState<any[]>([]);
  const [openRouterKey, setOpenRouterKey] = useState<string>('');
  const [currentModel, setCurrentModel] = useState<string>('openrouter/free');
  const [savedSettingsMsg, setSavedSettingsMsg] = useState<string>('');

  useEffect(() => {
    loadSessions();
    loadWatcherStatus();
    loadHitlSettings();
    loadPdfs();
    loadMcp();
    loadMemories();
    loadSettings();
  }, []);

  const loadSessions = async () => {
    try {
      const res = await fetch('/api/sessions');
      const data = await res.json();
      setSessions(data);
      if (data.length > 0 && !sessionId) {
        setSessionId(data[0].id);
      }
    } catch (e) {
      console.error(e);
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

  const loadMcp = async () => {
    try {
      const res = await fetch('/api/mcp/servers');
      const data = await res.json();
      setMcpServers(data.servers || []);
    } catch (e) {
      console.error(e);
    }
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

  const saveApiKey = async () => {
    try {
      await fetch('/api/settings/save', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          openrouter_api_key: openRouterKey,
          default_model: currentModel,
        }),
      });
      setSavedSettingsMsg('✓ API Key & Model Saved Successfully!');
      setTimeout(() => setSavedSettingsMsg(''), 3000);
    } catch (e) {
      console.error(e);
    }
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
    <div style={{ display: 'flex', height: '100vh', background: 'var(--bg)' }}>
      {/* Navigation Sidebar */}
      <div style={{ width: '250px', background: 'var(--panel)', borderRight: '1px solid var(--border)', display: 'flex', flexDirection: 'column' }}>
        <div style={{ padding: '16px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div style={{ width: '32px', height: '32px', borderRadius: '8px', background: 'linear-gradient(135deg, var(--accent), var(--accent2))', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 'bold', color: '#fff' }}>⚡</div>
          <div>
            <div style={{ fontWeight: 'bold', fontSize: '15px' }}>Aether OS</div>
            <div style={{ fontSize: '11px', color: 'var(--muted)' }}>Multi-Agent + Burr Engine</div>
          </div>
        </div>

        <div style={{ flex: 1, padding: '10px', overflowY: 'auto' }}>
          {[
            { id: 'chat', label: '💬 Chat', color: 'var(--accent)' },
            { id: 'burr', label: '⚡ Burr OS Dashboard', color: 'var(--accent2)' },
            { id: 'pdfs', label: '📚 RAG Knowledge Base', color: '#3b82f6' },
            { id: 'memory', label: '🧠 Fact Memory Store', color: '#ec4899' },
            { id: 'mcp', label: '🧩 MCP Tool Servers', color: '#8b5cf6' },
            { id: 'settings', label: '⚙️ Settings & Keys', color: '#10b981' },
          ].map((item) => (
            <button key={item.id} onClick={() => setActiveView(item.id)} style={{ width: '100%', padding: '10px 14px', background: activeView === item.id ? 'var(--panel2)' : 'transparent', color: activeView === item.id ? '#fff' : 'var(--muted)', borderLeft: activeView === item.id ? `4px solid ${item.color}` : '4px solid transparent', borderTop: 0, borderRight: 0, borderBottom: 0, borderRadius: '6px', marginBottom: '4px', textAlign: 'left', cursor: 'pointer', fontWeight: activeView === item.id ? 'bold' : 'normal', transition: 'all 0.15s ease' }}>
              {item.label}
            </button>
          ))}
        </div>

        <div style={{ padding: '12px 16px', borderTop: '1px solid var(--border)', fontSize: '11px', color: 'var(--muted)' }}>
          <div>Engine: <span style={{ color: 'var(--accent2)', fontWeight: 'bold' }}>● OpenRouter / Local</span></div>
          <div style={{ marginTop: '4px' }}>Watcher: <span style={{ color: watcherStatus?.running ? 'var(--accent2)' : 'var(--danger)' }}>{watcherStatus?.running ? '● Active' : '○ Inactive'}</span></div>
        </div>
      </div>

      {/* Main View Area */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        {/* Header Bar */}
        <div style={{ padding: '14px 24px', borderBottom: '1px solid var(--border)', background: 'var(--panel)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ fontWeight: 'bold', fontSize: '16px', letterSpacing: '0.5px' }}>{activeView.toUpperCase()}</div>
          {activeView === 'chat' && (
            <div style={{ display: 'flex', gap: '6px', background: 'var(--panel2)', borderRadius: '8px', padding: '4px', border: '1px solid var(--border)' }}>
              <button onClick={() => setMode('normal')} style={{ background: mode === 'normal' ? 'var(--accent)' : 'transparent', border: 0, color: '#fff', padding: '6px 14px', borderRadius: '6px', cursor: 'pointer', fontWeight: mode === 'normal' ? 'bold' : 'normal' }}>Normal</button>
              <button onClick={() => setMode('rag')} style={{ background: mode === 'rag' ? 'var(--accent)' : 'transparent', border: 0, color: '#fff', padding: '6px 14px', borderRadius: '6px', cursor: 'pointer', fontWeight: mode === 'rag' ? 'bold' : 'normal' }}>RAG</button>
              <button onClick={() => setMode('multiagent')} style={{ background: mode === 'multiagent' ? 'var(--accent2)' : 'transparent', border: 0, color: '#fff', padding: '6px 14px', borderRadius: '6px', cursor: 'pointer', fontWeight: mode === 'multiagent' ? 'bold' : 'normal' }}>Swarm 🤖</button>
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
                    <div style={{ fontSize: '13px', marginTop: '4px' }}>Ask questions, orchestrate multi-agent swarms, or query your local PDF knowledge base.</div>
                  </div>
                ) : null}

                {messages.map((m, idx) => (
                  <div key={idx} className="animate-slide-up" style={{ marginBottom: '16px', padding: '14px 18px', borderRadius: '12px', background: m.role === 'user' ? 'var(--accent)' : 'var(--panel)', border: '1px solid var(--border)', maxWidth: '85%', marginLeft: m.role === 'user' ? 'auto' : '0', boxShadow: '0 4px 12px rgba(0,0,0,0.15)' }}>
                    <div style={{ fontSize: '11px', fontWeight: 'bold', marginBottom: '4px', opacity: 0.7 }}>{m.role === 'user' ? 'YOU' : 'AETHER OS'}</div>
                    <div style={{ whiteSpace: 'pre-wrap', lineHeight: '1.5' }}>{m.content}</div>
                  </div>
                ))}

                {steps.map((st, idx) => (
                  <div key={idx} className="subagent-card animate-slide-up">
                    <div style={{ fontWeight: 'bold', fontSize: '13px', color: 'var(--accent2)' }}>🤖 {st.agent} ({st.role})</div>
                    <div style={{ fontSize: '12px', color: 'var(--muted)', marginTop: '2px' }}>{st.task}</div>
                    {st.summary && <div style={{ fontSize: '11px', marginTop: '6px', color: 'var(--text)' }}>Result: {st.summary}</div>}
                  </div>
                ))}

                {pendingHitl && (
                  <div className="glass-panel animate-slide-up glow-active" style={{ padding: '20px', borderRadius: '14px', borderColor: 'var(--accent)', marginTop: '12px' }}>
                    <div style={{ fontWeight: 'bold', color: 'var(--accent)', fontSize: '15px' }}>⚠️ Human-in-the-Loop Approval Request</div>
                    <div style={{ fontSize: '13px', margin: '10px 0', color: 'var(--text)' }}>Tool: <code style={{ background: 'var(--panel2)', padding: '2px 6px', borderRadius: '4px' }}>{pendingHitl.tool}</code></div>
                    <div style={{ display: 'flex', gap: '10px', marginTop: '12px' }}>
                      <button onClick={() => handleHitlApprove(true)} style={{ background: 'var(--accent2)', color: '#fff', border: 0, padding: '8px 20px', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold' }}>Approve Action</button>
                      <button onClick={() => handleHitlApprove(false)} style={{ background: 'var(--danger)', color: '#fff', border: 0, padding: '8px 20px', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold' }}>Reject</button>
                    </div>
                  </div>
                )}
              </div>

              <div style={{ display: 'flex', gap: '12px' }}>
                <textarea value={inputPrompt} onChange={(e) => setInputPrompt(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); } }} placeholder="Message Aether Desktop OS or launch subagent swarm..." style={{ flex: 1, background: 'var(--panel2)', border: '1px solid var(--border)', color: '#fff', borderRadius: '10px', padding: '14px', resize: 'none', height: '56px', fontSize: '14px', fontFamily: 'inherit' }} />
                <button onClick={handleSend} style={{ background: 'linear-gradient(135deg, var(--accent), #6366f1)', color: '#fff', border: 0, padding: '0 28px', borderRadius: '10px', cursor: 'pointer', fontWeight: 'bold', fontSize: '14px', boxShadow: '0 4px 16px rgba(124, 108, 255, 0.4)' }}>Send</button>
              </div>
            </div>
          )}

          {activeView === 'burr' && (
            <div>
              <h2 style={{ margin: '0 0 4px 0' }}>⚡ Apache Burr OS Dashboard</h2>
              <p style={{ color: 'var(--muted)', marginTop: 0 }}>State-Driven Orchestration & HITL Approvals Engine</p>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', marginTop: '20px' }}>
                <div className="glass-panel" style={{ padding: '20px', borderRadius: '14px' }}>
                  <h3 style={{ margin: '0 0 12px 0', fontSize: '16px' }}>🛑 Human-in-the-Loop (HITL) Controls</h3>
                  <p style={{ fontSize: '13px', color: 'var(--muted)' }}>Pause execution when tools execute system commands or modify files.</p>
                  <button onClick={toggleHitl} style={{ marginTop: '8px', background: hitlEnabled ? 'var(--accent2)' : 'var(--danger)', color: '#fff', border: 0, padding: '8px 18px', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold' }}>
                    {hitlEnabled ? '✓ HITL Approvals Active' : '✕ HITL Approvals Disabled'}
                  </button>
                </div>

                <div className="glass-panel" style={{ padding: '20px', borderRadius: '14px' }}>
                  <h3 style={{ margin: '0 0 12px 0', fontSize: '16px' }}>📁 Background File Watcher</h3>
                  <div style={{ fontSize: '13px', color: 'var(--muted)' }}>Monitoring Folder:</div>
                  <code style={{ fontSize: '12px', background: 'var(--panel2)', padding: '4px 8px', borderRadius: '6px', display: 'block', margin: '6px 0 12px 0' }}>{watcherStatus?.watch_dir || '%APPDATA%/aether/watch_folder'}</code>
                  <div style={{ fontSize: '13px' }}>Status: <span style={{ color: watcherStatus?.running ? 'var(--accent2)' : 'var(--danger)', fontWeight: 'bold' }}>{watcherStatus?.running ? 'Active (Auto-Ingesting)' : 'Inactive'}</span></div>
                </div>
              </div>

              <div className="glass-panel" style={{ padding: '20px', borderRadius: '14px', marginTop: '16px' }}>
                <h3 style={{ margin: '0 0 12px 0', fontSize: '16px' }}>⚙️ Multi-LLM Role Assignment</h3>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  {['planner', 'code', 'research', 'synthesis'].map((r) => (
                    <div key={r}>
                      <label style={{ fontSize: '12px', color: 'var(--muted)', textTransform: 'capitalize' }}>{r} Model:</label>
                      <input type="text" value={(roleModels as any)[r] || ''} onChange={(e) => handleRoleModelChange(r, e.target.value)} placeholder="e.g. anthropic/claude-3.5-sonnet" style={{ width: '100%', background: 'var(--panel2)', border: '1px solid var(--border)', color: '#fff', padding: '8px 12px', borderRadius: '6px', marginTop: '4px' }} />
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
              <div className="glass-panel" style={{ padding: '20px', borderRadius: '14px', marginTop: '16px', border: '1px solid var(--accent)', background: 'linear-gradient(180deg, rgba(124, 108, 255, 0.08), rgba(0, 0, 0, 0.2))' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <div style={{ fontWeight: 'bold', fontSize: '14px', color: 'var(--accent)' }}>📂 PDF Drop-In Folder Location:</div>
                  <div style={{ display: 'flex', gap: '8px' }}>
                    <button onClick={copyPdfLocation} style={{ background: copiedPdfPath ? 'var(--accent2)' : 'var(--panel2)', color: '#fff', border: '1px solid var(--border)', padding: '6px 14px', borderRadius: '6px', cursor: 'pointer', fontWeight: 'bold', fontSize: '12px', transition: 'all 0.2s ease' }}>
                      {copiedPdfPath ? '✓ Copied to Clipboard!' : '📋 Copy Path'}
                    </button>
                    <button onClick={openPdfFolder} style={{ background: 'var(--accent)', color: '#fff', border: 0, padding: '6px 14px', borderRadius: '6px', cursor: 'pointer', fontWeight: 'bold', fontSize: '12px' }}>
                      📂 Open in File Explorer
                    </button>
                    <button onClick={syncPdfs} disabled={syncingPdfs} style={{ background: 'var(--accent2)', color: '#fff', border: 0, padding: '6px 14px', borderRadius: '6px', cursor: 'pointer', fontWeight: 'bold', fontSize: '12px' }}>
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
              <div className="glass-panel" style={{ padding: '20px', borderRadius: '14px', marginTop: '16px' }}>
                <div style={{ fontWeight: 'bold', marginBottom: '14px', fontSize: '15px' }}>Indexed PDF Documents ({pdfFiles.length}):</div>
                {pdfFiles.length === 0 ? (
                  <div style={{ color: 'var(--muted)', fontSize: '13px', padding: '16px', textAlign: 'center', background: 'var(--panel2)', borderRadius: '8px' }}>
                    No PDF files indexed yet. Click <strong>"Open in File Explorer"</strong> above and paste your PDFs into the folder!
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {pdfFiles.map((f, idx) => (
                      <div key={idx} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '10px 14px', background: 'var(--panel2)', borderRadius: '8px', border: '1px solid var(--border)' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                          <span style={{ fontSize: '18px' }}>📄</span>
                          <div>
                            <div style={{ fontWeight: 'bold', fontSize: '13px' }}>{f.name || f.path || f}</div>
                            {f.size && <div style={{ fontSize: '11px', color: 'var(--muted)' }}>{(f.size / 1024).toFixed(1)} KB</div>}
                          </div>
                        </div>
                        <button onClick={() => removePdf(f.path || f)} style={{ background: 'transparent', color: 'var(--danger)', border: '1px solid rgba(239, 68, 68, 0.3)', padding: '4px 10px', borderRadius: '6px', cursor: 'pointer', fontSize: '12px' }}>
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
              <div className="glass-panel" style={{ padding: '20px', borderRadius: '14px', marginTop: '16px' }}>
                <div style={{ fontWeight: 'bold', marginBottom: '8px', fontSize: '14px' }}>➕ Add New Memory Fact:</div>
                <div style={{ display: 'flex', gap: '10px' }}>
                  <input type="text" value={newMemoryText} onChange={(e) => setNewMemoryText(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter') addMemory(); }} placeholder="e.g. User prefers Python and TypeScript, works on project ProjectX..." style={{ flex: 1, background: 'var(--panel2)', border: '1px solid var(--border)', color: '#fff', padding: '10px 14px', borderRadius: '8px', fontSize: '13px' }} />
                  <button onClick={addMemory} style={{ background: 'var(--accent)', color: '#fff', border: 0, padding: '0 20px', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold', fontSize: '13px' }}>
                    + Save Fact
                  </button>
                </div>
              </div>

              {/* Memory List with Edit & Delete */}
              <div className="glass-panel" style={{ padding: '20px', borderRadius: '14px', marginTop: '16px' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px' }}>
                  <div style={{ fontWeight: 'bold', fontSize: '15px' }}>Stored Durable Facts ({memories.length}):</div>
                </div>

                {memories.length === 0 ? (
                  <div style={{ color: 'var(--muted)', fontSize: '13px', padding: '16px', textAlign: 'center', background: 'var(--panel2)', borderRadius: '8px' }}>
                    No facts remembered yet. Type <code>REMEMBER: [fact]</code> in chat or add one above!
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                    {memories.map((m, i) => {
                      const text = typeof m === 'string' ? m : m.content || JSON.stringify(m);
                      const isEditing = editingMemoryIdx === i;

                      return (
                        <div key={i} style={{ padding: '12px 16px', background: 'var(--panel2)', borderRadius: '8px', border: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '12px' }}>
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

          {activeView === 'mcp' && (
            <div>
              <h2>🧩 Model Context Protocol (MCP) Servers</h2>
              <p style={{ color: 'var(--muted)' }}>Extend Aether OS capabilities with external MCP tool servers.</p>
              <div className="glass-panel" style={{ padding: '20px', borderRadius: '14px', marginTop: '16px' }}>
                {mcpServers.length === 0 ? <div style={{ color: 'var(--muted)' }}>No external MCP servers configured. Add servers in config.yaml.</div> : JSON.stringify(mcpServers)}
              </div>
            </div>
          )}

          {activeView === 'settings' && (
            <div>
              <h2>⚙️ Provider Settings & API Keys</h2>
              <p style={{ color: 'var(--muted)' }}>Configure your OpenRouter or frontier model API keys.</p>
              
              <div className="glass-panel" style={{ padding: '20px', borderRadius: '14px', marginTop: '16px' }}>
                <div style={{ marginBottom: '16px' }}>
                  <label style={{ fontSize: '13px', fontWeight: 'bold', display: 'block', marginBottom: '6px' }}>Active Model:</label>
                  <input type="text" value={currentModel} onChange={(e) => setCurrentModel(e.target.value)} placeholder="e.g. openrouter/free or anthropic/claude-3.5-sonnet" style={{ width: '100%', background: 'var(--panel2)', border: '1px solid var(--border)', color: '#fff', padding: '10px 14px', borderRadius: '8px', fontSize: '13px' }} />
                  <div style={{ fontSize: '11px', color: 'var(--muted)', marginTop: '4px' }}>Defaults to OpenRouter free models if no custom key is provided.</div>
                </div>

                <div style={{ marginBottom: '16px' }}>
                  <label style={{ fontSize: '13px', fontWeight: 'bold', display: 'block', marginBottom: '6px' }}>OpenRouter API Key:</label>
                  <input type="password" value={openRouterKey} onChange={(e) => setOpenRouterKey(e.target.value)} placeholder="sk-or-v1-..." style={{ width: '100%', background: 'var(--panel2)', border: '1px solid var(--border)', color: '#fff', padding: '10px 14px', borderRadius: '8px', fontSize: '13px' }} />
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <button onClick={saveApiKey} style={{ background: 'var(--accent)', color: '#fff', border: 0, padding: '10px 24px', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold', fontSize: '13px' }}>
                    💾 Save Settings
                  </button>
                  {savedSettingsMsg && <span style={{ color: 'var(--accent2)', fontWeight: 'bold', fontSize: '13px' }}>{savedSettingsMsg}</span>}
                </div>
              </div>

              {/* Architecture & Privacy Info */}
              <div className="glass-panel" style={{ padding: '20px', borderRadius: '14px', marginTop: '16px' }}>
                <h3 style={{ margin: '0 0 8px 0', fontSize: '15px' }}>🔒 Privacy & Self-Hosted Security</h3>
                <p style={{ fontSize: '13px', color: 'var(--muted)', lineHeight: '1.5', margin: 0 }}>
                  Aether Desktop stores all keys, memories, chat sessions, and vector databases strictly on your local machine in <code>%APPDATA%/aether/</code>. No data is transmitted to external telemetry servers.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
