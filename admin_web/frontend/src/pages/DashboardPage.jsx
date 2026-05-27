import { useState, useEffect } from 'react';
import { reportsApi, announcementApi, deptApi } from '../services/api';
import StatCard from '../components/StatCard';
import { toast } from 'react-hot-toast';
import {
  Building2,
  Users,
  GraduationCap,
  BookOpen,
  Layers,
  UserCheck,
  Calendar,
  AlertCircle,
  Megaphone,
  Trash2,
  AlertTriangle,
  Send
} from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

export default function DashboardPage() {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  // Noticeboard state
  const [announcements, setAnnouncements] = useState([]);
  const [depts, setDepts] = useState([]);
  const [newTitle, setNewTitle] = useState('');
  const [newContent, setNewContent] = useState('');
  const [newRole, setNewRole] = useState('all');
  const [newDept, setNewDept] = useState('');
  const [submittingAnn, setSubmittingAnn] = useState(false);

  // At-Risk state
  const [atRiskList, setAtRiskList] = useState([]);
  const [loadingRisk, setLoadingRisk] = useState(true);

  // Visual Charts state
  const [deptKpis, setDeptKpis] = useState([]);
  const [studentsPerSec, setStudentsPerSec] = useState([]);
  const [loadingCharts, setLoadingCharts] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const statsRes = await reportsApi.stats();
        setStats(statsRes.data);
      } catch (err) {
        setError('Failed to load system statistics.');
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  useEffect(() => {
    async function fetchNoticeboardAndRisk() {
      try {
        const [annsRes, deptsRes, riskRes, kpisRes, secRes] = await Promise.all([
          announcementApi.list(),
          deptApi.list(),
          reportsApi.atRiskSummary(),
          reportsApi.departmentalKpis(),
          reportsApi.studentsPerSection()
        ]);
        setAnnouncements(annsRes.data);
        setDepts(deptsRes.data);
        setAtRiskList(riskRes.data);
        setDeptKpis(kpisRes.data);
        setStudentsPerSec(secRes.data);
      } catch (err) {
        console.error('Failed to load dashboard extensions:', err);
      } finally {
        setLoadingRisk(false);
        setLoadingCharts(false);
      }
    }
    fetchNoticeboardAndRisk();
  }, []);

  const handleCreateAnnouncement = async (e) => {
    e.preventDefault();
    if (!newTitle.trim() || !newContent.trim()) {
      toast.error('Title and content are required.');
      return;
    }
    setSubmittingAnn(true);
    try {
      const payload = {
        title: newTitle,
        content: newContent,
        target_role: newRole,
        department_id: newDept ? parseInt(newDept, 10) : null
      };
      const res = await announcementApi.create(payload);
      toast.success('Global announcement broadcasted!');
      setAnnouncements([res.data, ...announcements]);
      setNewTitle('');
      setNewContent('');
      setNewRole('all');
      setNewDept('');
    } catch (err) {
      toast.error('Failed to post announcement.');
    } finally {
      setSubmittingAnn(false);
    }
  };

  const handleDeleteAnnouncement = async (id) => {
    if (!window.confirm('Are you sure you want to delete this announcement?')) return;
    try {
      await announcementApi.delete(id);
      toast.success('Announcement removed.');
      setAnnouncements(announcements.filter(a => a.id !== id));
    } catch (err) {
      toast.error('Failed to delete announcement.');
    }
  };

  if (loading) {
    return <div className="loading" style={{ padding: '24px', textAlign: 'center' }}>Loading system telemetry...</div>;
  }

  if (error) {
    return (
      <div className="result-box error" style={{ margin: '24px', display: 'flex', alignItems: 'center', gap: '8px' }}>
        <AlertCircle size={18} />
        <span>{error}</span>
      </div>
    );
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Admin Dashboard</h1>
          <p className="page-subtitle">Overview of the SmartStudy platform status.</p>
        </div>
        {stats?.active_semester && (
          <div
            className="badge badge-accent"
            style={{ display: 'flex', alignItems: 'center', gap: '6px', padding: '8px 16px' }}
          >
            <Calendar size={14} />
            <span>Active Semester: {stats.active_semester}</span>
          </div>
        )}
      </div>

      <div className="stats-grid">
        <StatCard
          title="Total Departments"
          value={stats?.total_departments}
          icon={Building2}
          color="var(--accent)"
        />
        <StatCard
          title="Total Teachers"
          value={stats?.total_teachers}
          icon={Users}
          color="var(--info)"
        />
        <StatCard
          title="Total Students"
          value={stats?.total_students}
          icon={GraduationCap}
          color="var(--success)"
        />
        <StatCard
          title="Active Courses"
          value={stats?.total_courses}
          icon={BookOpen}
          color="var(--warning)"
        />
        <StatCard
          title="Class Sections"
          value={stats?.total_sections}
          icon={Layers}
          color="var(--danger)"
        />
        <StatCard
          title="Total Enrollments"
          value={stats?.total_enrollments}
          icon={UserCheck}
          color="var(--accent-light)"
        />
      </div>

      {/* ─── VISUAL TELEMETRY & ANALYTICS CHARTS ─── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(450px, 1fr))', gap: '24px', marginTop: '24px' }}>
        
        {/* Chart 1: Department Workload (Students & Teachers) */}
        <div className="card">
          <div className="card-header" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Building2 className="text-accent" size={20} />
            <h3 className="card-title">Department Workload Distribution</h3>
          </div>
          <div className="card-body" style={{ minHeight: '300px', padding: '20px', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
            {loadingCharts ? (
              <div style={{ textAlign: 'center', color: 'var(--text-secondary)' }}>Loading workload distribution...</div>
            ) : deptKpis.length > 0 ? (
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={deptKpis} margin={{ top: 10, right: 10, left: -20, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                  <XAxis dataKey="code" stroke="var(--text-muted)" fontSize={11} tickLine={false} />
                  <YAxis stroke="var(--text-muted)" fontSize={11} tickLine={false} />
                  <Tooltip
                    contentStyle={{
                      background: 'var(--bg-secondary)',
                      borderColor: 'var(--border)',
                      borderRadius: '8px',
                      color: 'var(--text-primary)',
                      fontSize: '12px'
                    }}
                  />
                  <Legend verticalAlign="top" height={36} wrapperStyle={{ fontSize: '11px' }} />
                  <Bar name="Total Students" dataKey="total_students" fill="var(--accent)" radius={[4, 4, 0, 0]} />
                  <Bar name="Total Teachers" dataKey="total_teachers" fill="var(--info)" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
                No department data available.
              </div>
            )}
          </div>
        </div>

        {/* Chart 2: Comparative Department Performance */}
        <div className="card">
          <div className="card-header" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <UserCheck className="text-success" size={20} />
            <h3 className="card-title">Comparative Academic Performance</h3>
          </div>
          <div className="card-body" style={{ minHeight: '300px', padding: '20px', display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
            {loadingCharts ? (
              <div style={{ textAlign: 'center', color: 'var(--text-secondary)' }}>Loading academic metrics...</div>
            ) : deptKpis.length > 0 ? (
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={deptKpis} margin={{ top: 10, right: 10, left: -20, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                  <XAxis dataKey="code" stroke="var(--text-muted)" fontSize={11} tickLine={false} />
                  <YAxis stroke="var(--text-muted)" fontSize={11} tickLine={false} domain={[0, 100]} />
                  <Tooltip
                    contentStyle={{
                      background: 'var(--bg-secondary)',
                      borderColor: 'var(--border)',
                      borderRadius: '8px',
                      color: 'var(--text-primary)',
                      fontSize: '12px'
                    }}
                  />
                  <Legend verticalAlign="top" height={36} wrapperStyle={{ fontSize: '11px' }} />
                  <Bar name="Avg Attendance %" dataKey="average_attendance" fill="var(--success)" radius={[4, 4, 0, 0]} />
                  <Bar name="Quiz Mastery %" dataKey="average_quiz_success" fill="var(--warning)" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div style={{ textAlign: 'center', color: 'var(--text-muted)', fontSize: '13px' }}>
                No performance telemetry available.
              </div>
            )}
          </div>
        </div>

      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(450px, 1fr))', gap: '24px', marginTop: '24px' }}>
        
        {/* LEFT COLUMN: GLOBAL NOTICEBOARD */}
        <div className="card">
          <div className="card-header" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Megaphone className="text-accent" size={20} />
            <h3 className="card-title">Global Noticeboard & Bulletin</h3>
          </div>
          <div className="card-body">
            <form onSubmit={handleCreateAnnouncement} style={{ display: 'flex', flexDirection: 'column', gap: '12px', marginBottom: '24px' }}>
              <div style={{ display: 'flex', gap: '12px' }}>
                <div style={{ flex: 2 }}>
                  <label className="label" style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Broadcast Title</label>
                  <input
                    type="text"
                    className="input"
                    placeholder="e.g. System Maintenance Window"
                    value={newTitle}
                    onChange={e => setNewTitle(e.target.value)}
                    required
                  />
                </div>
                <div style={{ flex: 1 }}>
                  <label className="label" style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Target Role</label>
                  <select
                    className="input"
                    value={newRole}
                    onChange={e => setNewRole(e.target.value)}
                  >
                    <option value="all">All Roles</option>
                    <option value="teachers">Teachers Only</option>
                    <option value="students">Students Only</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="label" style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Target Department (Optional)</label>
                <select
                  className="input"
                  value={newDept}
                  onChange={e => setNewDept(e.target.value)}
                >
                  <option value="">All Departments</option>
                  {depts.map(d => (
                    <option key={d.id} value={d.id}>{d.name} ({d.code})</option>
                  ))}
                </select>
              </div>

              <div>
                <label className="label" style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>Bulletin Content</label>
                <textarea
                  className="input"
                  placeholder="Type the announcement details here..."
                  style={{ minHeight: '80px', resize: 'vertical' }}
                  value={newContent}
                  onChange={e => setNewContent(e.target.value)}
                  required
                />
              </div>

              <button type="submit" className="btn btn-primary" disabled={submittingAnn} style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
                <Send size={14} />
                <span>{submittingAnn ? 'Publishing...' : 'Publish Announcement'}</span>
              </button>
            </form>

            <div style={{ borderTop: '1px solid var(--border)', paddingTop: '16px' }}>
              <h4 style={{ fontWeight: 600, fontSize: '14px', marginBottom: '12px' }}>Active Broadcasts</h4>
              {announcements.length === 0 ? (
                <p style={{ color: 'var(--text-muted)', fontSize: '13px', textAlign: 'center', padding: '16px 0' }}>No active global bulletins.</p>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', maxHeight: '350px', overflowY: 'auto', paddingRight: '4px' }}>
                  {announcements.map(ann => (
                    <div
                      key={ann.id}
                      style={{
                        background: 'rgba(255, 255, 255, 0.02)',
                        border: '1px solid var(--border)',
                        borderRadius: 'var(--radius-sm)',
                        padding: '12px',
                        position: 'relative'
                      }}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '6px' }}>
                        <div>
                          <h5 style={{ fontWeight: 600, fontSize: '14px', color: 'var(--text-primary)' }}>{ann.title}</h5>
                          <span style={{ fontSize: '11px', color: 'var(--text-muted)' }}>
                            {new Date(ann.created_at).toLocaleString()}
                          </span>
                        </div>
                        <button
                          type="button"
                          onClick={() => handleDeleteAnnouncement(ann.id)}
                          style={{
                            background: 'transparent',
                            border: 'none',
                            color: 'var(--danger)',
                            cursor: 'pointer',
                            opacity: 0.8,
                            padding: '4px'
                          }}
                          title="Delete Bulletin"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                      <p style={{ fontSize: '13px', color: 'var(--text-secondary)', whiteSpace: 'pre-wrap', marginBottom: '8px' }}>
                        {ann.content}
                      </p>
                      <div style={{ display: 'flex', gap: '6px', flexWrap: 'wrap' }}>
                        <span className="badge badge-accent" style={{ fontSize: '10px', padding: '2px 8px' }}>
                          Role: {ann.target_role}
                        </span>
                        {ann.department_name && (
                          <span className="badge badge-info" style={{ fontSize: '10px', padding: '2px 8px' }}>
                            Dept: {ann.department_name}
                          </span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        {/* RIGHT COLUMN: AT-RISK TELEMETRY WARNINGS */}
        <div className="card">
          <div className="card-header" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <AlertTriangle className="text-danger" size={20} />
            <h3 className="card-title">At-Risk Student Telemetry Alerts</h3>
          </div>
          <div className="card-body">
            <p style={{ color: 'var(--text-secondary)', fontSize: '13px', marginBottom: '16px' }}>
              Identifies active students globally whose performance or attendance metrics fall below critical thresholds:
              <br />
              <span style={{ color: 'var(--danger)', fontWeight: 500 }}>Quiz Grade &lt; 50%</span> or <span style={{ color: 'var(--warning)', fontWeight: 500 }}>Attendance &lt; 75%</span>.
            </p>

            {loadingRisk ? (
              <p style={{ color: 'var(--text-secondary)', fontSize: '13px', textAlign: 'center', padding: '32px' }}>Analyzing global student telemetry...</p>
            ) : atRiskList.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '32px', border: '1px dashed var(--border)', borderRadius: 'var(--radius-md)' }}>
                <span style={{ color: 'var(--success)', fontWeight: 600, display: 'block', marginBottom: '4px' }}>All Clear!</span>
                <p style={{ color: 'var(--text-muted)', fontSize: '13px' }}>No students currently match at-risk warning parameters.</p>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', maxHeight: '580px', overflowY: 'auto', paddingRight: '4px' }}>
                {atRiskList.map(student => (
                  <div
                    key={student.id}
                    style={{
                      background: 'rgba(239, 68, 68, 0.02)',
                      border: '1px solid rgba(239, 68, 68, 0.15)',
                      borderRadius: 'var(--radius-md)',
                      padding: '16px'
                    }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '10px' }}>
                      <div>
                        <h4 style={{ fontWeight: 600, fontSize: '15px', color: 'var(--text-primary)' }}>{student.name}</h4>
                        <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>
                          {student.reg_number} • {student.department}
                        </span>
                      </div>
                      <span className="badge badge-danger" style={{ fontSize: '11px', padding: '3px 8px', fontWeight: 600 }}>
                        At-Risk
                      </span>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginBottom: '10px' }}>
                      <div style={{ background: 'rgba(255,255,255,0.02)', padding: '8px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)' }}>
                        <span style={{ fontSize: '11px', color: 'var(--text-secondary)', display: 'block' }}>Attendance Rate</span>
                        <span style={{
                          fontSize: '16px',
                          fontWeight: 700,
                          color: student.attendance_rate < 75 ? 'var(--warning)' : 'var(--success)'
                        }}>
                          {student.attendance_rate}%
                        </span>
                      </div>
                      <div style={{ background: 'rgba(255,255,255,0.02)', padding: '8px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)' }}>
                        <span style={{ fontSize: '11px', color: 'var(--text-secondary)', display: 'block' }}>Quiz Mastery</span>
                        <span style={{
                          fontSize: '16px',
                          fontWeight: 700,
                          color: student.quiz_grade < 50 ? 'var(--danger)' : 'var(--success)'
                        }}>
                          {student.quiz_grade}%
                        </span>
                      </div>
                    </div>

                    {student.weakest_courses && student.weakest_courses.length > 0 ? (
                      <div>
                        <span style={{ fontSize: '11px', color: 'var(--text-secondary)', fontWeight: 500, display: 'block', marginBottom: '4px' }}>
                          Triggering Courses:
                        </span>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                          {student.weakest_courses.map((wc, i) => (
                            <div
                              key={i}
                              style={{
                                display: 'flex',
                                justifyContent: 'space-between',
                                fontSize: '12px',
                                background: 'rgba(0,0,0,0.15)',
                                padding: '4px 8px',
                                borderRadius: 'var(--radius-sm)'
                              }}
                            >
                              <span style={{ color: 'var(--text-primary)', fontWeight: 500 }}>
                                {wc.course_code} - {wc.course_name}
                              </span>
                              <span style={{ color: 'var(--text-secondary)' }}>
                                Att: {wc.attendance_rate}% | Quiz: {wc.quiz_grade}%
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    ) : (
                      <p style={{ fontSize: '11px', color: 'var(--text-muted)' }}>Low global profile score across enrolled sections.</p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

      </div>

      <div className="card" style={{ marginTop: '24px' }}>
        <div className="card-header">
          <h3 className="card-title">System Welcome Guide</h3>
        </div>
        <div className="card-body">
          <p style={{ color: 'var(--text-secondary)', marginBottom: '16px' }}>
            Welcome to the SmartStudy Admin Web Panel. As an administrator, you have complete control over the system configurations and data structure:
          </p>
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
              gap: '16px',
            }}
          >
            <div
              style={{
                background: 'rgba(255,255,255,0.02)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-md)',
                padding: '16px',
              }}
            >
              <h4 style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: '8px' }}>1. Populate Academics</h4>
              <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
                Set up <strong>Departments</strong> first, then define <strong>Semesters</strong> and upload <strong>Courses</strong>.
              </p>
            </div>
            <div
              style={{
                background: 'rgba(255,255,255,0.02)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-md)',
                padding: '16px',
              }}
            >
              <h4 style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: '8px' }}>2. Provision Users</h4>
              <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
                Create <strong>Teacher</strong> accounts (passwords generated dynamically) and upload <strong>Students</strong> via CSV.
              </p>
            </div>
            <div
              style={{
                background: 'rgba(255,255,255,0.02)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-md)',
                padding: '16px',
              }}
            >
              <h4 style={{ fontWeight: 600, color: 'var(--text-primary)', marginBottom: '8px' }}>3. Define Sections & Enroll</h4>
              <p style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>
                Create course <strong>Sections</strong>, assign teachers, set room/schedule details, and map student enrollments.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
