import React, { useState, useEffect } from 'react';
import { api } from '../api';
import { ArrowLeft, Download, CheckCircle, Edit, Save, X, Loader2, ClipboardList } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';

function Logs() {
    const [logs, setLogs] = useState([]);
    const [loading, setLoading] = useState(true);
    const [editingId, setEditingId] = useState(null);
    const [newStatus, setNewStatus] = useState('');
    const role = localStorage.getItem('role');
    const navigate = useNavigate();

    useEffect(() => {
        if (role !== 'TEACHER') {
            navigate('/');
            return;
        }
        fetchLogs();
    }, []);

    const fetchLogs = async () => {
        try {
            const [studentsRes, logsRes] = await Promise.all([
                api.get('/api/v1/students/'),
                api.get('/api/v1/admin/attendance')
            ]);

            const studentsMap = {};
            studentsRes.data.forEach(s => studentsMap[s.id] = s.name);

            const enrichedLogs = logsRes.data.map(log => ({
                ...log,
                student_name: studentsMap[log.student_id] || 'Unknown'
            })).sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

            setLogs(enrichedLogs);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    const handleStatusUpdate = async (id) => {
        try {
            await api.patch(`/api/v1/admin/attendance/${id}?status=${newStatus}`);
            setEditingId(null);
            fetchLogs();
        } catch (e) {
            alert("Error updating status: " + (e.response?.data?.detail || "Only mentors can change status"));
        }
    };

    const handleApproveAll = async () => {
        try {
            await api.post('/api/v1/admin/attendance/approve');
            alert("Attendance Records Approved!");
            fetchLogs();
        } catch (e) {
            alert("Approval failed: " + (e.response?.data?.detail || e.message));
        }
    };

    const exportToCsv = async () => {
        try {
            const response = await api.get('/api/v1/admin/attendance/export', { responseType: 'blob' });
            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', 'approved_attendance.csv');
            document.body.appendChild(link);
            link.click();
        } catch (e) {
            alert("Export failed. Ensure data is approved first.");
        }
    };

    return (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="max-w-2xl mx-auto p-4 pb-24 space-y-6">
            <header className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-3">
                    <Link to="/" className="w-10 h-10 bg-slate-800 hover:bg-slate-700 rounded-full flex items-center justify-center text-slate-300 transition-colors">
                        <ArrowLeft size={20} />
                    </Link>
                    <div>
                        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
                            <ClipboardList className="text-primary-400" /> Audit Logs
                        </h1>
                        <p className="text-slate-400 text-sm">Detailed attendance history</p>
                    </div>
                </div>
            </header>

            <div className="flex gap-3 grid grid-cols-2">
                <button
                    onClick={handleApproveAll}
                    className="bg-emerald-600 hover:bg-emerald-500 text-white font-semibold py-3 px-4 rounded-xl transition-colors shadow-lg shadow-emerald-500/20 text-sm flex items-center justify-center gap-2"
                >
                    <CheckCircle size={18} /> Approve All
                </button>
                <button
                    onClick={exportToCsv}
                    className="bg-slate-800 hover:bg-slate-700 border border-slate-700 text-white font-semibold py-3 px-4 rounded-xl transition-colors text-sm flex items-center justify-center gap-2"
                >
                    <Download size={18} /> Export CSV
                </button>
            </div>

            {loading ? (
                <div className="flex items-center justify-center py-20 text-primary-400">
                    <Loader2 size={40} className="animate-spin" />
                </div>
            ) : (
                <div className="bg-slate-800/40 border border-slate-700/50 rounded-2xl overflow-hidden shadow-lg">
                    {logs.length === 0 ? (
                        <div className="p-8 text-center text-slate-400">
                            No attendance records found.
                        </div>
                    ) : (
                        <div className="divide-y divide-slate-700/50">
                            {logs.map((log) => (
                                <motion.div
                                    initial={{ opacity: 0, y: 10 }}
                                    animate={{ opacity: 1, y: 0 }}
                                    key={log.id}
                                    className="p-4 flex items-center justify-between hover:bg-slate-800/60 transition-colors"
                                >
                                    <div>
                                        <div className="font-bold text-slate-200">{log.student_name}</div>
                                        {editingId === log.id ? (
                                            <select
                                                value={newStatus}
                                                onChange={(e) => setNewStatus(e.target.value)}
                                                className="bg-slate-900 border border-primary-500 text-white rounded-md px-2 py-1 mt-1 text-xs focus:outline-none"
                                            >
                                                <option value="PRESENT">PRESENT</option>
                                                <option value="LATECOMER">LATECOMER</option>
                                                <option value="ABSENT">ABSENT</option>
                                            </select>
                                        ) : (
                                            <div className="flex items-center gap-1 mt-0.5">
                                                <span className={`text-xs font-bold px-2 py-0.5 rounded-md ${log.status === 'LATECOMER' ? 'bg-amber-500/10 text-amber-400 border border-amber-500/20' :
                                                    (log.status === 'PRESENT' ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' :
                                                        'bg-red-500/10 text-red-400 border border-red-500/20')
                                                    }`}>
                                                    {log.status}
                                                </span>
                                                {log.is_approved && <CheckCircle size={14} className="text-emerald-500 ml-1" />}
                                            </div>
                                        )}
                                        <div className="text-xs text-slate-500 mt-1 flex items-center gap-1">
                                            {new Date(log.timestamp).toLocaleDateString()} at {new Date(log.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                                        </div>
                                    </div>

                                    <div className="flex gap-2">
                                        {editingId === log.id ? (
                                            <>
                                                <button onClick={() => handleStatusUpdate(log.id)} className="w-8 h-8 flex items-center justify-center rounded-lg bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 transition-colors">
                                                    <Save size={16} />
                                                </button>
                                                <button onClick={() => setEditingId(null)} className="w-8 h-8 flex items-center justify-center rounded-lg bg-red-500/20 text-red-400 hover:bg-red-500/30 transition-colors">
                                                    <X size={16} />
                                                </button>
                                            </>
                                        ) : (
                                            <button
                                                onClick={() => { setEditingId(log.id); setNewStatus(log.status); }}
                                                className="w-8 h-8 flex items-center justify-center rounded-lg bg-slate-700 text-slate-300 hover:bg-slate-600 transition-colors"
                                            >
                                                <Edit size={16} />
                                            </button>
                                        )}
                                    </div>
                                </motion.div>
                            ))}
                        </div>
                    )}
                </div>
            )}
        </motion.div>
    );
}

export default Logs;
