import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';
import { Mic, Square, User, Upload, AlertCircle, MapPin, Target, LocateFixed, Verified, XCircle, Loader2, ArrowLeft } from 'lucide-react';
import { WavRecorder } from '../utils/WavRecorder';
import { motion, AnimatePresence } from 'framer-motion';

function Verify() {
    const [recording, setRecording] = useState(false);
    const [result, setResult] = useState(null);
    const [loading, setLoading] = useState(false);
    const [location, setLocation] = useState(null);
    const [gpsStatus, setGpsStatus] = useState('idle');
    const [hasMentor, setHasMentor] = useState(true);
    const [isSecure, setIsSecure] = useState(true);
    const navigate = useNavigate();

    const recorderRef = useRef(null);
    const locationRef = useRef(null);
    const gpsStatusRef = useRef('idle');
    const watchIdRef = useRef(null);

    useEffect(() => {
        checkProfile();
        setIsSecure(window.isSecureContext);
        startGpsWatch();
        return () => {
            if (watchIdRef.current !== null) {
                navigator.geolocation.clearWatch(watchIdRef.current);
            }
        };
    }, []);

    const checkProfile = async () => {
        try {
            const res = await api.get('/api/v1/students/profile');
            if (!res.data.mentor_id) {
                setHasMentor(false);
            }
        } catch (e) {
            console.error("Profile check failed");
        }
    };

    const startGpsWatch = () => {
        if ("geolocation" in navigator) {
            setGpsStatus('acquiring');
            gpsStatusRef.current = 'acquiring';

            watchIdRef.current = navigator.geolocation.watchPosition(
                (pos) => {
                    const coords = { lat: pos.coords.latitude, lon: pos.coords.longitude };
                    setLocation(coords);
                    locationRef.current = coords;
                    setGpsStatus('ready');
                    gpsStatusRef.current = 'ready';
                },
                (err) => {
                    console.error("GPS Error:", err);
                    setGpsStatus('error');
                    gpsStatusRef.current = 'error';
                },
                { enableHighAccuracy: true, maximumAge: 10000, timeout: 20000 }
            );
        } else {
            setGpsStatus('error');
        }
    };

    const startRecording = async () => {
        if (gpsStatus !== 'ready') return;
        setResult(null);
        try {
            recorderRef.current = new WavRecorder(16000);
            await recorderRef.current.start();
            setRecording(true);
        } catch (e) {
            alert('Error: ' + e.message);
        }
    };

    const stopRecording = async () => {
        if (recorderRef.current && recording) {
            const wavBlob = await recorderRef.current.stop();
            setRecording(false);
            verifyVoice(wavBlob);
        }
    };

    const verifyVoice = async (blob) => {
        setLoading(true);
        const formData = new FormData();
        formData.append('file', blob, 'verify.wav');

        const currentLoc = locationRef.current;
        if (currentLoc) {
            formData.append('latitude', currentLoc.lat);
            formData.append('longitude', currentLoc.lon);
        }

        try {
            const res = await api.post('/api/v1/verify/identify', formData);
            setResult(res.data);
        } catch (e) {
            setResult({ error: e.response?.data?.detail || "Connection Failed" });
        } finally {
            setLoading(false);
        }
    };

    if (!hasMentor) {
        return (
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="max-w-md mx-auto p-4 text-center mt-10">
                <div className="bg-slate-800/50 backdrop-blur-md border border-amber-500/30 p-8 rounded-3xl shadow-lg">
                    <AlertCircle size={64} className="text-amber-500 mx-auto mb-6" />
                    <h2 className="text-2xl font-bold text-white mb-2">Mentor Required</h2>
                    <p className="text-slate-400 mb-8">You must select an available mentor directly from your dashboard before you can mark attendance.</p>
                    <button onClick={() => navigate('/')} className="inline-block bg-primary-600 hover:bg-primary-500 text-white font-semibold py-3 px-8 rounded-xl transition-colors shadow-lg shadow-primary-500/20">
                        Go to Dashboard
                    </button>
                </div>
            </motion.div>
        );
    }

    return (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="max-w-md mx-auto p-4 space-y-6">
            <header className="mb-6 flex items-center justify-between">
                <div>
                    <h1 className="text-2xl font-bold text-white flex items-center gap-2">
                        <Target className="text-primary-400" /> Verify
                    </h1>
                    <p className="text-slate-400 text-sm mt-1">Mark your secure voice attendance.</p>
                </div>
            </header>

            <div className="bg-slate-800/40 border border-slate-700/50 p-8 rounded-3xl text-center shadow-lg relative min-h-[450px] flex flex-col justify-center">

                <AnimatePresence mode="wait">
                    {loading ? (
                        <motion.div key="loading" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="flex flex-col items-center">
                            <div className="relative">
                                <div className="absolute inset-0 bg-primary-500/30 rounded-full animate-ping scale-150"></div>
                                <div className="bg-primary-500/20 p-4 rounded-full relative z-10">
                                    <Loader2 size={48} className="text-primary-400 animate-spin" />
                                </div>
                            </div>
                            <h3 className="text-xl font-bold text-white mt-6 mb-2">Analyzing Voice Print</h3>
                            <p className="text-slate-400 text-sm">Matching against your enrolled signature...</p>
                        </motion.div>
                    ) : result ? (() => {
                        const isSuccess = (result.identified || result.verified) && !result.error;
                        const displayStatus = result.status || (result.message?.includes('PRESENT') ? 'PRESENT' : result.message?.includes('LATE') ? 'LATECOMER' : 'VERIFIED');
                        const isLate = displayStatus === 'LATECOMER' || (displayStatus && displayStatus.includes('LATE'));
                        return (
                        <motion.div key="result" initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} className="flex flex-col items-center">
                            {isSuccess ? (
                                <>
                                    <div className={`w-24 h-24 rounded-full flex items-center justify-center mb-6 shadow-xl ${isLate ? 'bg-amber-500 shadow-amber-500/30' : 'bg-emerald-500 shadow-emerald-500/30'}`}>
                                        <Verified size={48} className="text-white" />
                                    </div>
                                    <h2 className="text-2xl font-bold text-white mb-2">Attendance Logged</h2>
                                    <div className={`text-xl font-black mb-4 px-4 py-1.5 rounded-lg border ${isLate ? 'text-amber-400 border-amber-500/30 bg-amber-500/10' : 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10'}`}>
                                        Status: {displayStatus}
                                    </div>
                                    <div className="text-sm font-medium text-slate-400 bg-slate-900/50 px-3 py-1.5 rounded-full border border-slate-700/50">
                                        Voice Match: <span className="text-white">{(result.score * 100).toFixed(0)}%</span>
                                    </div>
                                </>
                            ) : (
                                <>
                                    <div className="w-24 h-24 rounded-full bg-red-500/20 flex items-center justify-center mb-6 border-4 border-red-500/30">
                                        <XCircle size={48} className="text-red-500" />
                                    </div>
                                    <h2 className="text-2xl font-bold text-red-400 mb-2">Verification Failed</h2>
                                    <div className="bg-red-500/10 border border-red-500/30 text-red-300 p-4 rounded-xl mb-4 text-sm w-full">
                                        <strong className="block mb-1">Reason:</strong>
                                        {result.error || result.message}
                                    </div>
                                    <p className="text-sm text-slate-400 mb-6 px-4">
                                        Ensure you are within the classroom geofence and speaking clearly in a quiet environment.
                                    </p>
                                </>
                            )}

                            <button
                                onClick={() => setResult(null)}
                                className="mt-8 bg-slate-700 hover:bg-slate-600 text-white font-semibold py-3 px-8 rounded-xl transition-colors flex items-center gap-2"
                            >
                                <ArrowLeft size={18} /> Retry Sign-in
                            </button>
                        </motion.div>
                        );
                    })() : (
                        <motion.div key="record" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="flex flex-col h-full justify-between items-center py-4">

                            {/* GPS Status Dashboard Item */}
                            <div className={`w-full flex items-center justify-between p-3 rounded-xl border mb-10 transition-colors ${gpsStatus === 'ready' ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-400' :
                                    gpsStatus === 'acquiring' ? 'bg-amber-500/10 border-amber-500/30 text-amber-400' :
                                        'bg-red-500/10 border-red-500/30 text-red-400'
                                }`}>
                                <div className="flex items-center gap-2 font-medium text-sm">
                                    {gpsStatus === 'ready' ? <LocateFixed size={18} /> :
                                        gpsStatus === 'acquiring' ? <Loader2 size={18} className="animate-spin" /> :
                                            <AlertCircle size={18} />}

                                    {gpsStatus === 'ready' ? "GPS Locked & Secured" :
                                        gpsStatus === 'acquiring' ? "Acquiring GPS Signal..." :
                                            "GPS Error / Denied"}
                                </div>
                                {gpsStatus !== 'ready' && (
                                    <button
                                        onClick={() => {
                                            if (watchIdRef.current) navigator.geolocation.clearWatch(watchIdRef.current);
                                            startGpsWatch();
                                        }}
                                        className="text-xs bg-slate-800/50 hover:bg-slate-700 px-3 py-1.5 rounded-lg border border-slate-600 transition-colors text-slate-200"
                                    >
                                        Refresh
                                    </button>
                                )}
                            </div>

                            {/* Security Warning */}
                            {!isSecure && (
                                <div className="bg-red-500/10 border border-red-500/30 text-red-400 p-4 rounded-xl text-sm flex items-start gap-3 w-full mb-8 text-left">
                                    <AlertCircle className="shrink-0 mt-0.5" size={18} />
                                    <p><strong>Non-Secure Context:</strong> Microphone access blocked. Use the <strong>HTTPS</strong> interface.</p>
                                </div>
                            )}

                            <div className="flex-1 flex flex-col items-center justify-center">
                                <div className="text-center mb-8">
                                    <p className="text-lg text-slate-300">Speak your passphrase:</p>
                                    <p className="text-xl md:text-2xl font-bold text-primary-400 mt-2">"My voice is my password"</p>
                                </div>

                                <div className="relative flex justify-center mb-6">
                                    {recording && (
                                        <>
                                            <div className="absolute inset-0 bg-indigo-500/20 rounded-full animate-ping delay-75 scale-150"></div>
                                            <div className="absolute inset-0 bg-indigo-500/20 rounded-full animate-ping delay-300 scale-[2]"></div>
                                        </>
                                    )}
                                    <button
                                        onClick={recording ? stopRecording : startRecording}
                                        disabled={gpsStatus !== 'ready'}
                                        className={`relative z-10 w-28 h-28 rounded-full flex items-center justify-center transition-all duration-300 ${gpsStatus !== 'ready'
                                                ? 'bg-slate-800 border-slate-700 cursor-not-allowed opacity-50'
                                                : recording
                                                    ? 'bg-slate-900 border-4 border-indigo-500 shadow-[0_0_40px_rgba(99,102,241,0.5)] scale-110'
                                                    : 'bg-gradient-to-br from-indigo-500 to-indigo-600 shadow-[0_10px_25px_rgba(99,102,241,0.4)] hover:scale-105 hover:shadow-[0_15px_35px_rgba(99,102,241,0.6)]'
                                            }`}
                                    >
                                        {recording ? <Square size={36} className="text-indigo-400 fill-indigo-400" /> : <Mic size={44} className="text-white" />}
                                    </button>
                                </div>
                                <p className={`text-sm font-medium transition-colors ${recording ? 'text-indigo-400 animate-pulse' : 'text-slate-400'}`}>
                                    {recording ? "Recording... Tap to finalize" :
                                        gpsStatus === 'ready' ? "Tap Mic to Start Logging" : "Awaiting GPS coordinates..."}
                                </p>
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>
            </div>
        </motion.div>
    );
}

export default Verify;
