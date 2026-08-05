import React, { useState, useEffect } from 'react';
import { Session, ChatMode, SubagentStep, HitlApproval, Checkpoint, WatcherStatus } from './types';

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
  const [pdfFiles, setPdfFiles] = useState<string[]>([]);
  const [mcpServers, setMcpServers] = useState<any[]>([]);
  const [memories, setMemories] = useState<string[]>([]);
  const [openRouterKey, setOpenRouterKey] = useState<string>('');

  useEffect(() => {
    loadSessions();
    loadWatcherStatus();
    loadHitlSettings();
    loadPdfs();
    loadMcp();
    loadMemories();
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
      const res = await fetch('/api/rag/pdfs');
      const data = await res.json();
      setPdfFiles(data.files || []);
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
      setMemories(data.memories || []);
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
      body: JSON.stringify({ hitl_enabled: nextVal }),
    });
  };

  const handleRoleModelChange = async (role: string, model: string) => {
    const nextRoles = { ...roleModels, [role]: model };
    setRoleModels(nextRoles);
    await fetch('/api/burr/roles', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ roles: nextRoles }),
    });
  };

  const handleSend = async () => {
    if (!inputPrompt.trim()) return;
    const userMsg = inputPrompt.trim();
    setInputPrompt('');
    setMessages((prev) => [...prev, { role: 'user', content: userMsg }]);

    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode, message: userMsg, session_id: sessionId }),
      });
      const reader = res.body?.getReader();
      const dec = new TextDecoder();
      let buf = '';

      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buf += dec.decode(value, { stream: true });
          const parts = buf.split('\n\n');
          parts.forEach((part) => {
            if (part.startsWith('data: ')) {
              try {
                const j = JSON.parse(part.slice(6));
                if (j.step === 'subagent_start') {
                  setSteps((prev) => [
                    ...prev,
                    { id: j.agent, agent: j.agent, role: j.role, task: j.task, status: 'running' },
                  ]);
                } else if (j.step === 'subagent_done') {
                  setSteps((prev) =>
                    prev.map((s) => (s.agent === j.agent ? { ...s, status: 'completed', summary: j.summary } : s))
                  );
                } else if (j.step === 'awaiting_approval') {
                  setPendingHitl(j.data);
                } else if (j.token) {
                  setMessages((prev) => [...prev, { role: 'assistant', content: j.token }]);
                }
              } catch (e) {}
            }
          });
          buf = '';
        }
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
            { id: 'mcp', label: '🧩 MCP Tool Servers', color: '#8b5cf6' },
            { id: 'memory', label: '🧠 Fact Memory', color: '#ec4899' },
            { id: 'settings', label: '⚙️ Settings & Keys', color: '#6b7280' },
          ].map((item) => (
            <button key={item.id} onClick={() => setActiveView(item.id)} style={{ width: '100%', padding: '10px 14px', background: activeView === item.id ? 'var(--panel2)' : 'transparent', color: activeView === item.id ? '#fff' : 'var(--muted)', borderLeft: activeView === item.id ? `4px solid ${item.color}` : '4px solid transparent', borderTop: 0, borderRight: 0, borderBottom: 0, borderRadius: '6px', marginBottom: '4px', textAlign: 'left', cursor: 'pointer', fontWeight: activeView === item.id ? 'bold' : 'normal', transition: 'all 0.15s ease' }}>
              {item.label}
            </button>
          ))}
        </div>

        <div style={{ padding: '12px 16px', borderTop: '1px solid var(--border)', fontSize: '11px', color: 'var(--muted)' }}>
          <div>Watcher: <span style={{ color: watcherStatus?.running ? 'var(--accent2)' : 'var(--danger)' }}>{watcherStatus?.running ? '● Active' : '○ Inactive'}</span></div>
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
                  <div style={{ textAlign: 'center', marginTop: '80px', color: 'var(--muted)' }}>
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
              <p style={{ color: 'var(--muted)' }}>Ground answers on your local PDF collection indexed into ChromaDB.</p>
              <div className="glass-panel" style={{ padding: '20px', borderRadius: '14px', marginTop: '16px' }}>
                <div style={{ fontWeight: 'bold', marginBottom: '12px' }}>Loaded PDF Documents ({pdfFiles.length}):</div>
                {pdfFiles.length === 0 ? (
                  <div style={{ color: 'var(--muted)', fontSize: '13px' }}>No PDFs added yet. Drop files into %APPDATA%/aether/watch_folder to auto-ingest!</div>
                ) : (
                  <ul style={{ paddingLeft: '20px' }}>
                    {pdfFiles.map((f, idx) => <li key={idx} style={{ marginBottom: '6px' }}>{f}</li>)}
                  </ul>
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

          {activeView === 'memory' && (
            <div>
              <h2>🧠 Fact Memory Store</h2>
              <p style={{ color: 'var(--muted)' }}>Durable facts remembered by Aether OS across chat sessions.</p>
              <div className="glass-panel" style={{ padding: '20px', borderRadius: '14px', marginTop: '16px' }}>
                {memories.length === 0 ? <div style={{ color: 'var(--muted)' }}>No facts remembered yet. Type "REMEMBER: [fact]" in chat to save a memory!</div> : memories.map((m, i) => <div key={i} style={{ padding: '8px', borderBottom: '1px solid var(--border)' }}>{m}</div>)}
              </div>
            </div>
          )}

          {activeView === 'settings' && (
            <div>
              <h2>⚙️ Provider Settings & API Keys</h2>
              <p style={{ color: 'var(--muted)' }}>Configure your OpenRouter or local Ollama provider keys.</p>
              <div className="glass-panel" style={{ padding: '20px', borderRadius: '14px', marginTop: '16px' }}>
                <label style={{ fontSize: '13px' }}>OpenRouter API Key:</label>
                <input type="password" value={openRouterKey} onChange={(e) => setOpenRouterKey(e.target.value)} placeholder="sk-or-v1-..." style={{ width: '100%', background: 'var(--panel2)', border: '1px solid var(--border)', color: '#fff', padding: '10px 14px', borderRadius: '8px', marginTop: '6px' }} />
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
