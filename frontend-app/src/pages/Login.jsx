import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { LogIn, ShieldCheck, Settings, Server, RefreshCcw, UserPlus } from 'lucide-react';
import { api, saveApiUrl } from '../api';
import { motion, AnimatePresence } from 'framer-motion';

const MotionDiv = motion.div;
const MotionButton = motion.button;

const extractAuthErrorMessage = (responseData, statusCode) => {
    const detail = responseData?.detail;
    if (Array.isArray(detail)) {
        return detail.map(d => `${d.loc.join('.')}: ${d.msg}`).join(', ');
    }
    if (typeof detail === 'string' && detail.trim()) {
        return detail;
    }
    if (typeof responseData === 'string' && responseData.trim()) {
        return responseData;
    }
    if (responseData?.message) {
        return responseData.message;
    }
    if (responseData?.error) {
        return responseData.error;
    }
    return `Authentication failed (HTTP ${statusCode})`;
};

const Login = () => {
    const [username, setUsername] = useState('');
    const [password, setPassword] = useState('');
    const [role, setRole] = useState('STUDENT');
    
    // Additional fields for student registration
    const [name, setName] = useState('');
    const [rollNumber, setRollNumber] = useState('');
    const [course, setCourse] = useState('');

    const [error, setError] = useState('');
    const [isRegister, setIsRegister] = useState(false);
    const [showSettings, setShowSettings] = useState(false);
    const [apiUrl, setApiUrl] = useState(localStorage.getItem('api_url') || `http://${window.location.hostname}:8001`);
    const navigate = useNavigate();

    // Force update from old port 8000
    useEffect(() => {
        const current = localStorage.getItem('api_url');
        if (current && current.includes(':8000')) {
            localStorage.removeItem('api_url');
            window.location.reload();
        }
    }, []);

    const clearStorage = () => {
        localStorage.clear();
        window.location.reload();
    };

    const handleAuth = async (e) => {
        e.preventDefault();
        setError('');

        const endpoint = isRegister ? '/api/v1/auth/register' : '/api/v1/auth/login';

        try {
            if (isRegister) {
                const payload = { username, password, role };
                if (role === 'STUDENT') {
                    payload.name = name;
                    payload.roll_number = rollNumber;
                    payload.course = course;
                }
                await api.post(endpoint, payload);
                setIsRegister(false);
                alert('Registration successful! Please login.');
                // Clear extra fields
                setName('');
                setRollNumber('');
                setCourse('');
            } else {
                const params = new URLSearchParams({ username, password });
                const res = await api.post(endpoint, params, {
                    headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
                });
                const data = res.data;
                localStorage.setItem('token', data.access_token);
                localStorage.setItem('role', data.role);
                localStorage.setItem('username', username);
                localStorage.setItem('user_id', data.user_id);
                navigate('/');
            }
        } catch (err) {
            console.error('Auth Error:', err);
            if (err.response) {
                const responseData = err.response.data;
                setError(extractAuthErrorMessage(responseData, err.response.status));
            } else if (err.request) {
                setError(`Connection timed out to ${apiUrl}. Check if the backend is running correctly.`);
            } else {
                setError('Request error: ' + err.message);
            }
        }
    };

    const handleSetUrl = () => {
        saveApiUrl(apiUrl);
        setShowSettings(false);
    };

    return (
        <div className="min-h-screen bg-dark-900 text-slate-100 flex flex-col items-center justify-center p-4 relative overflow-hidden">
            {/* Background elements */}
            <div className="absolute top-[-10%] left-[-10%] w-96 h-96 bg-primary-600/20 rounded-full blur-3xl pointer-events-none"></div>
            <div className="absolute bottom-[-10%] right-[-10%] w-96 h-96 bg-purple-600/20 rounded-full blur-3xl pointer-events-none"></div>

            {/* Header Icons */}
            <div className="absolute top-6 right-6 flex gap-4 z-50">
                <button onClick={clearStorage} className="p-2 hover:bg-slate-800 rounded-full transition-colors text-slate-400 hover:text-white" title="Reset App State">
                    <RefreshCcw size={20} />
                </button>
                <button onClick={() => setShowSettings(!showSettings)} className={`p-2 rounded-full transition-colors ${showSettings ? 'bg-primary-600 text-white' : 'hover:bg-slate-800 text-slate-400 hover:text-white'}`} title="API Settings">
                    <Settings  size={20} />
                </button>
            </div>

            <AnimatePresence>
                {showSettings && (
                    <MotionDiv 
                        initial={{ opacity: 0, y: -20, scale: 0.95 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: -20, scale: 0.95 }}
                        className="absolute top-20 right-6 z-50 w-80 bg-slate-800/90 backdrop-blur-xl border border-slate-700/50 rounded-2xl p-5 shadow-2xl"
                    >
                        <h4 className="flex items-center gap-2 m-0 mb-3 font-semibold text-slate-200">
                            <Server size={18} className="text-primary-500" /> API Target Server
                        </h4>
                        <p className="text-xs text-slate-400 mb-3 truncate" title={apiUrl}>
                            Current: {apiUrl}
                        </p>
                        <input
                            type="text"
                            value={apiUrl}
                            onChange={(e) => setApiUrl(e.target.value)}
                            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 focus:outline-none focus:border-primary-500 mb-4 transition-colors"
                        />
                        <div className="flex gap-2">
                            <button onClick={handleSetUrl} className="flex-2 bg-primary-600 hover:bg-primary-500 text-white py-2 px-3 rounded-lg text-sm font-medium transition-colors">
                                Update URL
                            </button>
                            <button
                                onClick={async () => {
                                    try {
                                        const res = await api.get('/health');
                                        alert(`Connection Success! Version: ${res.data.version}`);
                                    } catch (e) {
                                        alert(`Connection Failed: ${e.message}`);
                                    }
                                }}
                                className="flex-1 bg-slate-700 hover:bg-slate-600 text-white py-2 px-3 rounded-lg text-sm transition-colors"
                            >
                                Test
                            </button>
                        </div>
                    </MotionDiv>
                )}
            </AnimatePresence>

            <MotionDiv 
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
                className="w-full max-w-md z-10"
            >
                <div className="bg-slate-800/40 backdrop-blur-xl border border-slate-700/50 p-8 rounded-3xl shadow-2xl">
                    <div className="text-center mb-8">
                        <MotionDiv 
                            initial={{ scale: 0 }}
                            animate={{ scale: 1 }}
                            transition={{ type: "spring", stiffness: 200, damping: 15, delay: 0.2 }}
                            className="inline-flex items-center justify-center p-4 bg-primary-500/10 rounded-2xl mb-4"
                        >
                            <ShieldCheck size={40} className="text-primary-500" />
                        </MotionDiv>
                        <h2 className="text-2xl font-bold text-white mb-2 tracking-tight">
                            {isRegister ? 'Create an Account' : 'Welcome Back'}
                        </h2>
                        <p className="text-slate-400 text-sm">
                            {isRegister ? 'Join the voice attendance system' : 'Secure voice-based attendance'}
                        </p>
                    </div>

                    <form onSubmit={handleAuth} className="space-y-4">
                        {isRegister && (
                            <MotionDiv 
                                initial={{ opacity: 0, height: 0 }}
                                animate={{ opacity: 1, height: 'auto' }}
                                className="flex gap-2 mb-2 p-1 bg-slate-900/50 rounded-xl"
                            >
                                <button
                                    type="button"
                                    onClick={() => setRole('STUDENT')}
                                    className={`flex-1 py-2 text-sm font-medium rounded-lg transition-all ${role === 'STUDENT' ? 'bg-primary-600 text-white shadow-md' : 'text-slate-400 hover:text-slate-200'}`}
                                >
                                    Student
                                </button>
                                <button
                                    type="button"
                                    onClick={() => setRole('TEACHER')}
                                    className={`flex-1 py-2 text-sm font-medium rounded-lg transition-all ${role === 'TEACHER' ? 'bg-primary-600 text-white shadow-md' : 'text-slate-400 hover:text-slate-200'}`}
                                >
                                    Teacher
                                </button>
                            </MotionDiv>
                        )}
                        
                        <div>
                            <input
                                type="text"
                                placeholder={isRegister && role === 'STUDENT' ? "Choose a Username" : "Username"}
                                value={username}
                                onChange={(e) => setUsername(e.target.value)}
                                required
                                className="w-full bg-slate-900/80 border border-slate-700 rounded-xl px-4 py-3 text-slate-100 placeholder-slate-500 focus:outline-none focus:border-primary-500 focus:ring-1 focus:ring-primary-500 transition-all shadow-inner"
                            />
                        </div>

                        {isRegister && role === 'STUDENT' && (
                            <MotionDiv 
                                initial={{ opacity: 0, x: -10 }}
                                animate={{ opacity: 1, x: 0 }}
                                className="space-y-4"
                            >
                                <input
                                    type="text"
                                    placeholder="Full Name"
                                    value={name}
                                    onChange={(e) => setName(e.target.value)}
                                    required
                                    className="w-full bg-slate-900/80 border border-slate-700 rounded-xl px-4 py-3 text-slate-100 placeholder-slate-500 focus:outline-none focus:border-primary-500 focus:ring-1 focus:ring-primary-500 transition-all"
                                />
                                <div className="flex gap-4">
                                    <input
                                        type="text"
                                        placeholder="Roll Number"
                                        value={rollNumber}
                                        onChange={(e) => setRollNumber(e.target.value)}
                                        required
                                        className="w-1/2 bg-slate-900/80 border border-slate-700 rounded-xl px-4 py-3 text-slate-100 placeholder-slate-500 focus:outline-none focus:border-primary-500 focus:ring-1 focus:ring-primary-500 transition-all"
                                    />
                                    <input
                                        type="text"
                                        placeholder="Course/Branch"
                                        value={course}
                                        onChange={(e) => setCourse(e.target.value)}
                                        required
                                        className="w-1/2 bg-slate-900/80 border border-slate-700 rounded-xl px-4 py-3 text-slate-100 placeholder-slate-500 focus:outline-none focus:border-primary-500 focus:ring-1 focus:ring-primary-500 transition-all"
                                    />
                                </div>
                            </MotionDiv>
                        )}

                        <div>
                            <input
                                type="password"
                                placeholder="Password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                required
                                className="w-full bg-slate-900/80 border border-slate-700 rounded-xl px-4 py-3 text-slate-100 placeholder-slate-500 focus:outline-none focus:border-primary-500 focus:ring-1 focus:ring-primary-500 transition-all shadow-inner"
                            />
                        </div>

                        <AnimatePresence>
                            {error && (
                                <MotionDiv 
                                    initial={{ opacity: 0, height: 0 }}
                                    animate={{ opacity: 1, height: 'auto' }}
                                    exit={{ opacity: 0, height: 0 }}
                                    className="overflow-hidden"
                                >
                                    <div className="bg-red-500/10 border border-red-500/20 text-red-400 text-sm p-3 rounded-lg mt-2">
                                        {error}
                                    </div>
                                </MotionDiv>
                            )}
                        </AnimatePresence>

                        <MotionButton 
                            whileHover={{ scale: 1.01 }}
                            whileTap={{ scale: 0.98 }}
                            type="submit" 
                            className="w-full bg-gradient-to-r from-primary-600 to-primary-500 hover:from-primary-500 hover:to-indigo-500 text-white font-semibold py-3.5 px-4 rounded-xl shadow-lg shadow-primary-500/30 flex items-center justify-center gap-2 mt-6 transition-all"
                        >
                            {isRegister ? (
                                <><UserPlus size={18} /> Register Now</>
                            ) : (
                                <><LogIn size={18} /> Sign In</>
                            )}
                        </MotionButton>
                    </form>

                    <div className="mt-8 text-center border-t border-slate-700/50 pt-6">
                        <p className="text-slate-400 text-sm">
                            {isRegister ? 'Already have an account?' : "Don't have an account?"}
                            <button
                                onClick={() => { setIsRegister(!isRegister); setError(''); }}
                                className="ml-2 font-medium text-primary-400 hover:text-primary-300 transition-colors bg-transparent border-none focus:outline-none"
                            >
                                {isRegister ? 'Login instead' : 'Register here'}
                            </button>
                        </p>
                    </div>
                </div>
            </MotionDiv>
        </div>
    );
};

export default Login;
