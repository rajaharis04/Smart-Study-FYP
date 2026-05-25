import { useState, useEffect } from 'react';
import { teacherPortalApi } from '../../services/api';
import { BookOpen, Users, Award, AlertTriangle, Bell, Calendar, ArrowRight, Check } from 'lucide-react';
import toast from 'react-hot-toast';
import { useAuth } from '../../context/AuthContext';

export default function TeacherDashboardPage() {
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);

  const [announcements, setAnnouncements] = useState([]);
  const [activeSectionId, setActiveSectionId] = useState(null);
  const [loadingAnnouncements, setLoadingAnnouncements] = useState(false);
  const [newAnnTitle, setNewAnnTitle] = useState('');
  const [newAnnContent, setNewAnnContent] = useState('');
  const [isSubmittingAnn, setIsSubmittingAnn] = useState(false);

  const fetchDashboardData = async () => {
    try {
      const dashboardRes = await teacherPortalApi.dashboard();
      const notifRes = await teacherPortalApi.getNotifications();
      setData(dashboardRes.data);
      setNotifications(notifRes.data);
      
      const sectionsList = dashboardRes.data?.assigned_sections || [];
      if (sectionsList.length > 0) {
        setActiveSectionId(sectionsList[0].section_id);
      }
    } catch (err) {
      toast.error('Failed to load dashboard statistics.');
    } finally {
      setLoading(false);
    }
  };

  const fetchAnnouncementsList = async (sectId) => {
    if (!sectId) return;
    setLoadingAnnouncements(true);
    try {
      const res = await teacherPortalApi.listAnnouncements(sectId);
      setAnnouncements(res.data);
    } catch (err) {
      toast.error('Failed to load announcements.');
    } finally {
      setLoadingAnnouncements(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  useEffect(() => {
    if (activeSectionId) {
      fetchAnnouncementsList(activeSectionId);
    }
  }, [activeSectionId]);

  const handlePostAnnouncement = async (e) => {
    e.preventDefault();
    if (!newAnnTitle.trim() || !newAnnContent.trim()) {
      toast.error('Title and message content are required.');
      return;
    }
    if (!activeSectionId) {
      toast.error('No class section selected.');
      return;
    }
    setIsSubmittingAnn(true);
    try {
      await teacherPortalApi.createAnnouncement(activeSectionId, {
        title: newAnnTitle,
        content: newAnnContent
      });
      toast.success('Announcement broadcasted successfully!');
      setNewAnnTitle('');
      setNewAnnContent('');
      fetchAnnouncementsList(activeSectionId);
    } catch (err) {
      toast.error('Failed to broadcast announcement.');
    } finally {
      setIsSubmittingAnn(false);
    }
  };

  const handleDeleteAnnouncement = async (annId) => {
    if (!window.confirm('Delete this announcement notice?')) return;
    try {
      await teacherPortalApi.deleteAnnouncement(annId);
      toast.success('Announcement deleted.');
      fetchAnnouncementsList(activeSectionId);
    } catch (err) {
      toast.error('Failed to delete announcement.');
    }
  };

  const handleMarkAsRead = async (notifId) => {
    try {
      await teacherPortalApi.markNotificationRead(notifId);
      setNotifications(prev => prev.filter(n => n.id !== notifId));
      toast.success('Notification cleared.');
    } catch (err) {
      toast.error('Failed to update notification.');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center" style={{ minHeight: '60vh' }}>
        <div className="loading" style={{ fontSize: '18px', color: 'var(--text-secondary)' }}>Loading Dashboard...</div>
      </div>
    );
  }

  const stats = data?.stats || { avg_attendance: 0, avg_score: 0, at_risk_count: 0 };
  const sections = data?.assigned_sections || [];
  const quizzes = data?.recent_quizzes || [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '28px' }}>
      
      {/* Page Header */}
      <div className="page-header">
        <div>
          <h1 className="page-title">Assigned Course Panel</h1>
          <p className="page-subtitle">Manage assignments, upload materials, and review student progress analytics.</p>
        </div>
        <div className="flex items-center gap-3">
          <div style={{ position: 'relative' }}>
            <div className="topbar-user" style={{ background: 'var(--bg-secondary)' }}>
              <span className="user-avatar" style={{ background: 'linear-gradient(135deg, var(--success), #34d399)' }}>
                {user?.full_name ? user.full_name.split(' ').map(n => n[0]).join('').toUpperCase().substring(0, 2) : 'T'}
              </span>
              <span className="topbar-user-name">{user?.full_name || 'Teacher'}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="stats-grid">
        <div className="stat-card" style={{ '--card-color': 'var(--success)' }}>
          <div className="stat-card-icon" style={{ background: 'rgba(16,185,129,0.15)', color: 'var(--success)' }}>
            <Users size={22} />
          </div>
          <div className="stat-card-value">{stats.avg_attendance}%</div>
          <div className="stat-card-label">Average Attendance</div>
        </div>

        <div className="stat-card" style={{ '--card-color': 'var(--accent)' }}>
          <div className="stat-card-icon" style={{ background: 'var(--accent-glow)', color: 'var(--accent-light)' }}>
            <Award size={22} />
          </div>
          <div className="stat-card-value">{stats.avg_score}%</div>
          <div className="stat-card-label">Average Quiz Score</div>
        </div>

        <div className="stat-card" style={{ '--card-color': 'var(--danger)' }}>
          <div className="stat-card-icon" style={{ background: 'rgba(239,68,68,0.15)', color: 'var(--danger)' }}>
            <AlertTriangle size={22} />
          </div>
          <div className="stat-card-value">{stats.at_risk_count}</div>
          <div className="stat-card-label">At-Risk Students</div>
        </div>

        <div className="stat-card" style={{ '--card-color': 'var(--info)' }}>
          <div className="stat-card-icon" style={{ background: 'rgba(59,130,246,0.15)', color: 'var(--info)' }}>
            <BookOpen size={22} />
          </div>
          <div className="stat-card-value">{sections.length}</div>
          <div className="stat-card-label">Assigned Sections</div>
        </div>
      </div>

      {/* Main Grid split */}
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '28px' }}>
        
        {/* Left Column: Sections & Quizzes */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '28px' }}>
          
          {/* Sections List */}
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">My Class Sections</h3>
            </div>
            <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: '16px', padding: '20px' }}>
              {sections.length === 0 ? (
                <div className="empty-state">
                  <p>No active courses or sections assigned by the administrator yet.</p>
                </div>
              ) : (
                sections.map((sec) => (
                  <div 
                    key={sec.section_id} 
                    className="card" 
                    style={{ 
                      padding: '16px', 
                      display: 'flex', 
                      justifyContent: 'space-between', 
                      alignItems: 'center', 
                      background: 'rgba(255,255,255,0.02)',
                      borderColor: 'var(--border)'
                    }}
                  >
                    <div>
                      <h4 style={{ fontSize: '15px', fontWeight: '600', color: 'var(--text-primary)' }}>
                        {sec.course_name} ({sec.course_code})
                      </h4>
                      <div className="flex gap-4 mt-4" style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                        <span className="badge badge-accent">Section {sec.section_label}</span>
                        <span>👥 {sec.enrolled_count} Students Enrolled</span>
                        <span>📍 {sec.room}</span>
                        <span>⏰ {sec.schedule}</span>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Class Noticeboard */}
          <div className="card" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div className="card-header" style={{ padding: 0, borderBottom: '1px solid var(--border)', paddingBottom: '10px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 className="card-title flex items-center gap-2" style={{ margin: 0 }}>
                📢 Class Announcements noticeboard
              </h3>
              {sections.length > 0 && (
                <select
                  className="form-control"
                  style={{ width: '200px', padding: '4px 8px', fontSize: '13px', background: 'var(--bg-primary)' }}
                  value={activeSectionId || ''}
                  onChange={(e) => setActiveSectionId(parseInt(e.target.value))}
                >
                  {sections.map(s => (
                    <option key={s.section_id} value={s.section_id}>
                      Sec {s.section_label} ({s.course_code})
                    </option>
                  ))}
                </select>
              )}
            </div>

            {/* Post New Announcement Form */}
            <form onSubmit={handlePostAnnouncement} style={{ display: 'flex', flexDirection: 'column', gap: '10px', background: 'rgba(255,255,255,0.01)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: '14px' }}>
              <h4 style={{ fontSize: '13px', fontWeight: '700', margin: 0 }}>Create Announcement</h4>
              <input
                type="text"
                className="form-control"
                style={{ fontSize: '13px', padding: '6px 10px' }}
                placeholder="Announcement Title..."
                required
                value={newAnnTitle}
                onChange={(e) => setNewAnnTitle(e.target.value)}
              />
              <textarea
                className="form-control"
                style={{ fontSize: '13px', padding: '8px 10px', minHeight: '60px', resize: 'vertical' }}
                placeholder="Write notice board message contents..."
                required
                value={newAnnContent}
                onChange={(e) => setNewAnnContent(e.target.value)}
              />
              <button type="submit" className="btn btn-primary btn-sm" style={{ alignSelf: 'flex-end' }} disabled={isSubmittingAnn}>
                {isSubmittingAnn ? 'Broadcasting...' : 'Post Notice'}
              </button>
            </form>

            {/* List Announcements */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', maxHeight: '350px', overflowY: 'auto' }}>
              {loadingAnnouncements ? (
                <div style={{ fontSize: '12px', color: 'var(--text-secondary)', textAlign: 'center', padding: '10px' }}>Loading announcements...</div>
              ) : announcements.length === 0 ? (
                <div style={{ fontSize: '12px', color: 'var(--text-muted)', textAlign: 'center', padding: '10px' }}>No announcements posted for this section yet.</div>
              ) : (
                announcements.map(ann => (
                  <div key={ann.id} style={{ background: 'rgba(255,255,255,0.01)', border: '1px solid var(--border)', borderRadius: 'var(--radius-sm)', padding: '12px', display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontSize: '13px', fontWeight: '700', color: 'var(--text-primary)' }}>{ann.title}</span>
                      <button
                        type="button"
                        onClick={() => handleDeleteAnnouncement(ann.id)}
                        style={{ border: 'none', background: 'transparent', color: 'var(--danger)', fontSize: '11px', cursor: 'pointer' }}
                      >
                        Delete
                      </button>
                    </div>
                    <p style={{ fontSize: '12px', color: 'var(--text-secondary)', margin: 0, lineHeight: '1.4', wordBreak: 'break-word' }}>{ann.content}</p>
                    <span style={{ fontSize: '9px', color: 'var(--text-muted)' }}>
                      {new Date(ann.created_at).toLocaleString()}
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Quizzes Status */}
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">Recent Quizzes Status</h3>
            </div>
            <div className="card-body" style={{ padding: 0 }}>
              {quizzes.length === 0 ? (
                <div className="empty-state" style={{ padding: '32px' }}>
                  <p>No lectures have been uploaded and auto-graded quizzes generated yet.</p>
                </div>
              ) : (
                <div className="table-wrapper">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Lecture Topic</th>
                        <th>Type</th>
                        <th>Created Date</th>
                        <th>Student Attempts</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {quizzes.map((quiz) => (
                        <tr key={quiz.quiz_id}>
                          <td>{quiz.lecture_title}</td>
                          <td>
                            <span className="badge badge-info">{quiz.quiz_type}</span>
                          </td>
                          <td>
                            <span className="flex items-center gap-2">
                              <Calendar size={13} />
                              {new Date(quiz.created_at).toLocaleDateString()}
                            </span>
                          </td>
                          <td>{quiz.attempts_count} attempted</td>
                          <td>
                            {quiz.is_published ? (
                              <span className="badge badge-success">Live</span>
                            ) : (
                              <span className="badge badge-warning">Draft</span>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Right Column: Notification Sidebar */}
        <div className="card" style={{ height: 'fit-content' }}>
          <div className="card-header" style={{ borderBottom: '1px solid var(--border)' }}>
            <h3 className="card-title flex items-center gap-2">
              <Bell size={18} className="text-warning" />
              Notifications Center
            </h3>
            {notifications.length > 0 && (
              <span className="badge badge-warning">{notifications.filter(n => !n.is_read).length} Unread</span>
            )}
          </div>
          <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: '12px', padding: '16px', maxHeight: '500px', overflowY: 'auto' }}>
            {notifications.length === 0 ? (
              <div className="empty-state" style={{ padding: '24px 12px' }}>
                <p>No recent alerts or notifications.</p>
              </div>
            ) : (
              notifications.map((n) => (
                <div 
                  key={n.id} 
                  className="card" 
                  style={{ 
                    padding: '12px', 
                    background: n.is_read ? 'rgba(255,255,255,0.01)' : 'rgba(99,102,241,0.04)',
                    borderLeft: n.is_read ? '1px solid var(--border)' : '3px solid var(--accent)',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '6px'
                  }}
                >
                  <div className="flex justify-between items-center">
                    <span style={{ fontSize: '13px', fontWeight: '600', color: 'var(--text-primary)' }}>{n.title}</span>
                    {!n.is_read && (
                      <button 
                        onClick={() => handleMarkAsRead(n.id)}
                        style={{ border: 'none', background: 'transparent', color: 'var(--success)', display: 'flex', alignItems: 'center', cursor: 'pointer' }}
                        title="Mark as read"
                      >
                        <Check size={14} />
                      </button>
                    )}
                  </div>
                  <p style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: '1.4' }}>{n.message}</p>
                  <span style={{ fontSize: '9px', color: 'var(--text-muted)' }}>
                    {new Date(n.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })} - {new Date(n.created_at).toLocaleDateString()}
                  </span>
                </div>
              ))
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
