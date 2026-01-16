import re
from typing import Any, Dict, Optional
from .taxonomy import build_taxonomy, resolve_fact, FactStore
from .models import Question, Answer, FactInstance
from .context import normalize_context
from .router import IntentRouter
import json
from jinja2 import Template

try:
    from agents.llm_service import LLMService
    from agents.models import TaxonomyProposal
except ImportError:
    LLMService = None
    TaxonomyProposal = None

class QAEngine:
    def __init__(self):
        self.registry = build_taxonomy()
        self.router = IntentRouter()
        self.llm_service = LLMService() if LLMService else None
        
    def answer_question(self, question_text: str, user=None) -> Dict[str, Any]:
        question_obj = Question.objects.create(text=question_text, user=user)
        
        # 1. Deterministic Routing
        fact_version, context = self.router.route(question_text)
        
        # 2. LLM Fallback
        if not fact_version and self.llm_service:
            intent, context = self._parse_intent_llm(question_text)
            if intent:
                spec = self.registry.spec(intent)
                if spec and spec.version_obj:
                    fact_version = spec.version_obj

        if user:
            context['user'] = user

        if not fact_version:
            if self.llm_service:
                return self._handle_unrecognized_intent(question_obj, question_text)
            else:
                return {"text": "I'm sorry, I don't understand that question yet."}
            
        store = FactStore()
        try:
            # resolve_fact now returns a FactInstance
            fact_instance = resolve_fact(self.registry, store, fact_version.fact_definition.id, context)
            value = fact_instance.value
            
            answer_text = self._format_answer(fact_version.fact_definition.id, value, context)
            self._save_interaction(question_obj, fact_instance, answer_text)
            return {"text": answer_text}
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {"text": f"Error calculating answer: {str(e)}"}

    def _handle_unrecognized_intent(self, question_obj, text):
        schema_desc = "BankTransaction(date, amount, description), CreditCardTransaction(date, amount, category)"
        
        analysis = self.llm_service.analyze_unanswerable_question(text, schema_desc)
        
        if analysis.get("feasible"):
            fact_id = analysis.get("fact_id")
            logic_code = analysis.get("logic")
            # NEW: Capture schema and template
            params_schema = analysis.get("parameters_schema", {})
            out_template = analysis.get("output_template", "")
            
            proposal = None
            if TaxonomyProposal:
                proposal = TaxonomyProposal.objects.create(
                    question=text,
                    feasibility_analysis="Feasible",
                    proposed_fact_id=fact_id,
                    proposed_logic=logic_code,
                    proposed_schema=params_schema,
                    proposed_template=out_template,
                    status='pending'
                )
            
            return {
                "text": f"I can't answer that right now, but I've analyzed your question and it looks feasible. I've proposed a new fact '{fact_id}'. Would you like me to learn this capability?",
                "proposal_id": proposal.id if proposal else None,
                "proposal_logic": logic_code
            }
        else:
            return {"text": "I'm sorry, I don't have the data to answer that question."}

    def _parse_intent_llm(self, text: str) -> tuple[Optional[str], Dict[str, Any]]:
        # Pass full spec info including schema to LLM
        available_facts = []
        for fact_id, spec in self.registry.all_specs().items():
            if spec.kind == 'computed':
                available_facts.append({
                    "id": fact_id, 
                    "description": spec.description,
                    "schema": spec.parameters_schema # Pass schema to help LLM match constraints
                })
        
        result = self.llm_service.classify_intent(text, available_facts)
        
        intent = result.get("intent")
        context = result.get("context", {})
        
        if intent and intent not in self.registry.all_specs():
            intent = None
            
        return intent, context

    def _format_answer(self, fact_id: str, value: Any, context: Dict[str, Any]) -> str:
        # 1. Try to use the Jinja2 template if available
        spec = self.registry.spec(fact_id)
        if spec and spec.output_template:
            try:
                # Render template with value and context
                # We flatten context into the root namespace for easier access in template
                # Also normalize context for consistent rendering
                norm_ctx = normalize_context(context)
                render_ctx = {"value": value, **norm_ctx}
                return Template(spec.output_template).render(render_ctx)
            except Exception as e:
                print(f"Template rendering failed: {e}")
                # Fallback to default formatting

        # 2. Default formatting logic
        if isinstance(value, dict):
            target_category = context.get('category')
            if target_category:
                for k, v in value.items():
                    if k.lower() == target_category.lower():
                        return f"Spending on {k}: ${v:,.2f}"
                return f"No spending found for category '{target_category}'."

            lines = [f"Result for {fact_id.replace('_', ' ')}:"]
            for k, v in value.items():
                if isinstance(v, (int, float)):
                    lines.append(f"- {k}: ${v:,.2f}")
                else:
                    lines.append(f"- {k}: {v}")
            return "\n".join(lines)
        
        elif isinstance(value, (int, float)):
            return f"The result is ${value:,.2f}."
            
        return str(value)

    def _save_interaction(self, question_obj, fact_instance, answer_text):
        answer_obj = Answer.objects.create(
            question=question_obj,
            text=answer_text
        )
        answer_obj.facts_used.add(fact_instance)
