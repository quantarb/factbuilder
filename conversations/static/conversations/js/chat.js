const { useState, useEffect, useRef } = React;

function App() {
    const [conversations, setConversations] = useState([]);
    const [currentConversationId, setCurrentConversationId] = useState(null);
    const [messages, setMessages] = useState([]);
    const [inputText, setInputText] = useState("");
    const [loading, setLoading] = useState(false);
    const [showGraph, setShowGraph] = useState(false);
    const [graphDot, setGraphDot] = useState("");
    const messagesEndRef = useRef(null);

    useEffect(() => {
        fetchConversations();

        // Check for query param 'q' to auto-send message
        const params = new URLSearchParams(window.location.search);
        const initialQuestion = params.get('q');
        if (initialQuestion) {
            // Clear the query param so it doesn't re-trigger on refresh
            window.history.replaceState({}, document.title, window.location.pathname);
            // We need to wait a bit or handle this carefully to ensure state is ready
            // But since handleSendMessage is async and depends on state, we can just call it
            // However, we need to set input text first or pass it directly.
            // Let's pass it directly to a modified send function or just set it and trigger.
            // Better: modify handleSendMessage to accept optional text
            handleSendMessage(initialQuestion);
        }
    }, []);

    useEffect(() => {
        if (currentConversationId) {
            fetchMessages(currentConversationId);
        } else {
            setMessages([]);
        }
    }, [currentConversationId]);

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    useEffect(() => {
        if (showGraph && !graphDot) {
            fetchGraph();
        }
    }, [showGraph]);

    useEffect(() => {
        if (showGraph && graphDot) {
             d3.select("#graph").graphviz().renderDot(graphDot);
        }
    }, [showGraph, graphDot]);

    const scrollToBottom = () => {
        if (messagesEndRef.current) {
            messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
        }
    };

    const fetchConversations = async () => {
        const res = await fetch('/chat/api/conversations/');
        const data = await res.json();
        setConversations(data.conversations);
    };

    const fetchMessages = async (id) => {
        const res = await fetch(`/chat/api/conversations/${id}/messages/`);
        const data = await res.json();
        setMessages(data.messages);
    };

    const fetchGraph = async () => {
        const res = await fetch('/chat/api/taxonomy_graph/');
        const text = await res.text();
        setGraphDot(text);
    };

    const handleSendMessage = async (textOverride = null) => {
        const text = textOverride || inputText;
        if (!text || !text.trim()) return;
        
        if (!textOverride) {
            setInputText("");
        }
        setLoading(true);

        // Optimistic update
        // Note: if we are starting a new conversation (currentConversationId is null),
        // we might want to clear previous messages if any (though usually empty).
        // If we are in an existing conversation, we append.

        // If textOverride is present (from URL), we might be starting fresh or not.
        // For simplicity, if textOverride is used, we assume we want to send it to the current context
        // or a new one if none selected.

        const tempMessages = [...messages, { sender: 'user', text: text }];
        setMessages(tempMessages);

        try {
            const res = await fetch('/chat/api/send/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    text: text,
                    conversation_id: currentConversationId
                })
            });
            
            const data = await res.json();
            
            if (data.error) {
                console.error(data.error);
                return;
            }

            if (!currentConversationId) {
                setCurrentConversationId(data.conversation_id);
                fetchConversations(); // Refresh list to show new convo
            }
            
            // Update with actual response
            // data.bot_message now includes proposal_id if applicable
            // We need to be careful not to duplicate if we re-render or something,
            // but here we are just appending to state.
            // However, since we used tempMessages based on 'messages' state,
            // and 'messages' state might have changed if we were fetching in background (unlikely here),
            // it's safer to use functional update, but we need the bot message to follow the user message.

            setMessages(prev => {
                // We need to ensure we don't lose the user message we just added optimistically
                // But since we setMessages(tempMessages) before await, 'prev' here will be tempMessages
                // (unless other updates happened).
                // Actually, it's better to just append the bot message to the current state.
                return [...prev, data.bot_message];
            });
            
        } catch (err) {
            console.error("Error sending message:", err);
        } finally {
            setLoading(false);
        }
    };

    const handleApproveProposal = async (proposalId) => {
        setLoading(true);
        try {
            const res = await fetch('/chat/api/approve_proposal/', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ proposal_id: proposalId })
            });
            const data = await res.json();
            
            if (data.success) {
                // Add the new answer as a bot message
                setMessages(prev => [...prev, { 
                    sender: 'bot', 
                    text: "Proposal approved! Here is the answer:\n" + data.new_answer 
                }]);
                // Refresh graph if open
                if (showGraph) fetchGraph();
            } else {
                alert("Error approving proposal: " + data.error);
            }
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    const handleNewChat = () => {
        setCurrentConversationId(null);
    };

    return (
        <div className="flex h-screen">
            {/* Sidebar */}
            <div className="w-64 bg-white border-r border-gray-200 flex flex-col">
                <div className="p-4 border-b border-gray-200">
                    <button 
                        onClick={handleNewChat}
                        className="w-full bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2 px-4 rounded shadow transition"
                    >
                        + New Chat
                    </button>
                </div>
                <div className="flex-1 overflow-y-auto p-2">
                    {conversations.map(c => (
                        <div 
                            key={c.id}
                            onClick={() => setCurrentConversationId(c.id)}
                            className={`p-3 mb-1 rounded cursor-pointer truncate ${currentConversationId === c.id ? 'bg-blue-50 text-blue-700' : 'hover:bg-gray-50 text-gray-700'}`}
                        >
                            {c.title}
                        </div>
                    ))}
                </div>
                <div className="p-4 border-t border-gray-200">
                    <button
                        onClick={() => setShowGraph(!showGraph)}
                        className="w-full bg-gray-100 hover:bg-gray-200 text-gray-700 font-semibold py-2 px-4 rounded shadow transition"
                    >
                        {showGraph ? "Hide Graph" : "Show Taxonomy"}
                    </button>
                </div>
            </div>

            {/* Main Area */}
            <div className="flex-1 flex flex-col bg-white relative">
                {/* Graph Overlay */}
                {showGraph && (
                    <div className="absolute inset-0 z-20 bg-white flex flex-col">
                        <div className="p-4 border-b border-gray-200 flex justify-between items-center bg-gray-50">
                            <h2 className="text-lg font-bold text-gray-700">Fact Taxonomy Graph</h2>
                            <button onClick={() => setShowGraph(false)} className="text-gray-500 hover:text-gray-700">
                                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                                </svg>
                            </button>
                        </div>
                        <div className="flex-1 overflow-auto p-4" id="graph" style={{textAlign: "center"}}>
                            {!graphDot && <p>Loading graph...</p>}
                        </div>
                    </div>
                )}

                {/* Chat Header */}
                <div className="p-4 border-b border-gray-200 bg-white shadow-sm z-10">
                    <h1 className="text-xl font-bold text-gray-800">
                        {currentConversationId ? (conversations.find(c => c.id === currentConversationId) || {}).title : "New Conversation"}
                    </h1>
                </div>

                {/* Messages */}
                <div className="flex-1 overflow-y-auto p-6 space-y-4 bg-gray-50">
                    {messages.length === 0 && !loading && (
                        <div className="text-center text-gray-400 mt-20">
                            <p className="text-lg">Ask a question about your finances.</p>
                            <p className="text-sm">e.g., "What is my current balance?"</p>
                        </div>
                    )}
                    
                    {messages.map((m, idx) => (
                        <div key={idx} className={`flex ${m.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
                            <div className={`max-w-2xl p-4 shadow-sm ${m.sender === 'user' ? 'message-user' : 'message-bot'}`}>
                                <div className="whitespace-pre-wrap">{m.text}</div>
                                {m.proposal_id && (
                                    <div className="mt-3 pt-3 border-t border-blue-200">
                                        <button 
                                            onClick={() => handleApproveProposal(m.proposal_id)}
                                            className="bg-green-600 hover:bg-green-700 text-white text-sm font-semibold py-1 px-3 rounded shadow transition"
                                        >
                                            Yes, learn this capability
                                        </button>
                                    </div>
                                )}
                            </div>
                        </div>
                    ))}
                    
                    {loading && (
                        <div className="flex justify-start">
                            <div className="message-bot p-4 shadow-sm">
                                <div className="flex space-x-2">
                                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
                                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.4s'}}></div>
                                </div>
                            </div>
                        </div>
                    )}
                    <div ref={messagesEndRef} />
                </div>

                {/* Input */}
                <div className="p-4 border-t border-gray-200 bg-white">
                    <div className="flex space-x-4 max-w-4xl mx-auto">
                        <input 
                            type="text" 
                            value={inputText}
                            onChange={(e) => setInputText(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
                            placeholder="Type your question..."
                            className="flex-1 border border-gray-300 rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent shadow-sm"
                        />
                        <button 
                            onClick={() => handleSendMessage()}
                            disabled={!inputText.trim() || loading}
                            className="bg-blue-600 hover:bg-blue-700 disabled:bg-blue-300 text-white font-semibold py-2 px-6 rounded-lg shadow transition"
                        >
                            Send
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(<App />);