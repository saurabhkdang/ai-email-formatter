from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
from dynamic_orchestrator import DynamicMultiAgentOrchestrator
import os
import json
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

app = FastAPI(title="Visual Agent Builder Backend Execution Service")

# Allow your React frontend to communicate securely with this API wrapper
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, change this to your React app's specific URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define the incoming data contracts from the React UI
class PipelineRunRequest(BaseModel):
    graph_blueprint: Dict[str, Any]  # Matches your pipeline_blueprint.json layout
    initial_input: str               # The raw email string to process

@app.post("/api/pipeline/run")
async def run_visual_pipeline(request: PipelineRunRequest):
    try:
        orchestrator = DynamicMultiAgentOrchestrator(request.graph_blueprint)
        execution_context = orchestrator.run(request.initial_input)
        return {
            "status": "success",
            "pipeline_context": execution_context
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def run_visual_pipelin1(request: PipelineRunRequest):
    try:
        # Save the incoming graph layout to a temporary run blueprint file
        temp_blueprint_path = "temp_run_blueprint.json"
        with open(temp_blueprint_path, "w") as f:
            json.dump(request.graph_blueprint, f, indent=2)
            
        # Instantiate your orchestrator engine using the sent layout
        orchestrator = DynamicMultiAgentOrchestrator(temp_blueprint_path)
        
        # Execute the multi-agent graph chain sequence
        execution_context = orchestrator.run(request.initial_input)
        
        # Clean up the temporary configuration file
        if os.path.exists(temp_blueprint_path):
            os.remove(temp_blueprint_path)
            
        return {
            "status": "success",
            "pipeline_context": execution_context
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline execution runtime failure: {str(e)}")

app.mount("/", StaticFiles(directory="static", html=True), name="static")
# Serve index.html for everything else
@app.get("/{full_path:path}")
async def serve_react(full_path: str):
    return FileResponse("static/index.html")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)