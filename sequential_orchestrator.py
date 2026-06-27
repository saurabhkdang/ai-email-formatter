import ollama
import json
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

# ==========================================
# 1. DATA MODEL DEFINITION (The Target Schema)
# ==========================================
class LeadMasterSchema(BaseModel):
    """The strict database structure required for the master_leads table."""
    first_name: Optional[str] = Field(None, description="The lead's given or first name.")
    last_name: Optional[str] = Field(None, description="The lead's surname or family name.")
    email_address: Optional[str] = Field(None, description="Valid extracted contact email address.")
    
    # ✨ FIX 1: Allow phone_number to automatically map to phone
    phone: Optional[str] = Field(
        None, 
        description="Any telephone, mobile, cell, or contact number.",
        validation_alias="phone_number" 
    )
    
    company_name: Optional[str] = Field(None, description="The company, organization, or employer name.")
    comments: Optional[str] = Field(None, description="MANDATORY: Extract the main message body...")
    raw_name: Optional[str] = Field(None, description="If the email only specifies 'Name'...")
    
    additional_metadata: Optional[Dict[str, Any]] = Field(
        None, 
        description="A key-value dictionary of any other useful fields found that do not fit the main columns (e.g., budget, timeline)."
    )


# ==========================================
# 2. SEPARATE AGENT FUNCTIONS
# ==========================================

def run_ingestion_agent(raw_body: str) -> str:
    """Agent 1: Clean up messy formatting and headers."""
    print("🧹 [Ingestion Agent] Striping noise and isolating core text...")
    
    prompt = (
        "You are an Ingestion Agent. Clean the following text. "
        "Remove HTML tags, email signatures, legal disclaimers, and tracking metadata lines. "
        "Return ONLY the raw message content text as a clean paragraph."
    )
    
    response = ollama.chat(
        model="gemma4:31b-cloud",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": raw_body}
        ]
    )
    return response['message']['content']

# ==========================================
# 2. MULTI-AGENT EXTRACTION & TRANSLATION LAYER
# ==========================================
def run_extractor_agent(clean_text: str) -> LeadMasterSchema:
    """
    Acts as an internal multi-agent chain:
    Sub-Agent 1: Extracts raw text into a flat, raw JSON object.
    Sub-Agent 2: Maps those unstructured keys semantically to LeadMasterSchema.
    """
    
    # ---------------------------------------------------------
    # SUB-AGENT 1: The Raw Data Miner (Unconstrained)
    # ---------------------------------------------------------
    print("🤖 [Sub-Agent 1] Mining raw key-value fields naturally from text...")
    
    agent1_prompt = (
        "You are an information extraction assistant. Read the text and extract any user attributes, "
        "contact details, form fields, budgets, timelines, and messages. Output your findings as a simple, "
        "flat JSON object using the exact labels found in the text. Do not summarize or conversationalize."
    )
    
    response_1 = ollama.chat(
        model="gemma4:31b-cloud",
        format="json",  # Forces Ollama to speak in valid JSON, but allows dynamic keys
        messages=[
            {"role": "system", "content": agent1_prompt},
            {"role": "user", "content": clean_text}
        ]
    )
    raw_extracted_json = response_1['message']['content']
    
    # ---------------------------------------------------------
    # SUB-AGENT 2: The Semantic Translator (The Alignment Layer)
    # ---------------------------------------------------------
    print("🔮 [Sub-Agent 2] Translating raw text keys to Master Database Schema columns...")
    
    agent2_prompt = (
        "You are a Data Mapping Agent. You will be given a messy JSON object extracted from an email. "
        "Your job is to analyze the keys and values, understand their semantic meaning, and map them "
        "strictly to our target schema layout.\n\n"
        "CRITICAL ROUTING RULES:\n"
        "1. Any key or block of text implying user messages, 'what we need', specifications, needs, requirements, "
        "or descriptions MUST map directly to the 'comments' column.\n"
        "2. If full names are found together in a raw single field, split them cleanly into 'first_name' and 'last_name'.\n"
        "3. Any standalone keys like budget, estimated_budget, timeline, or country must be placed inside the "
        "'additional_metadata' dictionary."
    )
    
    response_2 = ollama.chat(
        model="gemma4:31b-cloud",
        format=LeadMasterSchema.model_json_schema(),  # Forces strict formatting to our clean model blueprint [cite: 193]
        messages=[
            {"role": "system", "content": agent2_prompt},
            {"role": "user", "content": f"Map this messy JSON data: {raw_extracted_json}"}
        ]
    )
    raw_json_string = response_2['message']['content']

    # =============================================================
    # ✨ THE CLEANUP FIX: Strip markdown fences if Ollama added them
    # =============================================================
    raw_json_string = raw_json_string.strip()
    if raw_json_string.startswith("```json"):
        raw_json_string = raw_json_string.replace("```json", "", 1)
    if raw_json_string.startswith("```"):
        raw_json_string = raw_json_string.replace("```", "", 1)
    if raw_json_string.endswith("```"):
        # Strip from the end
        raw_json_string = raw_json_string.rsplit("```", 1)[0]
    raw_json_string = raw_json_string.strip()
    # =============================================================
    print("Raw JSON : ", raw_json_string)

    # ---------------------------------------------------------
    # VALIDATION & BACKUP PARSING
    # ---------------------------------------------------------
    # Safely validate the aligned JSON string straight into our Pydantic Object [cite: 196]
    validated_object = LeadMasterSchema.model_validate_json(raw_json_string)
    
    return validated_object


def run_validator_agent(lead_data: LeadMasterSchema) -> str:
    """Agent 3: Evaluate data completeness to authorize database insertion."""
    print("🛡️ [Validator Agent] Checking data integrity constraints...")
    
    # Business rule: Must have at least a name or a company profile to be actionable
    if not (lead_data.first_name or lead_data.company_name):
        return "FAIL: Missing critical identifying entity properties."
        
    if lead_data.email_address and "@" not in lead_data.email_address:
        return "FAIL: Invalid email layout format structure intercepted."
        
    return "PASS"

# ==========================================
# 3. CENTRALIZED PIPELINE STATE LOOP
# ==========================================
def execute_multi_agent_pipeline(raw_email_input: str):
    print("🚀 Pipeline Started...")
    
    # The Global Memory Context dictionary
    pipeline_context = {
        "raw_input": raw_email_input,
        "clean_text": "",
        "extracted_lead": None,
        "status": "PENDING"
    }
    
    # Node 1 Execution
    pipeline_context["clean_text"] = run_ingestion_agent(pipeline_context["raw_input"])
    print(f"-> Intermediate Output: {pipeline_context['clean_text']}...\n") #[:60]
    
    # Node 2 Execution (Takes Node 1's output as its direct input payload)
    pipeline_context["extracted_lead"] = run_extractor_agent(pipeline_context["clean_text"])
    print(f"-> Intermediate Output: {pipeline_context['extracted_lead'].model_dump_json(indent=2)}\n")
    
    # Node 3 Execution (Takes Node 2's structured asset output to validate)
    pipeline_context["status"] = run_validator_agent(pipeline_context["extracted_lead"])
    print(f"🏁 Final Pipeline Status Outcome: {pipeline_context['status']}")
    
    return pipeline_context

if __name__ == "__main__":
    # A messy mock email mimicking your incoming web forms
    test_email_body = """
    <html>
        <body>
            <div class='header'>Form Submission ID: #994827</div>
            <p><strong>Message:</strong> Hello, we are looking for a quote regarding building a new React web application platform. We need it done within 3 months.</p>
            <p><strong>Client:</strong> Saurabh Dang</p>
            <p><strong>Contact No.:</strong> +91-9876543210</p>
            <p><strong>Est. Budget:</strong> $15,000</p>
            <hr>
            <small>Automated notification email disclaimer. Confidentiality applies.</small>
        </body>
    </html>
    """
    
    # Fire up the loop execution sequence
    final_state = execute_multi_agent_pipeline(test_email_body)