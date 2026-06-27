import React, { useState, useCallback, useMemo, useEffect } from 'react';
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  addEdge,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import AgentNode from './AgentNode';

export default function AgentCanvas() {
  const nodeTypes = useMemo(() => ({ agentNode: AgentNode }), []);

  // State tracking for all pipelines
  const [pipelines, setPipelines] = useState([
    { id: 'pipe_1', name: 'Email Lead Processing', initialInput: "Messy input content here...", nodes: [], edges: [] }
  ]);
  const [activePipelineId, setActivePipelineId] = useState('pipe_1');

  // Active workspace state maps
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [initialInputText, setInitialInputText] = useState("");
  
  // Execution response logs
  const [executionResult, setExecutionResult] = useState(null);
  const [isRunning, setIsRunning] = useState(false);

  // Sync current active data streams when swapping between pipelines
  useEffect(() => {
    const activePipe = pipelines.find(p => p.id === activePipelineId);
    if (activePipe) {
      setNodes(activePipe.nodes);
      setEdges(activePipe.edges);
      setInitialInputText(activePipe.initialInput);
      setExecutionResult(null); // Clear last pipeline history log
    }
  }, [activePipelineId]);

  // Continuously persist the current workspace grid mutations back to the active configuration slice
  const saveCurrentProgressToMemory = useCallback(() => {
    setPipelines(prev => prev.map(p => p.id === activePipelineId ? {
      ...p,
      nodes: nodes,
      edges: edges,
      initialInput: initialInputText
    } : p));
  }, [nodes, edges, initialInputText, activePipelineId]);

  // Capture sub-card field adjustments
  const handleNodeDataChange = useCallback((nodeId, updatedData) => {
    setNodes((nds) => {
      const nextNodes = nds.map((node) => (node.id === nodeId ? { ...node, data: updatedData } : node));
      // Trigger background synchronization loop pass
      setTimeout(saveCurrentProgressToMemory, 0);
      return nextNodes;
    });
  }, [setNodes, saveCurrentProgressToMemory]);

  // Hook new pipeline changes down to the memory structure
  useEffect(() => {
    if (nodes.length > 0 || edges.length > 0) {
      saveCurrentProgressToMemory();
    }
  }, [nodes, edges, initialInputText]);

  // Creates a completely blank separate pipeline track
  const createNewPipelineTrack = () => {
    const uniqueId = `pipe_${Date.now()}`;
    const freshPipe = {
      id: uniqueId,
      name: `Pipeline Workflow ${pipelines.length + 1}`,
      initialInput: "Raw initial context data payload text stream goes here...",
      nodes: [],
      edges: []
    };
    setPipelines([...pipelines, freshPipe]);
    setActivePipelineId(uniqueId);
  };

  // Spawns an agent card config panel onto the active grid viewport field
  const addAgentNodeToCanvas = () => {
    const uniqueId = `node_${Date.now()}`;
    const freshNode = {
      id: uniqueId,
      type: 'agentNode',
      position: { x: 150 + nodes.length * 30, y: 150 + nodes.length * 30 },
      data: {
        name: `Specialist Agent ${nodes.length + 1}`,
        model: 'gemma4:31b-cloud',
        system_prompt: 'You are an autonomous executor...',
        returns_output: true,
        onNodeDataChange: handleNodeDataChange
      },
    };
    setNodes((nds) => nds.concat(freshNode));
  };

  const onConnect = useCallback(
    (params) => setEdges((eds) => addEdge(params, eds)),
    [setEdges]
  );

  // 🚀 THE LIVE NETWORK BRIDGE: Generates blueprint and fires context out to FastAPI Python API
  const firePipelineExecutionTask = async () => {
    setIsRunning(true);
    setExecutionResult(null);

    const activePipe = pipelines.find(p => p.id === activePipelineId);
    
    const formattedNodes = nodes.map(node => ({
      id: node.id,
      name: node.data.name || "Unnamed Agent",
      model: node.data.model || "gemma4:31b-cloud",
      system_prompt: node.data.system_prompt || "",
      returns_output: node.data.returns_output !== false
    }));

    const formattedEdges = edges.map(edge => ({
      source: edge.source,
      target: edge.target
    }));

    const completeRequestPayload = {
      graph_blueprint: {
        pipeline_name: activePipe?.name || "Visually Orchestrated AI Workforce",
        nodes: formattedNodes,
        edges: formattedEdges
      },
      initial_input: initialInputText
    };

    try {
      const response = await fetch('http://127.0.0.1:8000/api/pipeline/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(completeRequestPayload),
      });

      if (!response.ok) {
        throw new Error(`Execution error: Backend status code ${response.status}`);
      }

      const data = await response.json();
      setExecutionResult(data);
    } catch (err) {
      console.error("❌ Network Endpoint execution failure intercepted:", err);
      alert(`Pipeline crash error: ${err.message}. Ensure your python app.py server is up and listening on port 8000.`);
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div style={{ width: '100vw', height: '100vh', display: 'flex', flexDirection: 'column', background: '#f1f5f9', fontFamily: 'sans-serif' }}>
      
      {/* Upper Control Strip Command Banner Layout */}
      <div style={{ padding: '14px 24px', background: '#0f172a', color: '#fff', display: 'flex', justifyContent: 'space-between', alignItems: 'center', boxShadow: '0 2px 8px rgba(0,0,0,0.2)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <h2 style={{ margin: 0, fontSize: '1.2rem', fontWeight: '600' }}>⚡ Visual Multi-Agent Hub Studio</h2>
          <select 
            value={activePipelineId} 
            onChange={(e) => setActivePipelineId(e.target.value)}
            style={{ padding: '6px 12px', borderRadius: '4px', border: '1px solid #475569', background: '#1e293b', color: '#fff', fontWeight: '600', fontSize: '13px' }}
          >
            {pipelines.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
          <button onClick={createNewPipelineTrack} style={{ background: '#475569', color: '#fff', border: 'none', padding: '6px 12px', borderRadius: '4px', cursor: 'pointer', fontSize: '12px', fontWeight: 'bold' }}>
            📁 Create New Pipeline Task
          </button>
        </div>
        <div style={{ display: 'flex', gap: '12px' }}>
          <button onClick={addAgentNodeToCanvas} style={{ background: '#10b981', color: '#fff', border: 'none', padding: '10px 18px', borderRadius: '6px', cursor: 'pointer', fontWeight: '600', fontSize: '13px' }}>
            ➕ Add Agent Node
          </button>
          <button onClick={firePipelineExecutionTask} disabled={isRunning} style={{ background: isRunning ? '#64748b' : '#3b82f6', color: '#fff', border: 'none', padding: '10px 22px', borderRadius: '6px', cursor: isRunning ? 'not-allowed' : 'pointer', fontWeight: '700', fontSize: '13px' }}>
            {isRunning ? '⏳ Running Agents...' : '🚀 Execute Live Graph Pipeline'}
          </button>
        </div>
      </div>

      {/* Main Container Multi-Grid Field Split Panels */}
      <div style={{ display: 'flex', flexGrow: 1, overflow: 'hidden' }}>
        
        {/* Left Section Panel: Inbound Prompt Context Staging Input */}
        <div style={{ width: '300px', background: '#ffffff', borderRight: '1px solid #cbd5e1', padding: '18px', display: 'flex', flexDirection: 'column', boxSizing: 'border-box' }}>
          <h3 style={{ margin: '0 0 6px 0', fontSize: '14px', color: '#334155', fontWeight: '600' }}>📋 Staging Input String</h3>
          <textarea
            value={initialInputText}
            onChange={(e) => setInitialInputText(e.target.value)}
            style={{ height: '35%', width: '100%', padding: '8px', border: '1px solid #cbd5e1', borderRadius: '6px', resize: 'none', boxSizing: 'border-box', fontFamily: 'monospace', fontSize: '12px', background: '#f8fafc', marginBottom: '16px' }}
          />

          {/* Real-time Agent Live Log Monitor Terminal Layer Section */}
          <h3 style={{ margin: '0 0 6px 0', fontSize: '14px', color: '#334155', fontWeight: '600' }}>📡 Live Runtime Agent Trace Log</h3>
          <div style={{ flexGrow: 1, width: '100%', background: '#090d16', borderRadius: '6px', padding: '12px', color: '#38bdf8', fontFamily: 'monospace', fontSize: '11px', overflowY: 'auto', boxSizing: 'border-box', border: '1px solid #1e293b' }}>
            {isRunning && <p style={{ color: '#eab308', margin: 0 }}>⏳ Query running... Orchestrator topological queue processing model steps...</p>}
            {!isRunning && !executionResult && <p style={{ color: '#64748b', margin: 0 }}>► Waiting for canvas configuration pipeline run trigger execution.</p>}
            
            {executionResult && (
              <div>
                <p style={{ color: '#22c55e', margin: '0 0 8px 0', fontWeight: 'bold' }}>✓ Status Check: PIPELINE RUN COMPLETE SUCCESS</p>
                {Object.entries(executionResult.pipeline_context).map(([nodeKey, nodeOutput]) => (
                  <div key={nodeKey} style={{ marginBottom: '12px', borderBottom: '1px dashed #1e293b', paddingBottom: '8px' }}>
                    <span style={{ color: '#a855f7', fontWeight: 'bold' }}>[{nodeKey.toUpperCase()}]:</span>
                    <pre style={{ whiteSpace: 'pre-wrap', margin: '4px 0 0 0', color: '#e2e8f0', fontSize: '10px' }}>{String(nodeOutput)}</pre>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right Section Panel: The Interactive Graphic Visual Workspace */}
        <div style={{ flexGrow: 1, height: '100%' }}>
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onConnect={onConnect}
            nodeTypes={nodeTypes}
            fitView
          >
            <Controls />
            <MiniMap style={{ background: '#fff' }} zoomable pannable />
            <Background variant="dots" gap={14} size={1} color="#94a3b8" />
          </ReactFlow>
        </div>

      </div>
    </div>
  );
}