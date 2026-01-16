from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from .models import Conversation, Message
from facts.engine import QAEngine
from facts.taxonomy import build_taxonomy, to_dot
from agents.models import TaxonomyProposal
from facts.models import DynamicFact
import json

@login_required
def chat_view(request):
    return render(request, 'conversations/chat.html')

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
                
            # Create DynamicFact with new fields
            DynamicFact.objects.create(
                id=proposal.proposed_fact_id,
                description=f"Auto-generated for: {proposal.question}",
                kind="computed",
                data_type="scalar",
                requires=["all_transactions"],
                code=proposal.proposed_logic,
                # NEW: Save schema and template
                parameters_schema=proposal.proposed_schema,
                output_template=proposal.proposed_template,
                is_active=True
            )
            
            proposal.status = 'approved'
            proposal.save()
            
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
