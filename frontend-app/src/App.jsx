import { BrowserRouter, Routes, Route, Link, useLocation, Navigate } from 'react-router-dom'
import { Mic, UserCheck, Settings, Home, LogOut, Users } from 'lucide-react'

// Pages
import Dashboard from './pages/Dashboard'
import StudentList from './pages/StudentList'
import Enroll from './pages/Enroll'
import Verify from './pages/Verify'
import Config from './pages/Config'
import Logs from './pages/Logs'
import Login from './pages/Login'

import './index.css'

function ProtectedRoute({ children }) {
  const token = localStorage.getItem('token');
  if (!token) return <Navigate to="/login" replace />;
  return children;
}

function NavBar() {
  const location = useLocation();
  const isActive = (path) => location.pathname === path;
  const role = localStorage.getItem('role');

  const handleLogout = () => {
    localStorage.clear();
    window.location.href = (import.meta.env.BASE_URL || '/') + 'login';
  };

  if (!localStorage.getItem('token')) return null;

  return (
    <div className="fixed bottom-0 left-0 right-0 bg-slate-900/95 backdrop-blur-md border-t border-slate-800 flex justify-around p-4 z-50 shadow-[0_-10px_40px_-15px_rgba(0,0,0,0.5)] safe-area-pb">
      <Link
        to="/"
        className={`flex flex-col items-center gap-1 transition-colors ${isActive('/') ? 'text-primary-500' : 'text-slate-500 hover:text-slate-300'}`}
      >
        <div className={`p-2 rounded-xl transition-all ${isActive('/') ? 'bg-primary-500/10' : 'bg-transparent'}`}>
          <Home size={22} />
        </div>
      </Link>

      {role === 'STUDENT' ? (
        <>
          <Link
            to="/enroll"
            className={`flex flex-col items-center gap-1 transition-colors ${isActive('/enroll') ? 'text-primary-500' : 'text-slate-500 hover:text-slate-300'}`}
          >
            <div className={`p-2 rounded-xl transition-all ${isActive('/enroll') ? 'bg-primary-500/10' : 'bg-transparent'}`}>
              <Mic size={22} />
            </div>
          </Link>
          <Link
            to="/verify"
            className={`flex flex-col items-center gap-1 transition-colors ${isActive('/verify') ? 'text-primary-500' : 'text-slate-500 hover:text-slate-300'}`}
          >
            <div className={`p-2 rounded-xl transition-all ${isActive('/verify') ? 'bg-primary-500/10' : 'bg-transparent'}`}>
              <UserCheck size={22} />
            </div>
          </Link>
        </>
      ) : (
        <>
          <Link
            to="/students"
            className={`flex flex-col items-center gap-1 transition-colors ${isActive('/students') ? 'text-primary-500' : 'text-slate-500 hover:text-slate-300'}`}
          >
            <div className={`p-2 rounded-xl transition-all ${isActive('/students') ? 'bg-primary-500/10' : 'bg-transparent'}`}>
              <Users size={22} />
            </div>
          </Link>
          <Link
            to="/logs"
            className={`flex flex-col items-center gap-1 transition-colors ${isActive('/logs') ? 'text-primary-500' : 'text-slate-500 hover:text-slate-300'}`}
          >
            <div className={`p-2 rounded-xl transition-all ${isActive('/logs') ? 'bg-primary-500/10' : 'bg-transparent'}`}>
              <UserCheck size={22} />
            </div>
          </Link>
          <Link
            to="/settings"
            className={`flex flex-col items-center gap-1 transition-colors ${isActive('/settings') ? 'text-primary-500' : 'text-slate-500 hover:text-slate-300'}`}
          >
            <div className={`p-2 rounded-xl transition-all ${isActive('/settings') ? 'bg-primary-500/10' : 'bg-transparent'}`}>
              <Settings size={22} />
            </div>
          </Link>
        </>
      )}

      <button
        onClick={handleLogout}
        className="flex flex-col items-center gap-1 text-slate-500 hover:text-red-400 transition-colors bg-transparent border-none cursor-pointer p-0"
      >
        <div className="p-2 rounded-xl bg-transparent">
          <LogOut size={22} />
        </div>
      </button>
    </div>
  )
}

function App() {
  const basename = import.meta.env.BASE_URL || '/';
  return (
    <BrowserRouter basename={basename}>
      <div className="pb-24 min-h-screen bg-slate-950 text-slate-100 font-sans selection:bg-primary-500/30">
        <Routes>
          <Route path="/login" element={<Login />} />

          <Route path="/" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
          <Route path="/students" element={<ProtectedRoute><StudentList /></ProtectedRoute>} />
          <Route path="/enroll" element={<ProtectedRoute><Enroll /></ProtectedRoute>} />
          <Route path="/verify" element={<ProtectedRoute><Verify /></ProtectedRoute>} />
          <Route path="/settings" element={<ProtectedRoute><Config /></ProtectedRoute>} />
          <Route path="/logs" element={<ProtectedRoute><Logs /></ProtectedRoute>} />
        </Routes>
        <NavBar />
      </div>
    </BrowserRouter>
  )
}

export default App
