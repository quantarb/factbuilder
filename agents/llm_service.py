import os
from typing import List, Dict, Any, Optional
from django.conf import settings
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.output_parsers import JsonOutputParser
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field
from django.core.management import call_command
from io import StringIO

class FeasibilityAnalysis(BaseModel):
    feasible: bool = Field(description="Whether the question can be answered by the available data")
    fact_id: str = Field(description="A proposed unique ID for the new fact (snake_case). It should be GENERAL (e.g. 'spending_in_period' not 'spending_last_month').", default=None)
    logic: str = Field(description="Valid Python code for the producer function. It must be a function body that accepts (deps, context) and returns a value.", default=None)
    parameters_schema: Dict[str, Any] = Field(description="JSON Schema describing the context parameters this fact requires (e.g. start_date, end_date, category).", default_factory=dict)
    output_template: str = Field(description="A Jinja2-style template string to format the answer. Use {{value}} for the result and {{context_var}} for context.", default=None)
    reason: str = Field(description="Reasoning for the decision", default=None)

class CapabilitySuggestion(BaseModel):
    question: str = Field(description="A question the system could answer")
    reasoning: str = Field(description="Why this question is answerable with current data")

class CapabilityList(BaseModel):
    suggestions: List[CapabilitySuggestion]

class IntentClassification(BaseModel):
    intent: Optional[str] = Field(description="The ID of the fact that best answers the question, or null if none match.")
    context: Dict[str, Any] = Field(description="Extracted entities like 'date', 'account_name', 'category', 'start_date', 'end_date'.")

def get_schema_snapshot(apps=("facts", "finance")) -> str:
    buf = StringIO()
    try:
        # Try to use the print_schema command if it exists
        call_command("print_schema", "--pretty", "--apps", *apps, stdout=buf)
        return buf.getvalue()
    except Exception:
        # Fallback if command doesn't exist or fails
        return """
        BankTransaction(date, amount, description, type, account_name, balance)
        CreditCardTransaction(date, amount, category, description, account_name)
        Account(name, user)
        """

class LLMService:
    def __init__(self):
        api_key = settings.OPENAI_API_KEY
        if not api_key:
            api_key = os.environ.get("OPENAI_API_KEY")
            
        if not api_key:
            print("WARNING: OPENAI_API_KEY not found. LLM features will fail.")
            self.llm = None
        else:
            self.llm = ChatOpenAI(temperature=0, model="gpt-4o", api_key=api_key)

    def classify_intent(self, question: str, available_facts: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Uses LLM to map a natural language question to an existing fact ID and extract context.
        """
        if not self.llm:
            return {"intent": None, "context": {}}

        parser = JsonOutputParser(pydantic_object=IntentClassification)
        
        # Include schema info in description to help LLM match constraints
        facts_desc = []
        for f in available_facts:
            schema_str = str(f.get('schema', {}))
            facts_desc.append(f"- {f['id']}: {f['description']} (Params: {schema_str})")
        
        facts_desc_str = "\n".join(facts_desc)

        prompt = PromptTemplate(
            template="""
            You are an intent classifier for a financial QA system.
            
            The user asked: "{question}"
            
            Here are the available facts (intents) the system can compute:
            {facts_desc}
            
            Your job is to:
            1. Identify if the question maps to one of these facts.
            2. Extract relevant context variables based on the fact's parameters.
            
            IMPORTANT:
            - If the user asks for a specific filter (e.g. "last month") but the fact's parameters do not support it (e.g. it has no date parameter), then it is a MISMATCH. Set intent to null.
            - If the user asks "spending on Gas", extract "Gas" as the 'category' parameter if the fact supports it.
            - If the user asks "last month", calculate 'start_date' and 'end_date' for the previous month relative to today.
            
            {format_instructions}
            """,
            input_variables=["question", "facts_desc"],
            partial_variables={"format_instructions": parser.get_format_instructions()},
        )

        chain = prompt | self.llm | parser
        
        try:
            result = chain.invoke({"question": question, "facts_desc": facts_desc_str})
            return result
        except Exception as e:
            print(f"Intent Classification Error: {e}")
            return {"intent": None, "context": {}}

    def analyze_unanswerable_question(self, question: str, available_schema: str) -> Dict[str, Any]:
        """
        Asks the LLM if a question can be answered by modifying the taxonomy.
        """
        if not self.llm:
            return {"feasible": False, "reason": "LLM not configured"}

        # Get dynamic schema
        dynamic_schema = get_schema_snapshot()
        
        parser = JsonOutputParser(pydantic_object=FeasibilityAnalysis)

        prompt = PromptTemplate(
            template="""
            You are an expert Python developer for a financial QA system.
            The system has a 'Fact Taxonomy' where facts are computed by producer functions.
            
            The system provides a base fact 'all_transactions' which is a Pandas DataFrame derived from the following models:
            
            SCHEMA:
            {schema}
            
            RULES:
            - Use ONLY the models/fields provided in SCHEMA.
            - Do NOT invent new fields/models.
            - If you need a concept not in SCHEMA (e.g. 'Merchant', 'Vendor'), respond exactly:
              feasible: False
              reason: "This question cannot be answered yet because merchant information does not exist."
            
            The user asked: "{question}"
            
            Can this be answered by writing a Python function that processes 'all_transactions'?
            
            CRITICAL CONSTRAINT:
            The 'description' field is opaque text. 
            We do NOT perform string matching on descriptions to infer merchants.
            
            If YES (and not about merchants):
            1. Set feasible=True.
            2. Provide a 'fact_id' (snake_case). 
               IMPORTANT: Make the fact GENERAL. 
               - If the user asks "spending on Gas", create a fact 'spending_by_category' that accepts a 'category' parameter, NOT 'spending_on_gas'.
               - If the user asks "spending last month", create a fact 'spending_in_period' that accepts 'start_date' and 'end_date', NOT 'spending_last_month'.
            3. Provide 'parameters_schema' (JSON Schema) for the GENERAL parameters (e.g. category, start_date, end_date).
            4. Provide 'output_template' (Jinja2 string) for the answer.
            5. Provide the 'logic' as Python code. 
               - The code should be the BODY of a function `def producer(deps, context):`.
               - Access the dataframe via `df = deps['all_transactions']`.
               - Use `context.get('param_name')` to filter the data.
               - Return the result.
            
            {format_instructions}
            """,
            input_variables=["question", "schema"],
            partial_variables={"format_instructions": parser.get_format_instructions()},
        )

        chain = prompt | self.llm | parser
        
        try:
            result = chain.invoke({"question": question, "schema": dynamic_schema})
            return result
        except Exception as e:
            return {"feasible": False, "reason": f"LLM Error: {str(e)}"}

    def suggest_capabilities(self, current_taxonomy_description: str) -> List[Dict[str, str]]:
        # (Same as before)
        if not self.llm:
            return []

        parser = JsonOutputParser(pydantic_object=CapabilityList)
        
        schema_context = get_schema_snapshot()

        prompt = PromptTemplate(
            template="""
            You are an expert product manager for a financial app.
            
            We have the following data available:
            {schema}
            
            The system currently supports these questions/facts:
            {current_taxonomy}
            
            Suggest 3-5 NEW, distinct questions that users might want to ask.
            
            {format_instructions}
            """,
            input_variables=["schema", "current_taxonomy"],
            partial_variables={"format_instructions": parser.get_format_instructions()},
        )

        chain = prompt | self.llm | parser
        
        try:
            result = chain.invoke({
                "schema": schema_context, 
                "current_taxonomy": current_taxonomy_description
            })
            return [s if isinstance(s, dict) else s.dict() for s in result.get('suggestions', [])]
        except Exception as e:
            print(f"LLM Error: {e}")
            return []
