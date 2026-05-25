import { useState, useEffect } from 'react';
import { reportsApi } from '../services/api';
import DataTable from '../components/DataTable';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell } from 'recharts';
import { BarChart3, Users, BookOpen, AlertCircle, ShieldAlert, Activity, ClipboardList } from 'lucide-react';

const COLORS = ['#6366f1', '#818cf8', '#4f46e5', '#3b82f6', '#10b981', '#f59e0b', '#ef4444'];

export default function ReportsPage() {
  const [activeTab, setActiveTab] = useState('academics'); // academics | departments | audit
  
  // Data States
  const [studentsPerSec, setStudentsPerSec] = useState([]);
  const [teachersSummary, setTeachersSummary] = useState([]);
  const [deptKpis, setDeptKpis] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    async function fetchAllReports() {
      try {
        const [secRes, teachRes, kpiRes, auditRes] = await Promise.all([
          reportsApi.studentsPerSection(),
          reportsApi.teachersSummary(),
          reportsApi.departmentalKpis(),
          reportsApi.auditLogs()
        ]);
        setStudentsPerSec(secRes.data);
        setTeachersSummary(teachRes.data);
        setDeptKpis(kpiRes.data);
        setAuditLogs(auditRes.data);
      } catch (err) {
        setError('Failed to fetch platform analytics datasets.');
      } finally {
        setLoading(false);
      }
    }
    fetchAllReports();
  }, []);

  if (loading) {
    return <div className="loading" style={{ textAlign: 'center', padding: '24px' }}>Compiling system telemetry...</div>;
  }

  if (error) {
    return (
      <div className="result-box error" style={{ margin: '24px', display: 'flex', alignItems: 'center', gap: '8px' }}>
        <AlertCircle size={18} />
        <span>{error}</span>
      </div>
    );
  }

  const teacherHeaders = [
    { key: 'employee_id', label: 'Employee ID' },
    { key: 'name', label: 'Teacher Name' },
    { key: 'department', label: 'Department' },
    { key: 'sections_count', label: 'Sections Assigned' },
    { key: 'is_active', label: 'Status' },
  ];

  const auditHeaders = [
    { key: 'timestamp', label: 'Timestamp' },
    { key: 'user_name', label: 'Administrator' },
    { key: 'action', label: 'Action Type' },
    { key: 'details', label: 'Modification Details' },
  ];

  // Helper for audit action colors
  const getActionBadgeClass = (action) => {
    if (action.includes('CREATE')) return 'badge-success';
    if (action.includes('DELETE')) return 'badge-danger';
    if (action.includes('UPDATE')) return 'badge-info';
    if (action.includes('ROLLOVER')) return 'badge-accent';
    return 'badge-warning';
  };

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Reports & System Logs</h1>
          <p className="page-subtitle">Analyze performance trends, faculty workload distribution, and audit security logs.</p>
        </div>
      </div>

      {/* Tabs Menu */}
      <div style={{
        display: 'flex',
        gap: '12px',
        borderBottom: '1px solid var(--border)',
        marginBottom: '24px',
        paddingBottom: '2px'
      }}>
        <button
          onClick={() => setActiveTab('academics')}
          style={{
            background: 'transparent',
            border: 'none',
            color: activeTab === 'academics' ? 'var(--accent-light)' : 'var(--text-secondary)',
            borderBottom: activeTab === 'academics' ? '2px solid var(--accent)' : '2px solid transparent',
            padding: '8px 16px',
            fontWeight: 500,
            fontSize: '14px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}
        >
          <Activity size={16} />
          Academics & Faculty Workload
        </button>
        <button
          onClick={() => setActiveTab('departments')}
          style={{
            background: 'transparent',
            border: 'none',
            color: activeTab === 'departments' ? 'var(--accent-light)' : 'var(--text-secondary)',
            borderBottom: activeTab === 'departments' ? '2px solid var(--accent)' : '2px solid transparent',
            padding: '8px 16px',
            fontWeight: 500,
            fontSize: '14px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}
        >
          <BarChart3 size={16} />
          Departmental Performance KPIs
        </button>
        <button
          onClick={() => setActiveTab('audit')}
          style={{
            background: 'transparent',
            border: 'none',
            color: activeTab === 'audit' ? 'var(--accent-light)' : 'var(--text-secondary)',
            borderBottom: activeTab === 'audit' ? '2px solid var(--accent)' : '2px solid transparent',
            padding: '8px 16px',
            fontWeight: 500,
            fontSize: '14px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px'
          }}
        >
          <ClipboardList size={16} />
          Administrative Audit Logs
        </button>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '28px' }}>
        
        {/* TAB 1: ACADEMICS & FACULTY */}
        {activeTab === 'academics' && (
          <>
            {/* CHART ROW */}
            <div className="card">
              <div className="card-header" style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <BarChart3 size={18} className="text-accent" />
                <h3 className="card-title">Enrollment Distribution Per Section</h3>
              </div>
              <div className="card-body" style={{ minHeight: '320px', padding: '20px' }}>
                {studentsPerSec.length > 0 ? (
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={studentsPerSec} margin={{ top: 10, right: 10, left: -20, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                      <XAxis dataKey="section" stroke="var(--text-muted)" fontSize={12} tickLine={false} />
                      <YAxis stroke="var(--text-muted)" fontSize={12} tickLine={false} />
                      <Tooltip
                        contentStyle={{
                          background: 'var(--bg-secondary)',
                          borderColor: 'var(--border)',
                          borderRadius: '8px',
                          color: 'var(--text-primary)',
                        }}
                      />
                      <Bar dataKey="enrolled" radius={[4, 4, 0, 0]}>
                        {studentsPerSec.map((entry, index) => (
                          <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="empty-state">
                    <Users size={32} className="text-muted" style={{ margin: '0 auto 12px' }} />
                    <h3>No active sections</h3>
                    <p>Register sections and enroll students to generate size distributions.</p>
                  </div>
                )}
              </div>
            </div>

            {/* WORKLOAD TABLE ROW */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '0 4px' }}>
                <BookOpen size={18} className="text-accent" />
                <h3 className="card-title" style={{ fontSize: '18px', fontWeight: 600 }}>Faculty Workload Summary</h3>
              </div>
              <DataTable
                headers={teacherHeaders}
                data={teachersSummary}
                searchKeys={['name', 'employee_id', 'department']}
                searchPlaceholder="Filter instructors..."
                renderRow={(teacher) => (
                  <>
                    <td><span className="badge badge-accent">{teacher.employee_id}</span></td>
                    <td>{teacher.name}</td>
                    <td>{teacher.department}</td>
                    <td>
                      <span className={`badge ${teacher.sections_count > 0 ? 'badge-info' : 'badge-warning'}`}>
                        {teacher.sections_count} Sections
                      </span>
                    </td>
                    <td>
                      <span className={`badge ${teacher.is_active ? 'badge-success' : 'badge-danger'}`}>
                        {teacher.is_active ? 'Active' : 'Inactive'}
                      </span>
                    </td>
                  </>
                )}
              />
            </div>
          </>
        )}

        {/* TAB 2: DEPARTMENT PERFORMANCE KPIs */}
        {activeTab === 'departments' && (
          <>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '20px' }}>
              {deptKpis.map(dept => (
                <div key={dept.department_id} className="card">
                  <div className="card-body" style={{ padding: '20px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
                      <div>
                        <span className="badge badge-accent" style={{ marginBottom: '4px' }}>{dept.code}</span>
                        <h4 style={{ fontSize: '16px', fontWeight: 700 }}>{dept.name}</h4>
                        <span style={{ fontSize: '12px', color: 'var(--text-secondary)' }}>HOD: {dept.hod_name}</span>
                      </div>
                    </div>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px', marginTop: '16px' }}>
                      <div style={{ background: 'rgba(255,255,255,0.02)', padding: '10px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)' }}>
                        <span style={{ fontSize: '11px', color: 'var(--text-secondary)', display: 'block' }}>Students Enrolled</span>
                        <span style={{ fontSize: '18px', fontWeight: 700 }}>{dept.total_students}</span>
                      </div>
                      <div style={{ background: 'rgba(255,255,255,0.02)', padding: '10px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)' }}>
                        <span style={{ fontSize: '11px', color: 'var(--text-secondary)', display: 'block' }}>Faculty Members</span>
                        <span style={{ fontSize: '18px', fontWeight: 700 }}>{dept.total_teachers}</span>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>

            <div className="card">
              <div className="card-header">
                <h3 className="card-title">Comparative Performance Analysis</h3>
              </div>
              <div className="card-body" style={{ minHeight: '340px', padding: '20px' }}>
                {deptKpis.length > 0 ? (
                  <ResponsiveContainer width="100%" height={320}>
                    <BarChart data={deptKpis} margin={{ top: 10, right: 10, left: -20, bottom: 5 }}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" />
                      <XAxis dataKey="code" stroke="var(--text-muted)" fontSize={12} tickLine={false} />
                      <YAxis stroke="var(--text-muted)" fontSize={12} tickLine={false} domain={[0, 100]} />
                      <Tooltip
                        contentStyle={{
                          background: 'var(--bg-secondary)',
                          borderColor: 'var(--border)',
                          borderRadius: '8px',
                          color: 'var(--text-primary)',
                        }}
                      />
                      <Legend verticalAlign="top" height={36} wrapperStyle={{ fontSize: '12px' }} />
                      <Bar name="Average Attendance (%)" dataKey="average_attendance" fill="var(--info)" radius={[4, 4, 0, 0]} />
                      <Bar name="Quiz Mastery (%)" dataKey="average_quiz_success" fill="var(--success)" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                ) : (
                  <p style={{ textAlign: 'center', color: 'var(--text-muted)' }}>No departments available to display performance metrics.</p>
                )}
              </div>
            </div>
          </>
        )}

        {/* TAB 3: ADMIN AUDIT LOGS */}
        {activeTab === 'audit' && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '0 4px' }}>
              <ShieldAlert size={18} className="text-accent" />
              <h3 className="card-title" style={{ fontSize: '18px', fontWeight: 600 }}>Administrative Activity Log Trail</h3>
            </div>
            <DataTable
              headers={auditHeaders}
              data={auditLogs}
              searchKeys={['user_name', 'action', 'details']}
              searchPlaceholder="Search audit logs..."
              renderRow={(log) => (
                <>
                  <td style={{ fontSize: '12px', color: 'var(--text-secondary)', whiteSpace: 'nowrap' }}>
                    {new Date(log.timestamp).toLocaleString()}
                  </td>
                  <td style={{ fontWeight: 500 }}>{log.user_name}</td>
                  <td>
                    <span className={`badge ${getActionBadgeClass(log.action)}`} style={{ fontSize: '10px' }}>
                      {log.action}
                    </span>
                  </td>
                  <td style={{ fontSize: '13px', color: 'var(--text-secondary)', maxWidth: '400px', wordBreak: 'break-word' }}>
                    {log.details}
                  </td>
                </>
              )}
            />
          </div>
        )}

      </div>
    </div>
  );
}
