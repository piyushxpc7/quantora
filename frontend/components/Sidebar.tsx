import Link from 'next/link';

const Sidebar = () => {
    return (
        <aside className="w-64 bg-slate-900 text-white h-screen fixed left-0 top-0 flex flex-col border-r border-slate-800">
            <div className="p-6 border-b border-slate-800">
                <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
                    QUANTORA
                </h1>
                <p className="text-xs text-slate-400 mt-1">AI Quant Ecosystem</p>
            </div>

            <nav className="flex-1 p-4 space-y-2">
                <Link href="/" className="flex items-center px-4 py-3 text-slate-300 hover:bg-slate-800 hover:text-white rounded-lg transition-all duration-200 group">
                    <span className="mr-3">📊</span>
                    Dashboard
                </Link>
                <Link href="/agents" className="flex items-center px-4 py-3 text-slate-300 hover:bg-slate-800 hover:text-white rounded-lg transition-all duration-200 group">
                    <span className="mr-3">🤖</span>
                    AI Agents
                </Link>
                <Link href="/drift" className="flex items-center px-4 py-3 text-slate-300 hover:bg-slate-800 hover:text-white rounded-lg transition-all duration-200 group">
                    <span className="mr-3">📉</span>
                    Drift Monitor
                </Link>
                <Link href="/settings" className="flex items-center px-4 py-3 text-slate-300 hover:bg-slate-800 hover:text-white rounded-lg transition-all duration-200 group">
                    <span className="mr-3">⚙️</span>
                    Settings
                </Link>
            </nav>

            <div className="p-4 border-t border-slate-800">
                <div className="flex items-center">
                    <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-blue-500 to-purple-500 flex items-center justify-center text-xs font-bold">
                        PC
                    </div>
                    <div className="ml-3">
                        <p className="text-sm font-medium">Piyush Chandra</p>
                        <p className="text-xs text-slate-500">Quant Researcher</p>
                    </div>
                </div>
            </div>
        </aside>
    );
};

export default Sidebar;
