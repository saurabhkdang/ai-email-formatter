import os
import json
import mysql.connector
import ollama
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

# ==========================================
# MASTER SCHEMA DEFINITION
# ==========================================
class LeadMasterSchema(BaseModel):
    """The strict database structure required for the master_leads table."""
    first_name: Optional[str] = Field(None, description="The lead's given or first name.")
    last_name: Optional[str] = Field(None, description="The lead's surname or family name.")
    email_address: Optional[str] = Field(None, description="Valid extracted contact email address.")
    phone: Optional[str] = Field(None, description="Any telephone, mobile, cell, or contact number.")
    company_name: Optional[str] = Field(None, description="The company, organization, or employer name.")
    # requirements: Optional[str] = Field(None, description="Project specs, user comments, requirements or notes about what they need.")
    
    # ENHANCED TARGETING FOR THE COMMENTS FIELD
    comments: Optional[str] = Field(
        None, 
        description="MANDATORY: Extract the main message body, requirements, project notes, details, requests, or questions here. Look for sections labeled 'Requirements', 'Project Notes', 'Besoins', 'What we need', 'Comments', or 'Message'."
    )

    # NEW SEMANTIC FALLBACK FIELDS
    raw_name: Optional[str] = Field(
        None, 
        description="If the email only specifies 'Name', 'Client', or 'Contact Name' without separating first and last, extract it here completely."
    )
    
    additional_metadata: Optional[Dict[str, Any]] = Field(
        None, 
        description="A key-value dictionary of any other useful fields found that do not fit the main columns (e.g., budget, timeline)."
    )

# ==========================================
# LOCAL AI AGENT FUNCTION (OLLAMA)
# ==========================================
def run_extraction_agent(raw_email_body: str) -> LeadMasterSchema:
    """
    Acts as the Ingestion, Extractor, and Mapping agents combined using local Ollama.
    Handles unseparated name fields intelligently by pre-splitting them.
    """
    system_instruction = """
    You are an expert Lead Extraction and Schema Mapping Agent.
    
    1. Ingestion/Cleanup: Disregard email signatures, corporate legal disclaimers, tracker IDs, and raw HTML noise.
    2. Extraction & Intelligent Splitting: 
       - Look for lead names under headings like "Name", "Client", "Contact Name", "User", etc.
       - If you find a single full name, dynamically split it into 'first_name' and 'last_name'.
       - Copy the original combined name string into the 'raw_name' field as a backup safety marker.
    3. Mapping & Redirection (CRITICAL): 
       - Map variations like "tele", "cell", "contact number", "phone no", or "Tel No." straight to the 'phone' schema key.
       - FORCED COMMENTS ROUTING: Find any text representing user requirements, project specs, custom messages, form notes, or user requests. You MUST map this strictly to the 'comments' schema key.
       - STRICT METADATA LIMITATION: The 'additional_metadata' dictionary is ONLY for explicit, short, key-value structural metrics (like 'budget', 'timeline', 'source', or 'country'). 
       - NEVER put multi-word user requirements, descriptions, or messages inside 'additional_metadata'. If it looks like a note or requirement, it belongs in 'requirements'.
    
    You MUST respond strictly with a single JSON object matching the requested schema. Do not include markdown code fences or explanation text.
    """

    response = ollama.chat(
        model='gemma4:31b-cloud',
        messages=[
            {"role": "system", "content": system_instruction},
            {"role": "user", "content": f"Extract and map this raw text: \n\n{raw_email_body}"}
        ],
        options={
            "temperature": 0.1 
        },
        format=LeadMasterSchema.model_json_schema() 
    )
    
    extracted_data = LeadMasterSchema.model_validate_json(response['message']['content'])
    
    # SECONDARY PYTHON BACKUP: If the LLM still missed splitting but caught the raw_name
    if extracted_data.raw_name and not extracted_data.first_name:
        name_parts = extracted_data.raw_name.strip().split(" ", 1)
        extracted_data.first_name = name_parts[0]
        if len(name_parts) > 1:
            extracted_data.last_name = name_parts[1]
            
    return extracted_data

# ==========================================
# VALIDATOR AGENT FUNCTION
# ==========================================
def validate_extracted_data(data: LeadMasterSchema) -> tuple[bool, str]:
    """
    Acts as the Validator Agent. Evaluates data integrity prior to running DB inserts.
    """
    # Expanded Validation Checklist: Accept the entry if ANY naming field is recovered
    if not data.first_name and not data.last_name and not data.raw_name and not data.company_name:
        return False, "Rejected: Missing all identifying lead names, clients, or corporate entities."
    
    if data.email_address and "@" not in data.email_address:
        return False, f"Invalid email structure detected: {data.email_address}"
        
    return True, "Passed validation"

# ==========================================
# MAIN EXECUTION PIPELINE
# ==========================================
def process_email_pipeline():
    # Establish Connection to your MySQL Instance
    db_config = {
        'host': 'localhost',
        'user': 'root',
        'password': '',
        'database': 'emailer'
    }
    
    conn = mysql.connector.connect(**db_config)
    cursor = conn.cursor(dictionary=True)
    
    # 1. Fetch unprocessed emails from the staging table
    cursor.execute("SELECT id, email_body FROM staging_emails WHERE processed = 0")
    emails_to_process = cursor.fetchall()
    
    if not emails_to_process:
        print("No new emails found in staging_emails.")
        return

    for row in emails_to_process:
        staging_id = row['id']
        raw_body = row['email_body']
        
        print(f"\n[Processing Staging ID: {staging_id}] Running local Ollama Agent...")
        
        try:
            # Step 2: Run local Ollama Extraction & Mapping Agent
            extracted_lead = run_extraction_agent(raw_body)
            
            # Step 3: Run Validation Agent Checks
            is_valid, reason = validate_extracted_data(extracted_lead)
            
            if is_valid:
                # Step 4: INSERT structured output into master_leads table
                insert_query = """
                    INSERT INTO master_leads 
                    (first_name, last_name, email_address, phone, company_name, requirements, additional_metadata)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                
                metadata_json = json.dumps(extracted_lead.additional_metadata) if extracted_lead.additional_metadata else None
                
                cursor.execute(insert_query, (
                    extracted_lead.first_name,
                    extracted_lead.last_name,
                    extracted_lead.email_address,
                    extracted_lead.phone,
                    extracted_lead.company_name,
                    extracted_lead.comments,
                    metadata_json
                ))
                print(" -> Success: Lead mapped and saved to master_leads table.")
                
            else:
                print(f" -> Failed Validation: {reason}. Routing to manual review queue.")
                insert_fail_query = """
                    INSERT INTO emails_failed_review (staging_id, raw_body, failure_reason)
                    VALUES (%s, %s, %s)
                """
                cursor.execute(insert_fail_query, (staging_id, raw_body, reason))
            
            # Step 5: Mark staging record as processed
            cursor.execute("UPDATE staging_emails SET processed = 1 WHERE id = %s", (staging_id,))
            conn.commit()

        except Exception as e:
            conn.rollback()
            print(f"💥 Critical parsing crash on entry {staging_id}: {str(e)}")
            try:
                cursor.execute("""
                    INSERT INTO emails_failed_review (staging_id, raw_body, failure_reason)
                    VALUES (%s, %s, %s)
                """, (staging_id, raw_body, f"System Crash: {str(e)}"))
                cursor.execute("UPDATE staging_emails SET processed = 1 WHERE id = %s", (staging_id,))
                conn.commit()
            except Exception:
                pass

    cursor.close()
    conn.close()

if __name__ == "__main__":
    process_email_pipeline()