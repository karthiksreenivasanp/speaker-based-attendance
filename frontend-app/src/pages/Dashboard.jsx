import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import { MapPin, CheckCircle, Clock, User, LogIn, ChevronRight, FileDown, CheckCircle2, ShieldCheck, PlayCircle, Trash2, Edit } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

function Dashboard() {
    const [role, setRole] = useState(localStorage.getItem('role'));
    const [loading, setLoading] = useState(true);

    // Teacher State
    const [stats, setStats] = useState({ present: 0, total: 0 });
    const [recentLogs, setRecentLogs] = useState([]);
    const [classInfo, setClassInfo] = useState(null);
    const [settingLocation, setSettingLocation] = useState(false);
    const [overrideMode, setOverrideMode] = useState(null);

    // Student State
    const [userProfile, setUserProfile] = useState(null);
    const [mentors, setMentors] = useState([]);
    const [voiceStatus, setVoiceStatus] = useState(null);

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        setLoading(true);
        try {
            const profileRes = await api.get('/api/v1/students/me');

            if (role === 'TEACHER') {
                setUserProfile(profileRes.data);

                let activeClass = null;
                try {
                    const classRes = await api.get('/api/v1/admin/classes/active');
                    activeClass = classRes.data;
                    setClassInfo(activeClass);
                } catch (err) {
                    console.log("No active class found.");
                    setClassInfo(null);
                }

                const [statsRes, logsRes] = await Promise.all([
                    api.get('/api/v1/students/'),
                    api.get(`/api/v1/admin/attendance?limit=50${activeClass ? `&class_id=${activeClass.id}` : ''}`)
                ]);

                setStats({
                    total: statsRes.data.length,
                    present: logsRes.data.filter(l => l.status === 'PRESENT').length
                });
                setRecentLogs(logsRes.data);
            } else {
                const [studentProf, mentorsRes, myLogs, voiceRes] = await Promise.all([
                    api.get('/api/v1/students/profile'),
                    api.get('/api/v1/students/mentors'),
                    api.get('/api/v1/admin/attendance?limit=10'),
                    api.get('/api/v1/students/voice')
                ]);
                setUserProfile({ ...profileRes.data, ...studentProf.data });
                setMentors(mentorsRes.data);
                setRecentLogs(myLogs.data);
                setVoiceStatus(voiceRes.data);
            }
        } catch (e) {
            console.error("Dashboard Load Error", e);
        } finally {
            setLoading(false);
        }
    };

    /** Teacher Actions **/
    const setLocation = async () => {
        setSettingLocation(true);
        navigator.geolocation.getCurrentPosition(async (pos) => {
            try {
                await api.post('/api/v1/admin/classes/start', {
                    latitude: pos.coords.latitude,
                    longitude: pos.coords.longitude,
                    radius: 20.0
                });
                alert("Location Fixed! Session Started.");
                loadData();
            } catch (e) {
                alert("Failed to start class session.");
            } finally {
                setSettingLocation(false);
            }
        }, () => {
            alert("Geolocation permission denied.");
            setSettingLocation(false);
        });
    };

    const approveAttendance = async () => {
        if (!classInfo) return alert("No active class");
        try {
            await api.post(`/api/v1/admin/attendance/approve?class_id=${classInfo.id}`);
            alert("Attendance Approved!");
            loadData();
        } catch (e) {
            alert("Failed to approve");
        }
    };

    const exportCsv = async () => {
        if (!classInfo) return alert("No active class");
        try {
            const response = await api.get(`/api/v1/admin/attendance/export?class_id=${classInfo.id}`, {
                responseType: 'blob'
            });
            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', `attendance_${new Date().toISOString().split('T')[0]}.csv`);
            document.body.appendChild(link);
            link.click();
        } catch (e) {
            alert("Export failed. Make sure the sheet is approved.");
        }
    };

    const updateStatus = async (id, status) => {
        try {
            await api.patch(`/api/v1/admin/attendance/${id}?status=${status}`);
            setOverrideMode(null);
            loadData();
        } catch (e) {
            alert("Failed to update status");
        }
    };

    /** Student Actions **/
    const selectMentor = async (id) => {
        try {
            await api.post(`/api/v1/students/select-mentor/${id}`);
            alert("Mentor Selected!");
            loadData();
        } catch (e) {
            alert(e.response?.data?.detail || "Failed to select mentor");
        }
    };

    const deleteVoice = async () => {
        if (!window.confirm("Are you sure you want to delete your voice template? You will need to re-enroll.")) return;
        try {
            await api.delete('/api/v1/students/voice');
            alert("Voice template deleted!");
            loadData();
        } catch (e) {
            alert("Failed to delete template");
        }
    };

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-[70vh] text-primary-400">
                <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary-500"></div>
            </div>
        );
    }

    const TeacherView = () => (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="max-w-4xl mx-auto p-4 space-y-6">
            <header className="mb-8">
                <h1 className="text-3xl font-bold text-white mb-2">Teacher Dashboard</h1>
                <p className="text-slate-400">Welcome back, Prof. {userProfile?.username}</p>
            </header>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-slate-800/50 backdrop-blur-md border border-slate-700/50 p-6 rounded-2xl flex flex-col items-center justify-center">
                    <h2 className="text-4xl font-bold text-emerald-400 mb-1">{stats.present}</h2>
                    <span className="text-xs font-semibold text-slate-400 tracking-wider">PRESENT TODAY</span>
                </div>
                <div className="bg-slate-800/50 backdrop-blur-md border border-slate-700/50 p-6 rounded-2xl flex flex-col items-center justify-center">
                    <h2 className="text-4xl font-bold text-primary-400 mb-1">{stats.total}</h2>
                    <span className="text-xs font-semibold text-slate-400 tracking-wider">TOTAL STUDENTS</span>
                </div>
            </div>

            <div className="bg-slate-800/50 backdrop-blur-md border border-primary-500/20 p-6 rounded-2xl shadow-lg shadow-primary-500/5 relative overflow-hidden">
                <div className="absolute top-0 right-0 p-12 opacity-5 pointer-events-none">
                    <MapPin size={100} />
                </div>
                <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 relative z-10">
                    <div>
                        <h3 className="text-xl font-bold text-slate-100 flex items-center gap-2 mb-1">
                            <MapPin className="text-primary-400" size={20} /> Class Session
                        </h3>
                        <p className="text-sm text-slate-400">
                            {classInfo?.session_start ?
                                <span className="text-emerald-400 flex items-center gap-1"><CheckCircle2 size={14} /> Active since {new Date(classInfo.session_start).toLocaleTimeString()}</span> :
                                "No active session currently."}
                        </p>
                    </div>
                    <button
                        onClick={setLocation}
                        disabled={settingLocation}
                        className="bg-primary-600 hover:bg-primary-500 disabled:opacity-50 text-white px-6 py-3 rounded-xl font-medium transition-all shadow-md shadow-primary-500/20 whitespace-nowrap"
                    >
                        {settingLocation ? "📡 Locking GPS..." : (classInfo ? "Restart Session" : "Start New Class")}
                    </button>
                </div>
            </div>

            {classInfo && (
                <div className="flex grid-cols-2 gap-4">
                    <button onClick={approveAttendance} className="flex-1 bg-slate-700 hover:bg-slate-600 text-white py-3 rounded-xl font-medium transition-colors flex items-center justify-center gap-2">
                        <CheckCircle2 size={18} /> Approve
                    </button>
                    <button onClick={exportCsv} className="flex-1 border border-primary-500/50 hover:bg-primary-500/10 text-primary-300 py-3 rounded-xl font-medium transition-colors flex items-center justify-center gap-2">
                        <FileDown size={18} /> Export CSV
                    </button>
                </div>
            )}

            <div className="mt-8">
                <h3 className="text-lg font-bold text-slate-200 mb-4 px-1">Live Attendance Feed</h3>
                <div className="bg-slate-800/30 backdrop-blur-sm border border-slate-700/50 rounded-2xl overflow-hidden shadow-xl">
                    {recentLogs.length === 0 ? (
                        <div className="p-8 text-center text-slate-500">No attendance records yet for this class.</div>
                    ) : (
                        <div className="divide-y divide-slate-700/50">
                            {recentLogs.map((log) => (
                                <div key={log.id} className="p-4 md:p-5 hover:bg-slate-700/20 transition-colors flex items-center justify-between">
                                    <div className="flex-1">
                                        <div className="font-semibold text-slate-200">Student ID: {log.student_id}</div>
                                        <div className="text-xs text-slate-500 flex items-center gap-1 mt-1">
                                            <Clock size={12} /> {new Date(log.timestamp).toLocaleTimeString()}
                                        </div>
                                    </div>

                                    <div className="flex items-center gap-4">
                                        <div className="text-right">
                                            {overrideMode === log.id ? (
                                                <div className="flex flex-col gap-1">
                                                    <button onClick={() => updateStatus(log.id, 'PRESENT')} className="text-xs bg-emerald-500/20 text-emerald-400 px-2 py-1 rounded">Set Present</button>
                                                    <button onClick={() => updateStatus(log.id, 'ABSENT')} className="text-xs bg-red-500/20 text-red-400 px-2 py-1 rounded">Set Absent</button>
                                                    <button onClick={() => setOverrideMode(null)} className="text-xs text-slate-400">Cancel</button>
                                                </div>
                                            ) : (
                                                <>
                                                    <div className={`font-bold text-sm ${log.status === 'LATECOMER' || log.status.includes('LATE') ? 'text-amber-400' :
                                                            (log.status === 'PRESENT' ? 'text-emerald-400' : 'text-red-400')
                                                        }`}>
                                                        {log.status}
                                                    </div>
                                                    <div className="text-[10px] text-slate-500">{Math.round(log.verification_score * 100)}% Match</div>
                                                </>
                                            )}
                                        </div>
                                        {!overrideMode && (
                                            <button onClick={() => setOverrideMode(log.id)} className="p-2 text-slate-500 hover:text-primary-400 bg-slate-800 rounded-lg">
                                                <Edit size={16} />
                                            </button>
                                        )}
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </motion.div>
    );

    const StudentView = () => (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="max-w-md mx-auto p-4 space-y-6">
            <header className="mb-6 flex justify-between items-center">
                <div>
                    <h1 className="text-2xl font-bold text-white">Student Hub</h1>
                    <p className="text-slate-400 text-sm">Hello, {userProfile?.name?.split(' ')[0] || userProfile?.username}</p>
                </div>
                <div className="w-12 h-12 bg-primary-600/20 rounded-full flex items-center justify-center text-primary-400 border border-primary-500/30">
                    <User size={24} />
                </div>
            </header>

            {/* Profile Summary Card */}
            <div className="bg-gradient-to-br from-slate-800 to-slate-900 border border-slate-700/50 p-5 rounded-2xl shadow-lg relative overflow-hidden">
                <div className="relative z-10 grid grid-cols-2 gap-4">
                    <div>
                        <p className="text-xs text-slate-500 uppercase font-semibold">Roll No</p>
                        <p className="text-white font-medium">{userProfile?.roll_number}</p>
                    </div>
                    <div>
                        <p className="text-xs text-slate-500 uppercase font-semibold">Course</p>
                        <p className="text-white font-medium truncate">{userProfile?.course}</p>
                    </div>
                    <div className="col-span-2 mt-2">
                        <p className="text-xs text-slate-500 uppercase font-semibold">Mentor</p>
                        <p className="text-white font-medium flex items-center gap-2">
                            {userProfile?.mentor_id ? `Teacher ID ${userProfile.mentor_id}` : <span className="text-amber-400 text-sm">Not Selected</span>}
                        </p>
                    </div>
                </div>
            </div>

            {!userProfile?.mentor_id && (
                <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="bg-amber-900/20 border border-amber-500/30 p-5 rounded-2xl">
                    <h3 className="text-amber-400 font-bold mb-2 flex items-center gap-2"><ShieldCheck size={18} /> Select Your Mentor</h3>
                    <p className="text-sm text-amber-200/70 mb-4">You must select an available mentor to attend their classes.</p>
                    <div className="space-y-2 max-h-48 overflow-y-auto pr-2 custom-scrollbar">
                        {mentors.map(m => (
                            <button
                                key={m.id}
                                onClick={() => selectMentor(m.id)}
                                className="w-full bg-slate-800/80 hover:bg-slate-700 border border-slate-700 p-3 rounded-xl flex items-center justify-between transition-colors focus:ring-2 ring-primary-500"
                            >
                                <span className="text-slate-200 text-sm font-medium">{m.username}</span>
                                <ChevronRight size={16} className="text-slate-500" />
                            </button>
                        ))}
                    </div>
                </motion.div>
            )}

            {userProfile?.mentor_id && (
                <div className="space-y-4">
                    {/* Voice Status Card */}
                    <div className="bg-slate-800/40 border border-slate-700/50 p-5 rounded-2xl shadow-md">
                        <div className="flex justify-between items-start mb-4">
                            <div>
                                <h3 className="font-bold text-slate-200 flex items-center gap-2">
                                    Voice Signature
                                    {voiceStatus?.enrolled ? <CheckCircle2 size={16} className="text-emerald-400" /> : null}
                                </h3>
                                <p className="text-xs text-slate-500 mt-1">
                                    {voiceStatus?.enrolled ? `Enrolled ${new Date(voiceStatus.enrollment_date).toLocaleDateString()}` : "No voice signature found."}
                                </p>
                            </div>
                        </div>

                        {voiceStatus?.enrolled ? (
                            <div className="flex gap-2">
                                <Link to="/enroll" className="flex-1 text-center bg-slate-700/50 hover:bg-slate-700 text-slate-300 py-2.5 rounded-lg text-sm font-medium transition-colors">
                                    Hear Playback or Update
                                </Link>
                                <button onClick={deleteVoice} className="bg-red-500/20 text-red-400 hover:bg-red-500/30 p-2.5 rounded-lg transition-colors">
                                    <Trash2 size={18} />
                                </button>
                            </div>
                        ) : (
                            <Link to="/enroll" className="block w-full text-center bg-primary-600 hover:bg-primary-500 text-white py-3 rounded-xl font-medium transition-colors shadow-md shadow-primary-500/20">
                                Enroll Voice Profile Now
                            </Link>
                        )}
                    </div>

                    {/* Quick Access */}
                    {voiceStatus?.enrolled && (
                        <Link to="/verify" className="flex flex-col items-center justify-center p-8 bg-gradient-to-br from-indigo-500/20 to-purple-500/20 border border-indigo-500/30 rounded-3xl group shadow-lg shadow-indigo-500/10 hover:shadow-indigo-500/20 transition-all duration-300 relative overflow-hidden">
                            <div className="absolute inset-0 bg-indigo-500/10 opacity-0 group-hover:opacity-100 transition-opacity"></div>
                            <div className="bg-indigo-500/20 p-4 rounded-full mb-4 group-hover:scale-110 transition-transform duration-300">
                                <Mic size={32} className="text-indigo-400" />
                            </div>
                            <h2 className="text-xl font-bold text-white">Mark Attendance</h2>
                            <p className="text-sm text-indigo-200 mt-2">Requires Location & Microphone</p>
                        </Link>
                    )}
                </div>
            )}

            {/* Application History */}
            <div className="mt-8">
                <h3 className="text-lg font-bold text-slate-200 mb-4 px-1 flex items-center justify-between">
                    Attendance History
                    <span className="text-xs font-normal text-slate-500 bg-slate-800 px-2 py-1 rounded-full">{recentLogs.length} Recent</span>
                </h3>
                <div className="bg-slate-800/30 backdrop-blur-sm border border-slate-700/50 rounded-2xl overflow-hidden">
                    {recentLogs.length === 0 ? (
                        <div className="p-6 text-center text-slate-500 text-sm">No attendance records yet.</div>
                    ) : (
                        <div className="divide-y divide-slate-700/50">
                            {recentLogs.map((log) => (
                                <div key={log.id} className="p-4 flex items-center justify-between hover:bg-slate-700/20 transition-colors">
                                    <div>
                                        <div className="text-sm font-semibold text-slate-300">Class {log.class_id}</div>
                                        <div className="text-xs text-slate-500 flex items-center gap-1 mt-1">
                                            <Clock size={12} /> {new Date(log.timestamp).toLocaleDateString()} {new Date(log.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                        </div>
                                    </div>
                                    <div className={`px-2.5 py-1 rounded-full text-xs font-bold border ${log.status === 'LATECOMER' || log.status.includes('LATE') ? 'text-amber-400 border-amber-500/30 bg-amber-500/10' :
                                            (log.status === 'PRESENT' ? 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10' : 'text-red-400 border-red-500/30 bg-red-500/10')
                                        }`}>
                                        {log.status}
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>

            <div className="h-10"></div> {/* Bottom padding for mobile navbar */}
        </motion.div>
    );

    return role === 'TEACHER' ? <TeacherView /> : <StudentView />;
}

export default Dashboard;
