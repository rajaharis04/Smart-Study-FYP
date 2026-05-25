import { NavLink } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  LayoutDashboard,
  Building2,
  Users,
  GraduationCap,
  BookOpen,
  Layers,
  Calendar,
  UserCheck,
  BarChart3,
  Settings,
  LogOut,
  Video,
  ClipboardList,
  FileSpreadsheet
} from 'lucide-react';

export default function Sidebar() {
  const { logout, user } = useAuth();

  const adminNavItems = [
    { to: '/', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/departments', label: 'Departments', icon: Building2 },
    { to: '/teachers', label: 'Teachers', icon: Users },
    { to: '/students', label: 'Students', icon: GraduationCap },
    { to: '/courses', label: 'Courses', icon: BookOpen },
    { to: '/sections', label: 'Sections', icon: Layers },
    { to: '/enrollments', label: 'Enrollments', icon: UserCheck },
    { to: '/semesters', label: 'Semesters', icon: Calendar },
    { to: '/reports', label: 'Reports', icon: BarChart3 },
    { to: '/accounts', label: 'Accounts', icon: Settings },
  ];

  const teacherNavItems = [
    { to: '/', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/teacher/topics', label: 'Topics & Objectives', icon: BookOpen },
    { to: '/teacher/lectures', label: 'Lectures & Videos', icon: Video },
    { to: '/teacher/quizzes', label: 'Quiz Manager', icon: ClipboardList },
    { to: '/teacher/analytics', label: 'Class Analytics', icon: BarChart3 },
    { to: '/teacher/grades', label: 'Grade Book', icon: FileSpreadsheet },
    { to: '/accounts', label: 'Accounts', icon: Settings },
  ];

  const isTeacher = user?.role === 'teacher';
  const navItems = isTeacher ? teacherNavItems : adminNavItems;

  return (
    <aside className="sidebar">
      <div className="sidebar-logo">
        <div className="sidebar-logo-icon">🎓</div>
        <div>
          <h1>SmartStudy</h1>
          <span>{isTeacher ? 'Teacher Portal' : 'Admin Portal'}</span>
        </div>
      </div>

      <nav className="sidebar-nav">
        <div className="nav-section-title">Management</div>
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
            >
              <Icon size={18} />
              <span>{item.label}</span>
            </NavLink>
          );
        })}
      </nav>

      <div className="sidebar-footer">
        <button className="nav-item text-danger" onClick={logout} style={{ width: '100%' }}>
          <LogOut size={18} />
          <span>Logout</span>
        </button>
      </div>
    </aside>
  );
}

