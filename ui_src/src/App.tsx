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

  useEffect(() => {
    loadSessions();
    loadWatcherStatus();
    loadHitlSettings();
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
      {/* Sidebar */}
      <div style={{ width: '240px', background: 'var(--panel)', borderRight: '1px solid var(--border)', display: 'flex', flexDirection: 'column' }}>
        <div style={{ padding: '16px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: '10px' }}>
          <img src="/ui/logo.png" alt="Aether" style={{ width: '32px', height: '32px', borderRadius: '8px' }} />
          <div>
            <div style={{ fontWeight: 'bold', fontSize: '15px' }}>Aether OS</div>
            <div style={{ fontSize: '11px', color: 'var(--muted)' }}>Agent + RAG + Burr</div>
          </div>
        </div>

        <div style={{ flex: 1, padding: '10px', overflowY: 'auto' }}>
          <button onClick={() => setActiveView('chat')} style={{ width: '100%', padding: '10px', background: activeView === 'chat' ? 'var(--accent)' : 'transparent', color: '#fff', border: 0, borderRadius: '8px', marginBottom: '4px', textAlign: 'left', cursor: 'pointer' }}>
            💬 Chat
          </button>
          <button onClick={() => setActiveView('burr')} style={{ width: '100%', padding: '10px', background: activeView === 'burr' ? 'var(--accent)' : 'transparent', color: '#fff', border: 0, borderRadius: '8px', marginBottom: '4px', textAlign: 'left', cursor: 'pointer' }}>
            ⚡ Burr OS
          </button>
          <button onClick={() => setActiveView('pdfs')} style={{ width: '100%', padding: '10px', background: activeView === 'pdfs' ? 'var(--accent)' : 'transparent', color: '#fff', border: 0, borderRadius: '8px', marginBottom: '4px', textAlign: 'left', cursor: 'pointer' }}>
            📚 RAG PDFs
          </button>
        </div>
      </div>

      {/* Main View */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        {/* Topbar */}
        <div style={{ padding: '12px 20px', borderBottom: '1px solid var(--border)', background: 'var(--panel)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ fontWeight: 'bold' }}>{activeView.toUpperCase()}</div>
          {activeView === 'chat' && (
            <div style={{ display: 'flex', gap: '6px', background: 'var(--panel2)', borderRadius: '8px', padding: '4px' }}>
              <button onClick={() => setMode('normal')} style={{ background: mode === 'normal' ? 'var(--accent)' : 'transparent', border: 0, color: '#fff', padding: '4px 12px', borderRadius: '6px', cursor: 'pointer' }}>Normal</button>
              <button onClick={() => setMode('rag')} style={{ background: mode === 'rag' ? 'var(--accent)' : 'transparent', border: 0, color: '#fff', padding: '4px 12px', borderRadius: '6px', cursor: 'pointer' }}>RAG</button>
              <button onClick={() => setMode('multiagent')} style={{ background: mode === 'multiagent' ? 'var(--accent)' : 'transparent', border: 0, color: '#fff', padding: '4px 12px', borderRadius: '6px', cursor: 'pointer' }}>Swarm 🤖</button>
            </div>
          )}
        </div>

        {/* View Content */}
        <div style={{ flex: 1, padding: '20px', overflowY: 'auto' }}>
          {activeView === 'chat' && (
            <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
              <div style={{ flex: 1, overflowY: 'auto', marginBottom: '16px' }}>
                {messages.map((m, idx) => (
                  <div key={idx} className={`animate-slide-up`} style={{ marginBottom: '12px', padding: '12px 16px', borderRadius: '12px', background: m.role === 'user' ? 'var(--accent)' : 'var(--panel)', maxWidth: '80%', marginLeft: m.role === 'user' ? 'auto' : '0' }}>
                    {m.content}
                  </div>
                ))}

                {steps.map((st, idx) => (
                  <div key={idx} className="subagent-card animate-slide-up">
                    <div style={{ fontWeight: 'bold', fontSize: '13px', color: 'var(--accent2)' }}>🤖 {st.agent} ({st.role})</div>
                    <div style={{ fontSize: '12px', color: 'var(--muted)' }}>{st.task}</div>
                  </div>
                ))}

                {pendingHitl && (
                  <div className="glass-panel animate-slide-up" style={{ padding: '16px', borderRadius: '12px', borderColor: 'var(--accent)' }}>
                    <div style={{ fontWeight: 'bold', color: 'var(--accent)' }}>⚠️ Human Approval Required</div>
                    <div style={{ fontSize: '13px', margin: '8px 0' }}>Tool: <b>{pendingHitl.tool}</b></div>
                    <div style={{ display: 'flex', gap: '8px' }}>
                      <button onClick={() => handleHitlApprove(true)} style={{ background: 'var(--accent2)', color: '#fff', border: 0, padding: '6px 16px', borderRadius: '6px', cursor: 'pointer' }}>Approve</button>
                      <button onClick={() => handleHitlApprove(false)} style={{ background: 'var(--danger)', color: '#fff', border: 0, padding: '6px 16px', borderRadius: '6px', cursor: 'pointer' }}>Reject</button>
                    </div>
                  </div>
                )}
              </div>

              <div style={{ display: 'flex', gap: '10px' }}>
                <textarea value={inputPrompt} onChange={(e) => setInputPrompt(e.target.value)} onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); } }} placeholder="Ask Aether OS..." style={{ flex: 1, background: 'var(--panel2)', border: '1px solid var(--border)', color: '#fff', borderRadius: '8px', padding: '10px', resize: 'none' }} />
                <button onClick={handleSend} style={{ background: 'var(--accent)', color: '#fff', border: 0, padding: '0 24px', borderRadius: '8px', cursor: 'pointer', fontWeight: 'bold' }}>Send</button>
              </div>
            </div>
          )}

          {activeView === 'burr' && (
            <div>
              <h2>⚡ Apache Burr OS Dashboard</h2>
              <p style={{ color: 'var(--muted)' }}>Explicit State ➔ Action ➔ State Orchestrator</p>

              <div className="glass-panel" style={{ padding: '16px', borderRadius: '12px', marginBottom: '16px' }}>
                <div style={{ fontWeight: 'bold', fontSize: '15px' }}>Background Watcher</div>
                <div style={{ fontSize: '12px', color: 'var(--muted)' }}>Monitoring: {watcherStatus?.watch_dir}</div>
                <div style={{ fontSize: '12px', marginTop: '6px' }}>Status: <span style={{ color: 'var(--accent2)' }}>{watcherStatus?.running ? 'Active' : 'Inactive'}</span></div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
