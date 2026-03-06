import React, { useState, useRef, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import { Mic, Check, Square, Upload, User, AlertCircle, PlayCircle, Loader2 } from 'lucide-react';
import { WavRecorder } from '../utils/WavRecorder';
import { motion, AnimatePresence } from 'framer-motion';

function Enroll() {
    const [step, setStep] = useState(0); // 0: Profile check, 1-3: Record Samples
    const [studentData, setStudentData] = useState(null);
    const [recording, setRecording] = useState(false);
    const [blobs, setBlobs] = useState([]);
    const [status, setStatus] = useState('');
    const [loading, setLoading] = useState(true);
    const [isSecure, setIsSecure] = useState(true);

    const recorderRef = useRef(null);

    useEffect(() => {
        fetchProfile();
        setIsSecure(window.isSecureContext);
    }, []);

    const fetchProfile = async () => {
        try {
            const res = await api.get('/api/v1/students/profile');
            setStudentData(res.data);
            if (!res.data.mentor_id) {
                setStatus('no_mentor');
            } else {
                setStep(1);
            }
        } catch (e) {
            setStatus('Error fetching profile');
        } finally {
            setLoading(false);
        }
    };

    const startRecording = async () => {
        try {
            recorderRef.current = new WavRecorder(16000);
            await recorderRef.current.start();
            setRecording(true);
        } catch (e) {
            setStatus('Error accessing mic: ' + e.message);
        }
    };

    const stopRecording = async () => {
        if (recorderRef.current && recording) {
            const wavBlob = await recorderRef.current.stop();
            setRecording(false);

            const newBlobs = [...blobs, wavBlob];
            setBlobs(newBlobs);

            if (newBlobs.length < 3) {
                setStep(step + 1);
            } else {
                submitEnrollment(newBlobs);
            }
        }
    };

    const submitEnrollment = async (finalFiles) => {
        setStatus('Uploading...');
        const formData = new FormData();
        formData.append('name', studentData?.name || 'Student');
        finalFiles.forEach((file, idx) => {
            const filename = `sample_${idx + 1}.wav`;
            formData.append('files', file, filename);
        });

        try {
            await api.post(`/api/v1/enroll/${studentData.id}`, formData);
            setStatus('success');
            setStep(4);
        } catch (e) {
            setStatus('Error: ' + (e.response?.data?.detail || e.message));
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-[70vh] text-primary-400">
                <Loader2 size={48} className="animate-spin" />
            </div>
        );
    }

    if (status === 'no_mentor') {
        return (
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="max-w-md mx-auto p-4 text-center mt-10">
                <div className="bg-slate-800/50 backdrop-blur-md border border-amber-500/30 p-8 rounded-3xl shadow-lg">
                    <AlertCircle size={64} className="text-amber-500 mx-auto mb-6" />
                    <h2 className="text-2xl font-bold text-white mb-2">Mentor Required</h2>
                    <p className="text-slate-400 mb-8">Please select an available mentor directly from your dashboard before you can proceed with voice enrollment.</p>
                    <Link to="/" className="inline-block bg-primary-600 hover:bg-primary-500 text-white font-semibold py-3 px-8 rounded-xl transition-colors shadow-lg shadow-primary-500/20">
                        Return to Dashboard
                    </Link>
                </div>
            </motion.div>
        );
    }

    return (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="max-w-md mx-auto p-4 space-y-6">
            <header className="mb-6">
                <h1 className="text-2xl font-bold text-white flex items-center gap-2">
                    <Mic className="text-primary-400" /> Voice Signature
                </h1>
                <p className="text-slate-400 text-sm mt-1">Enroll your voice to authenticate.</p>
            </header>

            <AnimatePresence mode="wait">
                {status === 'success' ? (
                    <motion.div
                        key="success"
                        initial={{ opacity: 0, scale: 0.9 }}
                        animate={{ opacity: 1, scale: 1 }}
                        className="bg-emerald-500/10 border border-emerald-500/20 p-8 rounded-3xl text-center shadow-lg"
                    >
                        <div className="w-20 h-20 bg-emerald-500 rounded-full flex items-center justify-center mx-auto mb-6 shadow-lg shadow-emerald-500/30">
                            <Check size={40} className="text-white" />
                        </div>
                        <h2 className="text-2xl font-bold text-emerald-400 mb-2">Enrollment Complete!</h2>
                        <p className="text-emerald-100/70 mb-8">Your unique voice signature has been securely saved.</p>
                        <button
                            onClick={() => (window.location.href = '/')}
                            className="bg-slate-800 hover:bg-slate-700 text-white font-semibold py-3 px-8 rounded-xl transition-colors"
                        >
                            Return Home
                        </button>
                    </motion.div>
                ) : (
                    <motion.div key="enroll" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
                        {/* Profile Badge */}
                        <div className="bg-slate-800/40 border border-slate-700/50 p-4 rounded-2xl flex items-center gap-4">
                            <div className="w-12 h-12 bg-indigo-500/20 rounded-full flex items-center justify-center border border-indigo-500/30">
                                <User className="text-indigo-400" />
                            </div>
                            <div>
                                <div className="text-xs text-slate-500 font-semibold uppercase tracking-wider">Enrolling Identity</div>
                                <div className="text-slate-200 font-bold">{studentData?.name}</div>
                            </div>
                        </div>

                        {/* Security Warning */}
                        {!isSecure && (
                            <div className="bg-red-500/10 border border-red-500/30 text-red-400 p-4 rounded-xl text-sm flex items-start gap-3">
                                <AlertCircle className="shrink-0 mt-0.5" size={18} />
                                <p><strong>Non-Secure Context:</strong> Browsers block microphone access unless accessed via HTTPS or Localhost.</p>
                            </div>
                        )}

                        <div className="bg-slate-800/40 border border-slate-700/50 p-8 rounded-3xl text-center shadow-lg min-h-[300px] flex flex-col justify-center">
                            <div className="mb-8">
                                <div className="text-xs font-bold text-slate-500 uppercase tracking-widest mb-2">Capture {step} of 3</div>
                                <p className="text-xl text-slate-300">Read the phrase below:</p>
                                <p className="text-2xl font-bold text-primary-400 mt-2">
                                    "{step === 1 ? 'My voice is my password' : step === 2 ? 'Present' : `Roll No ${studentData?.roll_number} Present`}"
                                </p>
                            </div>

                            <div className="relative flex justify-center mb-6">
                                {recording && (
                                    <>
                                        <div className="absolute inset-0 bg-red-500/20 rounded-full animate-ping delay-75 scale-150"></div>
                                        <div className="absolute inset-0 bg-red-500/20 rounded-full animate-ping delay-300 scale-[2]"></div>
                                    </>
                                )}
                                <button
                                    onClick={recording ? stopRecording : startRecording}
                                    className={`relative z-10 w-24 h-24 rounded-full flex items-center justify-center transition-all duration-300 ${recording
                                        ? 'bg-slate-900 border-4 border-red-500 shadow-[0_0_30px_rgba(239,68,68,0.5)] scale-110'
                                        : 'bg-gradient-to-br from-red-500 to-red-600 shadow-[0_10px_20px_rgba(239,68,68,0.4)] hover:scale-105 hover:shadow-[0_10px_30px_rgba(239,68,68,0.6)]'
                                        }`}
                                >
                                    {recording ? <Square size={32} className="text-red-500 fill-red-500" /> : <Mic size={36} className="text-white" />}
                                </button>
                            </div>
                            <p className={`text-sm font-medium transition-colors ${recording ? 'text-red-400 animate-pulse' : 'text-slate-400'}`}>
                                {recording ? "Recording... Tap to Stop" : "Tap Microphone to Speak"}
                            </p>
                        </div>
                    </motion.div>
                )}
            </AnimatePresence>

            {status && status !== 'success' && status !== 'Uploading...' && (
                <div className="bg-red-500/10 border border-red-500/20 text-red-400 p-4 rounded-xl text-sm flex gap-2">
                    <AlertCircle size={18} className="shrink-0" /> {status}
                </div>
            )}
            {status === 'Uploading...' && (
                <div className="bg-primary-500/10 border border-primary-500/20 text-primary-400 p-4 rounded-xl text-sm flex items-center justify-center gap-2">
                    <Loader2 size={18} className="animate-spin" /> Uploading voice templates...
                </div>
            )}
        </motion.div>
    );
}

export default Enroll;
