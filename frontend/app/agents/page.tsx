'use client';

import { useState } from 'react';

export default function AgentsPage() {
    const [messages, setMessages] = useState([
        { role: 'system', content: 'Quantora Agent System initialized. How can I help you today?' }
    ]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);

    const sendMessage = async () => {
        if (!input.trim()) return;

        const userMsg = { role: 'user', content: input };
        setMessages(prev => [...prev, userMsg]);
        setInput('');
        setLoading(true);

        try {
            // Mock API call for now
            // In real app: await fetch('/api/v1/agents/workflow', ...)
            setTimeout(() => {
                const response = {
                    role: 'assistant',
                    content: `I've processed your request: "${userMsg.content}".\n\n**Strategy Agent**: Generated momentum idea.\n**Backtest Agent**: CAGR 12%.\n**Risk Agent**: Approved.\n**Portfolio Agent**: Allocation updated.`
                };
                setMessages(prev => [...prev, response]);
                setLoading(false);
            }, 1500);
        } catch (error) {
            console.error(error);
            setLoading(false);
        }
    };

    return (
        <div className="h-[calc(100vh-8rem)] flex flex-col">
            <header className="mb-6">
                <h1 className="text-3xl font-bold text-white">Multi-Agent Chat</h1>
                <p className="text-slate-400 mt-1">Collaborate with Strategy, Backtest, Risk, and Portfolio Agents</p>
            </header>

            <div className="flex-1 bg-slate-900 rounded-xl border border-slate-800 flex flex-col overflow-hidden">
                {/* Chat Window */}
                <div className="flex-1 overflow-y-auto p-6 space-y-6">
                    {messages.map((msg, idx) => (
                        <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                            <div className={`max-w-3xl p-4 rounded-2xl ${msg.role === 'user'
                                    ? 'bg-blue-600 text-white rounded-br-none'
                                    : 'bg-slate-800 text-slate-200 rounded-bl-none'
                                }`}>
                                <p className="whitespace-pre-wrap">{msg.content}</p>
                            </div>
                        </div>
                    ))}
                    {loading && (
                        <div className="flex justify-start">
                            <div className="bg-slate-800 p-4 rounded-2xl rounded-bl-none flex items-center space-x-2">
                                <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce"></div>
                                <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce delay-75"></div>
                                <div className="w-2 h-2 bg-blue-400 rounded-full animate-bounce delay-150"></div>
                            </div>
                        </div>
                    )}
                </div>

                {/* Input Area */}
                <div className="p-4 border-t border-slate-800 bg-slate-900">
                    <div className="flex space-x-4">
                        <input
                            type="text"
                            value={input}
                            onChange={(e) => setInput(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
                            placeholder="Describe a trading strategy (e.g., 'Momentum on Tech stocks')..."
                            className="flex-1 bg-slate-950 border border-slate-800 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-blue-500 transition-colors"
                        />
                        <button
                            onClick={sendMessage}
                            disabled={loading}
                            className="bg-blue-600 hover:bg-blue-500 text-white px-6 py-3 rounded-lg font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            Send
                        </button>
                    </div>
                </div>
            </div>
        </div>
    );
}
