import os
import ollama
import json
from ollama import Client
from typing import Dict, Any, List

# ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")
# docker_client = Client(host=ollama_host)

class DynamicMultiAgentOrchestrator:
    def __init__(self, blueprint_path: str):
        # Load the visual blueprint JSON configuration
        #with open(blueprint_path, 'r') as f:
            #self.blueprint = json.load(f)
        self.blueprint = blueprint_path    
        # Map nodes by their unique ID for fast lookups
        self.nodes = {node["id"]: node for node in self.blueprint["nodes"]}
        self.edges = self.blueprint["edges"]
        
        # Pipeline execution memory context bucket
        self.pipeline_context = {}

        # 💡 DOCKER NETWORK CONNECTIVITY: Intercept the containerized hostname bridge
        ollama_host = os.getenv("OLLAMA_HOST", "http://ollama:11434")
        self.client = Client(host=ollama_host)

    def _determine_execution_order(self) -> List[str]:
        """
        Computes the topological sorting of the agent nodes.
        Ensures Agent A runs completely before its output feeds Agent B.
        """
        in_degree = {node_id: 0 for node_id in self.nodes}
        adj_list = {node_id: [] for node_id in self.nodes}
        
        for edge in self.edges:
            src, tgt = edge["source"], edge["target"]
            adj_list[src].append(tgt)
            in_degree[tgt] += 1
            
        # Find starting root nodes (nodes with no incoming connections)
        queue = [node_id for node_id in self.nodes if in_degree[node_id] == 0]
        order = []
        
        while queue:
            curr = queue.pop(0)
            order.append(curr)
            for neighbor in adj_list[curr]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
                    
        if len(order) != len(self.nodes):
            raise ValueError("🔄 Cyclical Loop Loop Error Intercepted! The visual graph contains a loop.")
        return order

    def _get_input_for_node(self, node_id: str, initial_input: str) -> str:
        """Looks backward across incoming edges to find the preceding node's output data."""
        incoming_sources = [e["source"] for e in self.edges if e["target"] == node_id]
        
        if not incoming_sources:
            # Root node reading the initial raw context text
            return initial_input
            
        # Extract output of the first connected preceding node from state tracking memory
        parent_id = incoming_sources[0]
        return self.pipeline_context.get(f"{parent_id}_output", "")

    def run(self, initial_payload: str) -> Dict[str, Any]:
        print(f"🚀 Initializing Orchestrator: {self.blueprint['pipeline_name']}")
        execution_schedule = self._determine_execution_order()
        
        current_data_stream = initial_payload
        
        for node_id in execution_schedule:
            node = self.nodes[node_id]
            print(f"\n🤖 [Executing Node]: {node['name']} (ID: {node_id}) using {node['model']}...")
            
            # Fetch context data from connected ancestors
            current_data_stream = self._get_input_for_node(node_id, initial_payload)
            
            # Setup dynamic local LLM parameters
            kwargs = {
                "model": node["model"],
                "messages": [
                    {"role": "system", "content": node["system_prompt"]},
                    {"role": "user", "content": f"Input context dataset to process:\n{current_data_stream}"}
                ]
            }
            
            # If it's the Extractor or Mapper node, append structural format rules dynamically
            if node_id == "node_extractor":
                kwargs["format"] = "json"
            elif node_id == "node_mapper":
                # We tell Agent 2 to return valid JSON mapping properties directly
                kwargs["format"] = "json" 
                
            # Fire local LLM operation step
            response = self.client.chat(**kwargs)
            agent_result = response['message']['content'].strip()
            
            # 💡 THE RETURN OUTPUT TOGGLE RULE:
            # If checked (True), persist output token data to state map layer
            if node.get("returns_output", True):
                self.pipeline_context[f"{node_id}_output"] = agent_result
                print(f"📥 Saved Output Context for downstream consumer wires.")
            else:
                print(f"🔇 Node configured to not return/persist data streams.")
                
        return self.pipeline_context
    

if __name__ == "__main__":
    # Simulate a messy web form form notification dump landing in your system staging environment
    messy_form_email = """
    <html>
        <body>
            <h3>New Contact Notification [ID: #5082]</h3>
            <p><strong>Name Given:</strong> Saurabh Dang</p>
            <p><strong>Contact Info:</strong> +91-9876543210</p>
            <p><strong>Project Requirements:</strong> We want to build an AI multi-agent platform utilizing React Flow canvases and Python FastAPI modules. Estimated launch timeline is 3 months.</p>
            <p><strong>Besoins Budget:</strong> $20,000 USD</p>
            <footer>Automated email notice. Disclaimer privacy applies.</footer>
        </body>
    </html>
    """
    
    # Instantiate engine pointing directly to our configuration map file
    orchestrator = DynamicMultiAgentOrchestrator("pipeline_blueprint.json")
    
    # Run the continuous state machine trace
    final_output_context = orchestrator.run(messy_form_email)
    
    print("\n🏁 ==========================================")
    print("🎯 FINAL EXECUTION PIPELINE CONTEXT RESULT:")
    print("==============================================")
    print(json.dumps(final_output_context, indent=2))