import { BrowserRouter as Router, Routes, Route, useLocation } from 'react-router-dom';
import { AuthProvider, RequireAuth, useAuth } from './context/AuthContext';
import { Toaster } from 'react-hot-toast';

import Sidebar from './components/Sidebar';
import TopBar from './components/TopBar';

// Admin Pages
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import DepartmentsPage from './pages/DepartmentsPage';
import TeachersPage from './pages/TeachersPage';
import StudentsPage from './pages/StudentsPage';
import CoursesPage from './pages/CoursesPage';
import SectionsPage from './pages/SectionsPage';
import EnrollmentsPage from './pages/EnrollmentsPage';
import SemestersPage from './pages/SemestersPage';
import RegistrationWeekPage from './pages/RegistrationWeekPage';
import ReportsPage from './pages/ReportsPage';
import AccountsPage from './pages/AccountsPage';

// Teacher Pages
import TeacherDashboardPage from './pages/teacher/TeacherDashboardPage';
import TeacherTopicsPage from './pages/teacher/TeacherTopicsPage';
import TeacherLecturesPage from './pages/teacher/TeacherLecturesPage';
import TeacherQuizzesPage from './pages/teacher/TeacherQuizzesPage';
import TeacherAnalyticsPage from './pages/teacher/TeacherAnalyticsPage';
import TeacherGradesPage from './pages/teacher/TeacherGradesPage';

function AppLayout() {
  const location = useLocation();
  const { user } = useAuth();
  const isLoginPage = location.pathname === '/login';

  const getPageTitle = (path) => {
    switch (path) {
      case '/': return 'Dashboard';
      case '/departments': return 'Departments';
      case '/teachers': return 'Teachers Directory';
      case '/students': return 'Students Directory';
      case '/courses': return 'Course Catalog';
      case '/sections': return 'Class Sections Scheduler';
      case '/enrollments': return 'Class Enrollments';
      case '/semesters': return 'Semesters Schedule';
      case '/registration-week': return 'Registration Week Settings';
      case '/reports': return 'Reports & Analytics';
      case '/accounts': return 'Account Settings';
      case '/teacher/topics': return 'Topics & Objectives';
      case '/teacher/lectures': return 'Lectures & Videos';
      case '/teacher/quizzes': return 'Quiz Management';
      case '/teacher/analytics': return 'Class Analytics';
      case '/teacher/grades': return 'Class Grade Book';
      default: return 'SmartStudy Portal';
    }
  };

  if (isLoginPage) {
    return (
      <Routes>
        <Route path="/login" element={<LoginPage />} />
      </Routes>
    );
  }

  const isTeacher = user?.role === 'teacher';

  return (
    <RequireAuth>
      <div className="app-layout">
        <Sidebar />
        <div className="main-content">
          <TopBar title={getPageTitle(location.pathname)} />
          <main className="page-body">
            {isTeacher ? (
              <Routes>
                <Route path="/" element={<TeacherDashboardPage />} />
                <Route path="/teacher/topics" element={<TeacherTopicsPage />} />
                <Route path="/teacher/lectures" element={<TeacherLecturesPage />} />
                <Route path="/teacher/quizzes" element={<TeacherQuizzesPage />} />
                <Route path="/teacher/analytics" element={<TeacherAnalyticsPage />} />
                <Route path="/teacher/grades" element={<TeacherGradesPage />} />
                <Route path="/accounts" element={<AccountsPage />} />
              </Routes>
            ) : (
              <Routes>
                <Route path="/" element={<DashboardPage />} />
                <Route path="/departments" element={<DepartmentsPage />} />
                <Route path="/teachers" element={<TeachersPage />} />
                <Route path="/students" element={<StudentsPage />} />
                <Route path="/courses" element={<CoursesPage />} />
                <Route path="/sections" element={<SectionsPage />} />
                <Route path="/enrollments" element={<EnrollmentsPage />} />
                <Route path="/semesters" element={<SemestersPage />} />
                <Route path="/registration-week" element={<RegistrationWeekPage />} />
                <Route path="/reports" element={<ReportsPage />} />
                <Route path="/accounts" element={<AccountsPage />} />
              </Routes>
            )}
          </main>
        </div>
      </div>
    </RequireAuth>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <Router>
        <AppLayout />
      </Router>
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: 'var(--bg-secondary)',
            color: 'var(--text-primary)',
            border: '1px solid var(--border)',
          },
        }}
      />
    </AuthProvider>
  );
}

