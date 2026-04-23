import React, { useState } from 'react';
import { api, saveApiUrl } from '../api';
import { motion } from 'framer-motion';
import { Settings, Server, CheckCircle, XCircle, Info } from 'lucide-react';

const MotionDiv = motion.div;

function Config() {
    const [url, setUrl] = useState(api.defaults.baseURL);
    const [status, setStatus] = useState(null);

    const testConnection = async () => {
        try {
            await api.get('/');
            setStatus('success');
        } catch {
            setStatus('error');
        }
    };

    const handleSave = () => {
        saveApiUrl(url);
    };

    return (
        <MotionDiv initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="max-w-md mx-auto p-4 space-y-6">
            <header className="mb-6">
                <h1 className="text-2xl font-bold text-white flex items-center gap-2">
                    <Settings className="text-primary-400" /> Settings
                </h1>
                <p className="text-slate-400 text-sm mt-1">Configure application preferences.</p>
            </header>

            <MotionDiv initial={{ y: 20, opacity: 0 }} animate={{ y: 0, opacity: 1 }} className="bg-slate-800/40 border border-slate-700/50 p-6 rounded-3xl shadow-lg relative overflow-hidden">
                <div className="absolute top-0 right-0 p-4 opacity-10">
                    <Server size={120} />
                </div>

                <h3 className="text-xl font-bold text-white mb-2 relative z-10 flex items-center gap-2">
                    Backend Connection
                </h3>
                <p className="text-sm text-slate-400 mb-6 relative z-10">
                    Enter the URL of your FastAPI backend server. If running locally on another device, use its local IP address (e.g., http://192.168.1.5:8000).
                </p>

                <div className="relative z-10 space-y-4">
                    <input
                        className="w-full bg-slate-900/50 border border-slate-700 rounded-xl px-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:border-primary-500 focus:ring-1 focus:ring-primary-500 transition-colors"
                        value={url}
                        onChange={(e) => setUrl(e.target.value)}
                        placeholder="http://192.168.x.x:8000"
                    />

                    <div className="flex gap-3">
                        <button
                            className="flex-1 bg-slate-700 hover:bg-slate-600 text-white font-semibold py-3 px-4 rounded-xl transition-colors"
                            onClick={testConnection}
                        >
                            Test Link
                        </button>
                        <button
                            className="flex-1 bg-primary-600 hover:bg-primary-500 text-white font-semibold py-3 px-4 rounded-xl transition-colors shadow-lg shadow-primary-500/20"
                            onClick={handleSave}
                        >
                            Save & Reload
                        </button>
                    </div>

                    {status === 'success' && (
                        <MotionDiv initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="flex items-center gap-2 text-emerald-400 bg-emerald-400/10 border border-emerald-400/20 p-3 rounded-lg text-sm mt-4">
                            <CheckCircle size={18} /> Connection Successful! Backend is reachable.
                        </MotionDiv>
                    )}
                    {status === 'error' && (
                        <MotionDiv initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="flex items-center gap-2 text-red-400 bg-red-400/10 border border-red-400/20 p-3 rounded-lg text-sm mt-4">
                            <XCircle size={18} /> Connection Failed. Ensure the server is running and accessible on this network.
                        </MotionDiv>
                    )}
                </div>
            </MotionDiv>

            <MotionDiv initial={{ y: 20, opacity: 0 }} animate={{ y: 0, opacity: 1 }} transition={{ delay: 0.1 }} className="bg-slate-800/40 border border-slate-700/50 p-6 rounded-3xl shadow-lg flex items-start gap-4">
                <div className="w-12 h-12 bg-primary-500/20 rounded-full flex items-center justify-center shrink-0 text-primary-400">
                    <Info size={24} />
                </div>
                <div>
                    <h3 className="text-lg font-bold text-white mb-1">About App</h3>
                    <p className="text-sm text-slate-400">
                        Voice Attendance Tracker v2.0
                        <br />
                        A secure, biometric attendance system designed for modern classrooms.
                    </p>
                </div>
            </MotionDiv>
        </MotionDiv>
    );
}

export default Config;
