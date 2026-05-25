import { useState, useEffect } from 'react';
import { teacherPortalApi } from '../../services/api';
import { BarChart3, AlertTriangle, Users, Award, FileText, ChevronDown, ChevronRight, CheckCircle, HelpCircle } from 'lucide-react';
import toast from 'react-hot-toast';

export default function TeacherAnalyticsPage() {
  const [sections, setSections] = useState([]);
  const [selectedSection, setSelectedSection] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadingAnalytics, setLoadingAnalytics] = useState(false);

  // Student details toggle
  const [expandedStudentId, setExpandedStudentId] = useState(null);

  const fetchSections = async () => {
    try {
      const res = await teacherPortalApi.sections();
      setSections(res.data);
      if (res.data.length > 0) {
        setSelectedSection(res.data[0]);
      }
    } catch (err) {
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
    } catch (err) {
      toast.error('Failed to load class analytics.');
    } finally {
      setLoadingAnalytics(false);
    }
  };

  useEffect(() => {
    fetchSections();
  }, []);

  useEffect(() => {
    if (selectedSection) {
      fetchSectionAnalytics(selectedSection.id);
    }
  }, [selectedSection]);

  const toggleStudentDetails = (id) => {
    setExpandedStudentId(prev => (prev === id ? null : id));
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center" style={{ minHeight: '60vh' }}>
        <div className="loading" style={{ fontSize: '18px' }}>Loading Analytics Panel...</div>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      
      {/* Top Selector Panel */}
      <div className="card" style={{ padding: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
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
        </div>
      </div>

      {loadingAnalytics || !analytics ? (
        <div className="card flex items-center justify-center" style={{ minHeight: '40vh', padding: '32px' }}>
          <div className="loading" style={{ color: 'var(--text-secondary)' }}>Calculating analytics data...</div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '28px' }}>
          
          {/* Class-Level Stats Summary */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '20px' }}>
            
            <div className="stat-card" style={{ '--card-color': 'var(--accent)' }}>
              <div className="stat-card-icon" style={{ background: 'var(--accent-glow)', color: 'var(--accent-light)' }}>
                <Award size={22} />
              </div>
              <div className="stat-card-value">{analytics.class_avg_mastery}%</div>
              <div className="stat-card-label">Class Avg Mastery</div>
            </div>

            <div className="stat-card" style={{ '--card-color': 'var(--success)' }}>
              <div className="stat-card-icon" style={{ background: 'rgba(16,185,129,0.15)', color: 'var(--success)' }}>
                <CheckCircle size={22} />
              </div>
              <div className="stat-card-value">{analytics.class_avg_attendance}%</div>
              <div className="stat-card-label">Class Attendance Rate</div>
            </div>

            <div className="stat-card" style={{ '--card-color': 'var(--danger)' }}>
              <div className="stat-card-icon" style={{ background: 'rgba(239,68,68,0.15)', color: 'var(--danger)' }}>
                <AlertTriangle size={22} />
              </div>
              <div className="stat-card-value">{analytics.at_risk_students.length}</div>
              <div className="stat-card-label">At-Risk Students</div>
            </div>

            <div className="stat-card" style={{ '--card-color': 'var(--info)' }}>
              <div className="stat-card-icon" style={{ background: 'rgba(59,130,246,0.15)', color: 'var(--info)' }}>
                <Users size={22} />
              </div>
              <div className="stat-card-value">{analytics.total_enrolled}</div>
              <div className="stat-card-label">Total Students Enrolled</div>
            </div>

          </div>

          {/* Double split box: Topic Difficulty + Risk distribution */}
          <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '28px' }}>
            
            {/* Topic Difficulties */}
            <div className="card" style={{ padding: '20px' }}>
              <h3 className="card-title" style={{ fontSize: '15px', marginBottom: '16px', borderBottom: '1px solid var(--border)', paddingBottom: '10px' }}>
                Topic Mastery & Difficulties
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
                {analytics.topic_difficulty.map((t, idx) => (
                  <div key={idx} className="flex justify-between items-center" style={{ background: 'rgba(255,255,255,0.01)', padding: '10px 14px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)' }}>
                    <div>
                      <h4 style={{ fontSize: '13px', fontWeight: '700', color: 'var(--text-primary)' }}>{t.topic_title}</h4>
                      <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Class Average Mastery: {t.average_score}%</span>
                    </div>
                    <span className={`badge ${
                      t.difficulty === 'Easy' ? 'badge-success' : (t.difficulty === 'Medium' ? 'badge-warning' : 'badge-danger')
                    }`}>
                      {t.difficulty}
                    </span>
                  </div>
                ))}
              </div>
            </div>

            {/* At Risk & High Performers lists */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
              <div className="card" style={{ padding: '16px', borderLeft: '3px solid var(--danger)' }}>
                <h4 style={{ fontSize: '13px', fontWeight: '700', color: 'var(--danger)', marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <AlertTriangle size={15} /> At-Risk Students (&lt;50% Score)
                </h4>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                  {analytics.at_risk_students.length === 0 ? (
                    <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>None - all students are on track.</span>
                  ) : (
                    analytics.at_risk_students.map((st, idx) => (
                      <span key={idx} className="badge badge-danger" style={{ textTransform: 'none' }}>
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

          {/* Student Progress List */}
          <div className="card">
            <div className="card-header">
              <h3 className="card-title">Student Performance List</h3>
            </div>
            <div className="card-body" style={{ padding: 0 }}>
              <div className="table-wrapper">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th style={{ width: '40px' }}></th>
                      <th>Student Name</th>
                      <th>Reg. ID</th>
                      <th>Quiz Mastery</th>
                      <th>Attendance Rate</th>
                      <th>Watch Ratio</th>
                      <th>Engagement</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {analytics.students.map((s) => {
                      const isExpanded = expandedStudentId === s.student_id;
                      return (
                        <>
                          <tr 
                            key={s.student_id} 
                            onClick={() => toggleStudentDetails(s.student_id)}
                            style={{ cursor: 'pointer' }}
                          >
                            <td>{isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}</td>
                            <td>{s.name}</td>
                            <td>{s.reg_number}</td>
                            <td>{s.overall_mastery}%</td>
                            <td>{s.attendance_rate}%</td>
                            <td>{s.avg_watch_pct}%</td>
                            <td>{s.avg_engagement}%</td>
                            <td>
                              <span className={`badge ${s.status === 'On track' ? 'badge-success' : 'badge-danger'}`}>
                                {s.status}
                              </span>
                            </td>
                          </tr>

                          {/* Student Details Expanded Pane */}
                          {isExpanded && (
                            <tr style={{ background: 'rgba(255,255,255,0.01)' }}>
                              <td colSpan={8} style={{ padding: '20px 32px' }}>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                                  
                                  <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '32px' }}>
                                    {/* Left: Topic-wise masteries */}
                                    <div>
                                      <h5 style={{ fontSize: '13px', fontWeight: '700', color: 'var(--text-secondary)', marginBottom: '10px' }}>
                                        Topic Mastery Breakdown
                                      </h5>
                                      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                                        {s.topic_mastery.map((tm, idx) => (
                                          <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', fontSize: '13px' }}>
                                            <span>{tm.topic_title}</span>
                                            <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                                              <span style={{ fontWeight: 'bold' }}>{tm.score}%</span>
                                              <span className={`badge ${
                                                tm.rating === 'strong' ? 'badge-success' : (tm.rating === 'working' ? 'badge-warning' : 'badge-danger')
                                              }`} style={{ fontSize: '9px', padding: '1px 6px' }}>
                                                {tm.rating}
                                              </span>
                                            </div>
                                          </div>
                                        ))}
                                      </div>
                                    </div>

                                    {/* Right: Recommended action */}
                                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                                      <div className="card" style={{ padding: '16px', background: 'var(--bg-primary)', borderLeft: '3px solid var(--accent)' }}>
                                        <h5 style={{ fontSize: '12px', fontWeight: '700', textTransform: 'uppercase', color: 'var(--accent-light)', marginBottom: '6px' }}>
                                          💡 AI Recommended Action
                                        </h5>
                                        <p style={{ fontSize: '13px', color: 'var(--text-primary)', lineHeight: '1.4' }}>
                                          {s.recommended_action}
                                        </p>
                                      </div>

                                      {/* Action button */}
                                      <button 
                                        className="btn btn-secondary btn-sm"
                                        onClick={(e) => {
                                          e.stopPropagation();
                                          toast.success(`Message template prepared for ${s.name}: "${s.recommended_action}"`);
                                        }}
                                        style={{ alignSelf: 'flex-start' }}
                                      >
                                        Contact Student
                                      </button>
                                    </div>
                                  </div>

                                  {/* Detailed Watch History */}
                                  <div style={{ borderTop: '1px solid var(--border)', paddingTop: '16px', marginTop: '10px' }}>
                                    <h5 style={{ fontSize: '13px', fontWeight: '700', color: 'var(--text-secondary)', marginBottom: '12px' }}>
                                      Detailed Lecture Watch History
                                    </h5>
                                    {!s.watch_history || s.watch_history.length === 0 ? (
                                      <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>No lectures watched yet.</p>
                                    ) : (
                                      <div className="table-wrapper">
                                        <table className="data-table" style={{ background: 'transparent' }}>
                                          <thead>
                                            <tr>
                                              <th>Lecture Title</th>
                                              <th>Watch %</th>
                                              <th>Pause Count</th>
                                              <th>Playback Speed</th>
                                              <th>Engagement Score</th>
                                              <th>Status</th>
                                              <th>Started At</th>
                                            </tr>
                                          </thead>
                                          <tbody>
                                            {s.watch_history.map((wh, wIdx) => (
                                              <tr key={wIdx}>
                                                <td style={{ fontSize: '12px' }}>{wh.lecture_title}</td>
                                                <td style={{ fontSize: '12px' }}>{wh.watch_percentage}%</td>
                                                <td style={{ fontSize: '12px' }}>{wh.pause_count}</td>
                                                <td style={{ fontSize: '12px' }}>{wh.playback_speed}x</td>
                                                <td style={{ fontSize: '12px' }}>{wh.engagement_score}%</td>
                                                <td style={{ fontSize: '12px' }}>
                                                  <span className={`badge ${wh.is_complete ? 'badge-success' : 'badge-warning'}`}>
                                                    {wh.is_complete ? 'Complete' : 'Incomplete'}
                                                  </span>
                                                </td>
                                                <td style={{ fontSize: '12px' }}>
                                                  {wh.started_at ? new Date(wh.started_at).toLocaleString() : 'N/A'}
                                                </td>
                                              </tr>
                                            ))}
                                          </tbody>
                                        </table>
                                      </div>
                                    )}
                                  </div>

                                </div>
                              </td>
                            </tr>
                          )}
                        </>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

        </div>
      )}

    </div>
  );
}
