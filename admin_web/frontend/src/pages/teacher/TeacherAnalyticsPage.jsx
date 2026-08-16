import { useState, useEffect } from 'react';
import { teacherPortalApi } from '../../services/api';
import {
  BarChart3, AlertTriangle, Users, Award, FileText,
  ChevronDown, ChevronRight, CheckCircle, Brain, Zap,
  Eye, Target, TrendingUp, X, BookOpen
} from 'lucide-react';
import toast from 'react-hot-toast';

/* ── Small Progress Bar ─────────────────────────────────────────── */
function MiniBar({ value, max = 100, color = 'var(--accent)' }) {
  const pct = Math.min(100, Math.max(0, (value / max) * 100));
  return (
    <div style={{ background: 'var(--bg-input)', borderRadius: 99, height: 6, width: '100%' }}>
      <div style={{
        background: color, borderRadius: 99, height: 6,
        width: `${pct}%`, transition: 'width 0.6s ease'
      }} />
    </div>
  );
}

/* ── Radar Chart (CSS polygon) ───────────────────────────────────── */
function RadarChart({ data }) {
  // data: [{label, value (0-100)}] — exactly 5 items
  const cx = 80, cy = 80, r = 60;
  const n = data.length;
  const angles = data.map((_, i) => (i * 360) / n - 90);
  const toXY = (angle, radius) => ({
    x: cx + radius * Math.cos((angle * Math.PI) / 180),
    y: cy + radius * Math.sin((angle * Math.PI) / 180),
  });
  const bgPoints = angles.map(a => toXY(a, r));
  const dataPoints = data.map((d, i) => toXY(angles[i], (d.value / 100) * r));
  const toStr = pts => pts.map(p => `${p.x},${p.y}`).join(' ');

  return (
    <svg width={160} height={160} viewBox="0 0 160 160">
      {[0.25, 0.5, 0.75, 1].map((f, fi) => (
        <polygon key={fi}
          points={toStr(angles.map(a => toXY(a, r * f)))}
          fill="none" stroke="var(--border)" strokeWidth={0.8} opacity={0.5}
        />
      ))}
      {bgPoints.map((p, i) => (
        <line key={i} x1={cx} y1={cy} x2={p.x} y2={p.y}
          stroke="var(--border)" strokeWidth={0.8} opacity={0.4}
        />
      ))}
      <polygon
        points={toStr(dataPoints)}
        fill="var(--accent)" fillOpacity={0.18}
        stroke="var(--accent-light)" strokeWidth={2}
      />
      {dataPoints.map((p, i) => (
        <circle key={i} cx={p.x} cy={p.y} r={4}
          fill="var(--accent-light)" stroke="var(--bg-primary)" strokeWidth={1.5}
        />
      ))}
      {data.map((d, i) => {
        const lp = toXY(angles[i], r + 18);
        return (
          <text key={i} x={lp.x} y={lp.y} textAnchor="middle"
            fontSize={9} fill="var(--text-secondary)"
            dominantBaseline="middle">
            {d.label}
          </text>
        );
      })}
    </svg>
  );
}

/* ── Per-Student Profile Drawer ─────────────────────────────────── */
function StudentProfileDrawer({ student, onClose }) {
  if (!student) return null;

  const radarData = [
    { label: 'Mastery', value: student.overall_mastery ?? 0 },
    { label: 'Confidence', value: student.confidence_score ?? 0 },
    { label: 'Engagement', value: student.avg_engagement ?? 0 },
    { label: 'Attendance', value: student.attendance_rate ?? 0 },
    { label: 'Assignment', value: student.assignment_mastery ?? 0 },
  ];

  const mastColor = v =>
    v >= 75 ? 'var(--success)' : v >= 50 ? '#f59e0b' : 'var(--danger)';

  return (
    <div style={{
      position: 'fixed', top: 0, right: 0, width: 480, height: '100vh',
      background: 'var(--bg-secondary)', borderLeft: '1px solid var(--border)',
      zIndex: 1000, overflowY: 'auto', padding: '24px',
      display: 'flex', flexDirection: 'column', gap: 20,
      boxShadow: '-8px 0 32px rgba(0,0,0,0.4)',
      animation: 'slideInRight 0.25s ease'
    }}>
      <style>{`@keyframes slideInRight { from { transform: translateX(100%); } to { transform: translateX(0); } }`}</style>

      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h2 style={{ fontSize: 18, fontWeight: 800, color: 'var(--text-primary)', margin: 0 }}>
            {student.name}
          </h2>
          <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>
            {student.reg_number} &nbsp;·&nbsp;
            <span className={`badge ${student.status === 'At risk' ? 'badge-danger' : 'badge-success'}`}>
              {student.status}
            </span>
          </p>
        </div>
        <button onClick={onClose} className="btn btn-secondary btn-sm"
          style={{ borderRadius: 99, width: 32, height: 32, padding: 0 }}>
          <X size={14} />
        </button>
      </div>

      {/* Radar chart + quick stats */}
      <div style={{ display: 'flex', gap: 20, alignItems: 'center' }}>
        <RadarChart data={radarData} />
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 12 }}>
          {[
            { label: 'Learning Score', value: `${student.learning_score ?? 0}%`, color: 'var(--accent-light)' },
            { label: 'Quiz Mastery', value: `${student.overall_mastery}%`, color: mastColor(student.overall_mastery) },
            { label: 'Assignment Mastery', value: `${student.assignment_mastery ?? 0}%`, color: mastColor(student.assignment_mastery ?? 0) },
            { label: 'Confidence', value: `${student.confidence_score ?? 0}%`, color: mastColor(student.confidence_score ?? 0) },
            { label: 'Hint Usage', value: `${student.hint_dependency_pct ?? 0}%`, color: (student.hint_dependency_pct ?? 0) > 40 ? 'var(--danger)' : 'var(--success)' },
          ].map((row, i) => (
            <div key={i}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 4 }}>
                <span style={{ color: 'var(--text-secondary)' }}>{row.label}</span>
                <span style={{ fontWeight: 700, color: row.color }}>{row.value}</span>
              </div>
              <MiniBar value={parseFloat(row.value)} color={row.color} />
            </div>
          ))}
        </div>
      </div>

      {/* AI Recommended Action */}
      <div className="card" style={{ padding: 16, borderLeft: '3px solid var(--accent)', background: 'var(--bg-input)' }}>
        <h5 style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', color: 'var(--accent-light)', marginBottom: 8 }}>
          💡 AI Recommended Action
        </h5>
        <p style={{ fontSize: 13, color: 'var(--text-primary)', lineHeight: 1.5, margin: 0 }}>
          {student.recommended_action}
        </p>
      </div>

      {/* Topic Mastery Breakdown */}
      <div>
        <h4 style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-secondary)', marginBottom: 12 }}>
          Topic Mastery Breakdown
        </h4>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {(student.topic_mastery ?? []).map((tm, i) => (
            <div key={i}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, marginBottom: 4 }}>
                <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{tm.topic_title}</span>
                <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
                  <span style={{ fontWeight: 700, color: mastColor(tm.score) }}>{tm.score}%</span>
                  <span className={`badge ${tm.rating === 'strong' ? 'badge-success' : tm.rating === 'working' ? 'badge-warning' : 'badge-danger'}`}
                    style={{ fontSize: 9, padding: '1px 6px' }}>
                    {tm.rating}
                  </span>
                </div>
              </div>
              <MiniBar value={tm.score} color={mastColor(tm.score)} />
            </div>
          ))}
        </div>
      </div>

      {/* Watch History */}
      {student.watch_history?.length > 0 && (
        <div>
          <h4 style={{ fontSize: 13, fontWeight: 700, color: 'var(--text-secondary)', marginBottom: 12 }}>
            Lecture Watch History
          </h4>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {student.watch_history.map((wh, i) => (
              <div key={i} className="card" style={{ padding: '10px 14px', background: 'var(--bg-input)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary)' }}>{wh.lecture_title}</span>
                  <span className={`badge ${wh.is_complete ? 'badge-success' : 'badge-warning'}`} style={{ fontSize: 9 }}>
                    {wh.is_complete ? 'Complete' : 'Partial'}
                  </span>
                </div>
                <div style={{ display: 'flex', gap: 16, fontSize: 11, color: 'var(--text-muted)' }}>
                  <span>Watch: <strong style={{ color: 'var(--text-primary)' }}>{wh.watch_percentage}%</strong></span>
                  <span>Pauses: <strong style={{ color: 'var(--text-primary)' }}>{wh.pause_count}</strong></span>
                  <span>Speed: <strong style={{ color: 'var(--text-primary)' }}>{wh.playback_speed}x</strong></span>
                  <span>Engagement: <strong style={{ color: mastColor(wh.engagement_score) }}>{wh.engagement_score}%</strong></span>
                </div>
                <MiniBar value={wh.watch_percentage} color="var(--info)" />
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/* ── Topic Heatmap ───────────────────────────────────────────────── */
function TopicHeatmap({ heatmapData }) {
  if (!heatmapData || heatmapData.length === 0) return null;

  const cellColor = (m) =>
    m >= 75 ? 'rgba(16,185,129,0.75)' : m >= 50 ? 'rgba(245,158,11,0.75)' : 'rgba(239,68,68,0.75)';

  const students = heatmapData[0]?.students ?? [];

  return (
    <div className="card">
      <div className="card-header">
        <h3 className="card-title">
          <Target size={16} style={{ marginRight: 8, color: 'var(--accent-light)' }} />
          Topic × Student Mastery Heatmap
        </h3>
        <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>
          🟢 ≥75% Proficient &nbsp; 🟡 50–74% Developing &nbsp; 🔴 &lt;50% Struggling
        </p>
      </div>
      <div className="card-body" style={{ padding: 0, overflowX: 'auto' }}>
        <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 12 }}>
          <thead>
            <tr>
              <th style={{ padding: '10px 16px', textAlign: 'left', color: 'var(--text-secondary)', background: 'var(--bg-input)', borderBottom: '1px solid var(--border)', whiteSpace: 'nowrap', width: 160 }}>
                Topic / Student
              </th>
              {students.map((s, i) => (
                <th key={i} style={{
                  padding: '8px 6px', textAlign: 'center', fontSize: 11,
                  color: 'var(--text-secondary)', background: 'var(--bg-input)',
                  borderBottom: '1px solid var(--border)', maxWidth: 80,
                  whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis'
                }}>
                  {s.name.split(' ')[0]}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {heatmapData.map((row, ri) => (
              <tr key={ri}>
                <td style={{
                  padding: '10px 16px', fontWeight: 600, color: 'var(--text-primary)',
                  borderBottom: '1px solid var(--border)', background: 'var(--bg-input)',
                  whiteSpace: 'nowrap', maxWidth: 160, overflow: 'hidden', textOverflow: 'ellipsis'
                }}>
                  {row.topic_title}
                </td>
                {row.students.map((s, si) => (
                  <td key={si} style={{
                    padding: '8px 6px', textAlign: 'center',
                    borderBottom: '1px solid var(--border)'
                  }}>
                    <div style={{
                      margin: '0 auto', width: 44, height: 28, borderRadius: 6,
                      background: cellColor(s.mastery),
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontSize: 11, fontWeight: 700, color: '#fff',
                    }}>
                      {s.mastery}%
                    </div>
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/* ── Main Page ───────────────────────────────────────────────────── */
export default function TeacherAnalyticsPage() {
  const [sections, setSections] = useState([]);
  const [selectedSection, setSelectedSection] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadingAnalytics, setLoadingAnalytics] = useState(false);
  const [selectedStudent, setSelectedStudent] = useState(null);
  const [activeTab, setActiveTab] = useState('overview'); // 'overview' | 'heatmap' | 'students'

  const fetchSections = async () => {
    try {
      const res = await teacherPortalApi.sections();
      setSections(res.data);
      if (res.data.length > 0) setSelectedSection(res.data[0]);
    } catch {
      toast.error('Failed to load courses.');
    } finally {
      setLoading(false);
    }
  };

  const fetchSectionAnalytics = async (sectId) => {
    setLoadingAnalytics(true);
    try {
      const res = await teacherPortalApi.getSectionAnalytics(sectId);
      setAnalytics(res.data);
    } catch {
      toast.error('Failed to load class analytics.');
    } finally {
      setLoadingAnalytics(false);
    }
  };

  useEffect(() => { fetchSections(); }, []);
  useEffect(() => {
    if (selectedSection) fetchSectionAnalytics(selectedSection.id);
  }, [selectedSection]);

  const mastColor = v =>
    v >= 75 ? 'var(--success)' : v >= 50 ? '#f59e0b' : 'var(--danger)';

  if (loading) return (
    <div className="flex items-center justify-center" style={{ minHeight: '60vh' }}>
      <div className="loading" style={{ fontSize: '18px' }}>Loading Analytics Panel...</div>
    </div>
  );

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>

      {/* Overlay dim when drawer open */}
      {selectedStudent && (
        <div onClick={() => setSelectedStudent(null)} style={{
          position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', zIndex: 999
        }} />
      )}

      <StudentProfileDrawer student={selectedStudent} onClose={() => setSelectedStudent(null)} />

      {/* Top Selector */}
      <div className="card" style={{ padding: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
          <span className="form-label" style={{ margin: 0, fontWeight: '600' }}>Select Course Section:</span>
          <select
            className="form-control"
            style={{ width: '280px', background: 'var(--bg-primary)' }}
            value={selectedSection ? selectedSection.id : ''}
            onChange={(e) => {
              const sec = sections.find(s => s.id === parseInt(e.target.value));
              setSelectedSection(sec);
            }}
          >
            {sections.map(s => (
              <option key={s.id} value={s.id}>
                {s.course_code} - {s.course_name} (Sec {s.section_label})
              </option>
            ))}
          </select>

          {/* Tabs */}
          <div style={{ marginLeft: 'auto', display: 'flex', gap: 8 }}>
            {[
              { key: 'overview', label: 'Overview', icon: BarChart3 },
              { key: 'heatmap', label: 'Heatmap', icon: Target },
              { key: 'students', label: 'Student List', icon: Users },
            ].map(({ key, label, icon: Icon }) => (
              <button key={key}
                className={`btn btn-sm ${activeTab === key ? 'btn-primary' : 'btn-secondary'}`}
                onClick={() => setActiveTab(key)}
                style={{ display: 'flex', alignItems: 'center', gap: 6 }}
              >
                <Icon size={14} /> {label}
              </button>
            ))}
          </div>
        </div>
      </div>

      {loadingAnalytics || !analytics ? (
        <div className="card flex items-center justify-center" style={{ minHeight: '40vh', padding: '32px' }}>
          <div className="loading" style={{ color: 'var(--text-secondary)' }}>Calculating analytics data...</div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '28px' }}>

          {/* ── TAB: Overview ─────────────────────────────────────── */}
          {activeTab === 'overview' && (
            <>
              {/* Class-Level Stats */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '20px' }}>
                {[
                  { icon: Award, label: 'Class Avg Mastery', value: `${analytics.class_avg_mastery}%`, color: 'var(--accent)', glow: 'var(--accent-glow)' },
                  { icon: CheckCircle, label: 'Class Attendance', value: `${analytics.class_avg_attendance}%`, color: 'var(--success)', glow: 'rgba(16,185,129,0.15)' },
                  { icon: AlertTriangle, label: 'At-Risk Students', value: analytics.at_risk_students.length, color: 'var(--danger)', glow: 'rgba(239,68,68,0.15)' },
                  { icon: Users, label: 'Total Enrolled', value: analytics.total_enrolled, color: 'var(--info)', glow: 'rgba(59,130,246,0.15)' },
                  { icon: Brain, label: 'High Performers', value: analytics.high_performers.length, color: '#a78bfa', glow: 'rgba(167,139,250,0.15)' },
                ].map((card, i) => (
                  <div key={i} className="stat-card" style={{ '--card-color': card.color }}>
                    <div className="stat-card-icon" style={{ background: card.glow, color: card.color }}>
                      <card.icon size={22} />
                    </div>
                    <div className="stat-card-value">{card.value}</div>
                    <div className="stat-card-label">{card.label}</div>
                  </div>
                ))}
              </div>

              {/* Topic Difficulty + At-Risk / High Performers */}
              <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '28px' }}>
                <div className="card" style={{ padding: '20px' }}>
                  <h3 className="card-title" style={{ fontSize: '15px', marginBottom: '16px', borderBottom: '1px solid var(--border)', paddingBottom: '10px' }}>
                    Topic Mastery & Difficulties
                  </h3>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                    {analytics.topic_difficulty.map((t, idx) => (
                      <div key={idx}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                          <div>
                            <h4 style={{ fontSize: '13px', fontWeight: '700', color: 'var(--text-primary)', margin: 0 }}>{t.topic_title}</h4>
                            <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Class Avg: {t.average_score}%</span>
                          </div>
                          <span className={`badge ${t.difficulty === 'Easy' ? 'badge-success' : t.difficulty === 'Medium' ? 'badge-warning' : 'badge-danger'}`}>
                            {t.difficulty}
                          </span>
                        </div>
                        <MiniBar value={t.average_score} color={mastColor(t.average_score)} />
                      </div>
                    ))}
                  </div>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                  <div className="card" style={{ padding: '16px', borderLeft: '3px solid var(--danger)' }}>
                    <h4 style={{ fontSize: '13px', fontWeight: '700', color: 'var(--danger)', marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <AlertTriangle size={15} /> At-Risk Students (&lt;50% Score)
                    </h4>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                      {analytics.at_risk_students.length === 0 ? (
                        <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>None — all students are on track.</span>
                      ) : (
                        analytics.at_risk_students.map((st, idx) => (
                          <span key={idx} className="badge badge-danger" style={{ textTransform: 'none', cursor: 'pointer' }}
                            onClick={() => { setSelectedStudent(analytics.students.find(s => s.name === st.name)); setActiveTab('students'); }}>
                            {st.name} ({st.score}%)
                          </span>
                        ))
                      )}
                    </div>
                  </div>
                  <div className="card" style={{ padding: '16px', borderLeft: '3px solid var(--success)' }}>
                    <h4 style={{ fontSize: '13px', fontWeight: '700', color: 'var(--success)', marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                      <Award size={15} /> High Performers (&gt;85% Score)
                    </h4>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                      {analytics.high_performers.length === 0 ? (
                        <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>None yet.</span>
                      ) : (
                        analytics.high_performers.map((st, idx) => (
                          <span key={idx} className="badge badge-success" style={{ textTransform: 'none' }}>
                            {st.name} ({st.score}%)
                          </span>
                        ))
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </>
          )}

          {/* ── TAB: Heatmap ──────────────────────────────────────── */}
          {activeTab === 'heatmap' && (
            <TopicHeatmap heatmapData={analytics.topic_heatmap} />
          )}

          {/* ── TAB: Student List ──────────────────────────────────── */}
          {activeTab === 'students' && (
            <div className="card">
              <div className="card-header">
                <h3 className="card-title">Student Performance — Full Learning Dashboard</h3>
                <p style={{ fontSize: 12, color: 'var(--text-muted)', marginTop: 4 }}>
                  Click any row to open the detailed learning profile drawer.
                </p>
              </div>
              <div className="card-body" style={{ padding: 0 }}>
                <div className="table-wrapper">
                  <table className="data-table">
                    <thead>
                      <tr>
                        <th>Student</th>
                        <th>Quiz Mastery</th>
                        <th>Assignment</th>
                        <th>Learning Score</th>
                        <th>Confidence</th>
                        <th>Hint Usage</th>
                        <th>Attendance</th>
                        <th>Engagement</th>
                        <th>Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {analytics.students.map((s) => (
                        <tr key={s.student_id}
                          onClick={() => setSelectedStudent(s)}
                          style={{ cursor: 'pointer', transition: 'background 0.15s' }}
                          onMouseEnter={e => e.currentTarget.style.background = 'var(--bg-input)'}
                          onMouseLeave={e => e.currentTarget.style.background = ''}
                        >
                          <td>
                            <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{s.name}</div>
                            <div style={{ fontSize: 11, color: 'var(--text-muted)' }}>{s.reg_number}</div>
                          </td>
                          <td>
                            <div style={{ fontWeight: 700, color: mastColor(s.overall_mastery) }}>{s.overall_mastery}%</div>
                            <MiniBar value={s.overall_mastery} color={mastColor(s.overall_mastery)} />
                          </td>
                          <td>
                            <div style={{ fontWeight: 700, color: mastColor(s.assignment_mastery ?? 0) }}>{s.assignment_mastery ?? 0}%</div>
                            <MiniBar value={s.assignment_mastery ?? 0} color={mastColor(s.assignment_mastery ?? 0)} />
                          </td>
                          <td>
                            <div style={{ fontWeight: 700, color: 'var(--accent-light)' }}>{s.learning_score ?? 0}%</div>
                            <MiniBar value={s.learning_score ?? 0} color="var(--accent-light)" />
                          </td>
                          <td>
                            <div style={{ fontWeight: 700, color: mastColor(s.confidence_score ?? 0) }}>{s.confidence_score ?? 0}%</div>
                          </td>
                          <td>
                            <span style={{
                              fontWeight: 700, fontSize: 12,
                              color: (s.hint_dependency_pct ?? 0) > 40 ? 'var(--danger)' : 'var(--success)'
                            }}>
                              {s.hint_dependency_pct ?? 0}%
                            </span>
                          </td>
                          <td style={{ fontWeight: 600 }}>{s.attendance_rate}%</td>
                          <td style={{ fontWeight: 600 }}>{s.avg_engagement}%</td>
                          <td>
                            <span className={`badge ${s.status === 'On track' ? 'badge-success' : 'badge-danger'}`}>
                              {s.status}
                            </span>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

        </div>
      )}
    </div>
  );
}
