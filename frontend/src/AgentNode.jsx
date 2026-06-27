import React from 'react';
import { Handle, Position } from '@xyflow/react';

export default function AgentNode({ id, data }) {
  const updateField = (key, value) => {
    if (data.onNodeDataChange) {
      data.onNodeDataChange(id, { ...data, [key]: value });
    }
  };

  return (
    <div style={{ background: '#ffffff', border: '2px solid #3b82f6', borderRadius: '10px', padding: '16px', width: '280px', boxShadow: '0 4px 10px rgba(0,0,0,0.15)', fontFamily: 'sans-serif' }}>
      <Handle type="target" position={Position.Left} style={{ background: '#3b82f6', width: '8px', height: '8px' }} />

      <div style={{ fontWeight: 'bold', fontSize: '14px', borderBottom: '1px solid #e2e8f0', paddingBottom: '6px', marginBottom: '10px', color: '#1e3a8a', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span>🤖 Agent Node</span>
        <span style={{ fontSize: '10px', background: '#dbeafe', color: '#1e40af', padding: '2px 6px', borderRadius: '4px' }}>{id}</span>
      </div>

      <div style={{ marginBottom: '8px' }}>
        <label style={{ display: 'block', fontSize: '10px', color: '#64748b', marginBottom: '2px', fontWeight: '600' }}>AGENT NAME</label>
        <input type="text" value={data.name || ''} onChange={(e) => updateField('name', e.target.value)} placeholder="Name your agent..." style={{ width: '100%', padding: '6px', border: '1px solid #cbd5e1', borderRadius: '4px', fontSize: '12px', boxSizing: 'border-box' }} />
      </div>

      <div style={{ marginBottom: '8px' }}>
        <label style={{ display: 'block', fontSize: '10px', color: '#64748b', marginBottom: '2px', fontWeight: '600' }}>MODEL WORKER</label>
        <select value={data.model || 'gemma4:31b-cloud'} onChange={(e) => updateField('model', e.target.value)} style={{ width: '100%', padding: '6px', border: '1px solid #cbd5e1', borderRadius: '4px', background: '#fff', fontSize: '12px' }}>
          <option value="gemma4:31b-cloud">gemma4:31b-cloud</option>
          <option value="llama3">llama3</option>
          <option value="mistral">mistral</option>
        </select>
      </div>

      <div style={{ marginBottom: '10px' }}>
        <label style={{ display: 'block', fontSize: '10px', color: '#64748b', marginBottom: '2px', fontWeight: '600' }}>SYSTEM PROMPT</label>
        <textarea value={data.system_prompt || ''} onChange={(e) => updateField('system_prompt', e.target.value)} placeholder="Instructions..." rows={3} style={{ width: '100%', padding: '6px', border: '1px solid #cbd5e1', borderRadius: '4px', resize: 'vertical', fontSize: '11px', boxSizing: 'border-box' }} />
      </div>

      <div style={{ display: 'flex', alignItems: 'center', background: '#f8fafc', padding: '6px', borderRadius: '4px' }}>
        <input type="checkbox" id={`output-${id}`} checked={data.returns_output !== false} onChange={(e) => updateField('returns_output', e.target.checked)} style={{ marginRight: '6px', cursor: 'pointer' }} />
        <label htmlFor={`output-${id}`} style={{ fontSize: '11px', color: '#334155', cursor: 'pointer', fontWeight: '500' }}>Returns Output Context</label>
      </div>

      <Handle type="source" position={Position.Right} style={{ background: '#10b981', width: '8px', height: '8px' }} />
    </div>
  );
}