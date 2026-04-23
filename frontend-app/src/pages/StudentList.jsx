import React, { useEffect, useState } from 'react';
import { api } from '../api';
import { ArrowLeft, Users, Download, Trash2, Loader2, Search } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';

const MotionDiv = motion.div;

function StudentList() {
    const [students, setStudents] = useState([]);
    const [loading, setLoading] = useState(true);
    const [searchQuery, setSearchQuery] = useState('');
    const role = localStorage.getItem('role');
    const navigate = useNavigate();

    useEffect(() => {
        if (role !== 'TEACHER') {
            navigate('/');
            return;
        }
        loadData();
    }, []);

    const loadData = async () => {
        try {
            const [studentsRes, attendanceRes] = await Promise.all([
                api.get('/api/v1/students/'),
                api.get('/api/v1/admin/attendance')
            ]);

            const attendanceMap = {};
            attendanceRes.data.forEach(a => {
                attendanceMap[a.student_id] = a;
            });

            const sList = studentsRes.data.map(s => ({
                ...s,
                attendance: attendanceMap[s.id] || null
            }));

            setStudents(sList);
        } catch (e) {
            console.error(e);
        } finally {
            setLoading(false);
        }
    };

    const handleReset = async () => {
        if (!window.confirm("WARNING: Are you sure you want to reset ALL attendance records globally? This cannot be undone.")) return;
        try {
            await api.delete('/api/v1/admin/attendance/reset');
            loadData();
        } catch {
            alert("Failed to reset database");
        }
    };

    const handleExport = async () => {
        try {
            const response = await api.get('/api/v1/admin/attendance/export', { responseType: 'blob' });
            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', 'global_attendance_report.csv');
            document.body.appendChild(link);
            link.click();
        } catch {
            alert("Export failed. Make sure records are properly generated.");
        }
    };

    const handleDeleteStudent = async (studentId, studentName) => {
        if (!window.confirm(`WARNING: Are you sure you want to completely delete ${studentName} and all their attendance/voice records? This cannot be undone.`)) return;
        try {
            await api.delete(`/api/v1/admin/students/${studentId}`);
            alert(`${studentName} deleted successfully.`);
            loadData();
        } catch (e) {
            alert(e.response?.data?.detail || "Failed to delete student");
        }
    };

    const filteredStudents = students.filter(s =>
        s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        (s.roll_number && s.roll_number.toLowerCase().includes(searchQuery.toLowerCase()))
    );

    return (
        <MotionDiv initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="max-w-3xl mx-auto p-4 pb-24 space-y-6">
            <header className="flex items-center justify-between flex-wrap gap-4 mb-2">
                <div className="flex items-center gap-3">
                    <Link to="/" className="w-10 h-10 bg-slate-800 hover:bg-slate-700 rounded-full flex items-center justify-center text-slate-300 transition-colors">
                        <ArrowLeft size={20} />
                    </Link>
                    <div>
                        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
                            <Users className="text-indigo-400" /> Student Directory
                        </h1>
                        <p className="text-slate-400 text-sm">{students.length} Registered Students</p>
                    </div>
                </div>

                <div className="flex gap-2 w-full md:w-auto">
                    <button
                        onClick={handleExport}
                        className="flex-1 md:flex-none bg-slate-800 hover:bg-slate-700 border border-slate-700 text-white font-semibold py-2 px-4 rounded-xl transition-colors text-sm flex items-center justify-center gap-2"
                    >
                        <Download size={16} /> Export Data
                    </button>
                    <button
                        onClick={handleReset}
                        className="bg-red-500/10 hover:bg-red-500/20 text-red-500 border border-red-500/30 p-2 rounded-xl transition-colors shrink-0"
                        title="Reset Database"
                    >
                        <Trash2 size={20} />
                    </button>
                </div>
            </header>

            <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={18} />
                <input
                    type="text"
                    placeholder="Search by Name or Roll Number..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full bg-slate-800/60 border border-slate-700 rounded-xl pl-10 pr-4 py-3 text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors"
                />
            </div>

            {loading ? (
                <div className="flex items-center justify-center py-20 text-indigo-400">
                    <Loader2 size={40} className="animate-spin" />
                </div>
            ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {filteredStudents.length === 0 ? (
                        <div className="col-span-full p-8 text-center text-slate-400 bg-slate-800/40 border border-slate-700/50 rounded-2xl">
                            No students match your search criteria.
                        </div>
                    ) : (
                        filteredStudents.map((s, index) => (
                            <MotionDiv
                                initial={{ opacity: 0, y: 10 }}
                                animate={{ opacity: 1, y: 0 }}
                                transition={{ delay: index * 0.02 }}
                                key={s.id}
                                className="bg-slate-800/40 border border-slate-700/50 p-4 rounded-2xl hover:bg-slate-800/60 transition-colors flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3"
                            >
                                <div className="w-full sm:w-auto overflow-hidden">
                                    <div className="font-bold text-slate-200 truncate">{s.name}</div>
                                    <div className="text-xs text-slate-400 mt-1 flex flex-wrap gap-2">
                                        <span className="bg-slate-900/50 px-2 py-0.5 rounded text-indigo-300 border border-indigo-500/20 truncate">Roll: {s.roll_number || 'N/A'}</span>
                                        <span className="bg-slate-900/50 px-2 py-0.5 rounded text-slate-300 border border-slate-600/50 truncate">{s.course || 'Unassigned'}</span>
                                    </div>
                                </div>
                                <div className="flex flex-row sm:flex-col items-center sm:items-end w-full sm:w-auto justify-between sm:justify-end gap-2 shrink-0">
                                    <div className={`text-xs font-bold px-2 py-1 rounded-md border ${s.attendance ? (s.attendance.status === 'LATECOMER' ? 'bg-amber-500/10 text-amber-400 border-amber-500/20' : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20') : 'bg-red-500/10 text-red-400 border-red-500/20'
                                        }`}>
                                        {s.attendance?.status || 'ABSENT'}
                                    </div>
                                    <button 
                                        onClick={() => handleDeleteStudent(s.id, s.name)}
                                        className="text-slate-500 hover:text-red-400 p-1 transition-colors"
                                        title="Delete Student"
                                    >
                                        <Trash2 size={14} />
                                    </button>
                                </div>
                            </MotionDiv>
                        ))
                    )}
                </div>
            )}
        </MotionDiv>
    );
}

export default StudentList;
