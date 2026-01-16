from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from .models import Conversation, Message
from facts.engine import QAEngine
from facts.taxonomy import build_taxonomy, to_dot
from agents.models import TaxonomyProposal
from facts.models import IntentRecognizer, FactDefinitionVersion
import json

@login_required
def chat_view(request):
    return render(request, 'conversations/chat.html')

@login_required
def capabilities_view(request):
    """
    Displays a list of questions the system can currently answer,
    along with their live answers for the current user.
    """
    engine = QAEngine()
    capabilities = []
    
    # Fetch all active intent recognizers
    recognizers = IntentRecognizer.objects.filter(
        fact_version__status='approved',
        fact_version__fact_definition__is_active=True
    ).select_related('fact_version', 'fact_version__fact_definition')
    
    for rec in recognizers:
        # Use example questions if available, otherwise use regex patterns as a fallback description
        questions = rec.example_questions if rec.example_questions else rec.regex_patterns
        
        # If we have regex patterns but no examples, we might want to show a generic message
        # But usually we should have examples.
        
        # For display, let's pick the first example question to run
        primary_question = questions[0] if questions else None
        
        if primary_question:
            # Clean up regex if it was used as a fallback (simple heuristic)
            if not rec.example_questions and primary_question.startswith('^') or '\\' in primary_question:
                 display_question = f"Matches pattern: {primary_question}"
                 answer_text = "(Pattern match only)"
            else:
                display_question = primary_question
                # Execute the question to get the live answer
                try:
                    response = engine.answer_question(display_question, user=request.user)
                    answer_text = response.get('text', 'No answer returned')
                except Exception as e:
                    answer_text = f"Error: {str(e)}"
            
            capabilities.append({
                'fact_id': rec.fact_version.fact_definition.id,
                'description': rec.fact_version.fact_definition.description,
                'question': display_question,
                'answer': answer_text,
                'all_examples': questions
            })
            
    return render(request, 'conversations/capabilities.html', {'capabilities': capabilities})

@login_required
def get_conversations(request):
    conversations = Conversation.objects.filter(user=request.user).order_by('-updated_at')
    data = [{'id': c.id, 'title': str(c), 'updated_at': c.updated_at} for c in conversations]
    return JsonResponse({'conversations': data})

@login_required
def get_messages(request, conversation_id):
    try:
        conversation = Conversation.objects.get(id=conversation_id, user=request.user)
        messages = conversation.messages.all()
        data = []
        for m in messages:
            msg_data = {
                'sender': m.sender, 
                'text': m.text, 
                'created_at': m.created_at,
                'proposal_id': m.related_proposal.id if m.related_proposal else None
            }
            data.append(msg_data)
        return JsonResponse({'messages': data})
    except Conversation.DoesNotExist:
        return JsonResponse({'error': 'Conversation not found'}, status=404)

@csrf_exempt
@login_required
def send_message(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        text = data.get('text')
        conversation_id = data.get('conversation_id')
        
        if not text:
            return JsonResponse({'error': 'No text provided'}, status=400)
            
        if conversation_id:
            try:
                conversation = Conversation.objects.get(id=conversation_id, user=request.user)
            except Conversation.DoesNotExist:
                return JsonResponse({'error': 'Conversation not found'}, status=404)
        else:
            title = text[:30] + "..." if len(text) > 30 else text
            conversation = Conversation.objects.create(user=request.user, title=title)
            
        Message.objects.create(conversation=conversation, sender='user', text=text)
        
        engine = QAEngine()
        response_data = engine.answer_question(text, user=request.user)
        
        answer_text = response_data.get('text', "Error")
        proposal_id = response_data.get('proposal_id')
        
        bot_msg = Message.objects.create(conversation=conversation, sender='bot', text=answer_text)
        if proposal_id:
            bot_msg.related_proposal_id = proposal_id
            bot_msg.save()
        
        return JsonResponse({
            'conversation_id': conversation.id,
            'user_message': {'sender': 'user', 'text': text},
            'bot_message': {
                'sender': 'bot', 
                'text': answer_text,
                'proposal_id': proposal_id
            }
        })
        
    return JsonResponse({'error': 'Invalid method'}, status=405)

@csrf_exempt
@login_required
def approve_proposal(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        proposal_id = data.get('proposal_id')
        
        try:
            proposal = TaxonomyProposal.objects.get(id=proposal_id)
            
            if proposal.status != 'pending':
                return JsonResponse({'error': 'Proposal already processed'}, status=400)
                
            # Use the model method to approve and create version
            proposal.approve(user=request.user)
            
            engine = QAEngine()
            response_data = engine.answer_question(proposal.question, user=request.user)
            new_answer = response_data.get('text')
            
            return JsonResponse({
                'success': True,
                'new_answer': new_answer
            })
            
        except TaxonomyProposal.DoesNotExist:
            return JsonResponse({'error': 'Proposal not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Invalid method'}, status=405)

@login_required
def taxonomy_graph_view(request):
    reg = build_taxonomy()
    dot_content = to_dot(reg)
    return HttpResponse(dot_content, content_type="text/plain")
