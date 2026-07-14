import { useState, useEffect } from 'react';
import { enrollmentApi, sectionApi, teacherApi } from '../services/api';
import DataTable from '../components/DataTable';
import Modal from '../components/Modal';
import { 
  Trash2, 
  AlertCircle, 
  Filter, 
  Check, 
  X, 
  RefreshCw,
  UserCheck,
  Grid,
  List,
  BookOpen,
  Users,
  ChevronLeft,
  ArrowRight,
  Edit2
} from 'lucide-react';
import { toast } from 'react-hot-toast';

export default function EnrollmentsPage() {
  const [enrollments, setEnrollments] = useState([]);
  const [sections, setSections] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // View state
  const [viewMode, setViewMode] = useState('SECTIONS'); // 'SECTIONS' | 'ALL'
  const [selectedSection, setSelectedSection] = useState(null);

  // Edit Teacher State
  const [teachers, setTeachers] = useState([]);
  const [editModalOpen, setEditModalOpen] = useState(false);
  const [editTeacherId, setEditTeacherId] = useState('');
  const [savingTeacher, setSavingTeacher] = useState(false);

  // Filters state (only used in ALL mode)
  const [selectedCourseFilter, setSelectedCourseFilter] = useState('');
  const [selectedSectionFilter, setSelectedSectionFilter] = useState('');
  const [selectedStatusFilter, setSelectedStatusFilter] = useState('ACTIVE'); // Default to ACTIVE

  const fetchData = async () => {
    setLoading(true);
    setError('');
    try {
      const [eRes, sRes, tRes] = await Promise.all([
        enrollmentApi.list(),
        sectionApi.list(),
        teacherApi.list()
      ]);
      setEnrollments(eRes.data);
      setSections(sRes.data);
      const activeTeachers = tRes.data.filter(t => t.is_active);
      setTeachers(activeTeachers);
    } catch (err) {
      console.error(err);
      setError('Failed to load enrollments data. Please check your connection.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleDeactivate = async (id, name, courseCode, sectionLabel) => {
    if (!window.confirm(`Are you sure you want to drop student ${name} from course section ${courseCode} - ${sectionLabel}?`)) return;
    try {
      await enrollmentApi.deactivate(id);
      toast.success('Student dropped from course section successfully');
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to drop student.');
    }
  };

  const handleApproveStatus = async (id, name) => {
    try {
      await enrollmentApi.updateStatus(id, 'ACTIVE');
      toast.success(`Enrollment for ${name} approved and activated.`);
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to approve enrollment.');
    }
  };

  const handleUpdateTeacher = async (e) => {
    e.preventDefault();
    if (!selectedSection) return;
    setSavingTeacher(true);
    try {
      const payload = {
        teacher_id: editTeacherId ? parseInt(editTeacherId, 10) : null
      };
      const response = await sectionApi.update(selectedSection.id, payload);
      toast.success('Instructor updated successfully');
      setSelectedSection(response.data);
      setEditModalOpen(false);
      fetchData();
    } catch (err) {
      console.error(err);
      toast.error(err.response?.data?.detail || 'Failed to update instructor.');
    } finally {
      setSavingTeacher(false);
    }
  };

  // Dynamic filter lists for global ALL view
  const uniqueCourses = [...new Set(enrollments.map(e => e.course_name))].filter(Boolean);
  const uniqueSections = [...new Set(enrollments.map(e => e.section_label))].filter(Boolean);

  // Filter global list
  const filteredEnrollments = enrollments.filter(e => {
    const courseMatch = selectedCourseFilter ? e.course_name === selectedCourseFilter : true;
    const sectionMatch = selectedSectionFilter ? e.section_label === selectedSectionFilter : true;
    
    let statusMatch = true;
    if (selectedStatusFilter !== 'ALL') {
      statusMatch = e.status === selectedStatusFilter;
    }
    return courseMatch && sectionMatch && statusMatch;
  });

  const headers = [
    { key: 'student_reg', label: 'Registration No' },
    { key: 'student_name', label: 'Student Name' },
    { key: 'course_name', label: 'Course' },
    { key: 'credit_hours', label: 'Credits' },
    { key: 'section_label', label: 'Section' },
    { key: 'teacher_name', label: 'Instructor' },
    { key: 'semester_name', label: 'Semester' },
    { key: 'status', label: 'Status' },
    { key: 'enrolled_at', label: 'Date Joined', sortable: false },
    { key: 'actions', label: 'Actions', sortable: false },
  ];

  // Specific section headers (removes course & section info as they are in the header card)
  const sectionRosterHeaders = [
    { key: 'student_reg', label: 'Registration No' },
    { key: 'student_name', label: 'Student Name' },
    { key: 'semester_name', label: 'Semester' },
    { key: 'status', label: 'Status' },
    { key: 'enrolled_at', label: 'Date Joined', sortable: false },
    { key: 'actions', label: 'Actions', sortable: false },
  ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      
      {/* Page Header */}
      <div className="page-header" style={{ marginBottom: 0, display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <h1 className="page-title">Enrolled Students Directory</h1>
          <p className="page-subtitle">Track, filter, and manage student rosters grouped by sections or globally.</p>
        </div>
        
        {/* View Switcher segment control */}
        <div style={{
          display: 'flex',
          background: 'rgba(0,0,0,0.03)',
          padding: '4px',
          borderRadius: 'var(--radius-md)',
          border: '1px solid var(--border)'
        }}>
          <button
            onClick={() => { setViewMode('SECTIONS'); setSelectedSection(null); }}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '8px 16px',
              borderRadius: '6px',
              border: 'none',
              background: viewMode === 'SECTIONS' ? 'var(--accent)' : 'transparent',
              color: viewMode === 'SECTIONS' ? '#fff' : 'var(--text-secondary)',
              cursor: 'pointer',
              fontSize: '13px',
              fontWeight: 600,
              transition: 'all 0.2s'
            }}
          >
            <Grid size={15} />
            <span>Grouped by Sections</span>
          </button>
          <button
            onClick={() => setViewMode('ALL')}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              padding: '8px 16px',
              borderRadius: '6px',
              border: 'none',
              background: viewMode === 'ALL' ? 'var(--accent)' : 'transparent',
              color: viewMode === 'ALL' ? '#fff' : 'var(--text-secondary)',
              cursor: 'pointer',
              fontSize: '13px',
              fontWeight: 600,
              transition: 'all 0.2s'
            }}
          >
            <List size={15} />
            <span>All Enrollments List</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="result-box error" style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <AlertCircle size={20} />
          <span>{error}</span>
        </div>
      )}

      {loading ? (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '40vh', gap: '12px' }}>
          <RefreshCw size={32} className="spin text-accent" />
          <span style={{ color: 'var(--text-secondary)', fontSize: '14px' }}>Loading student directory...</span>
        </div>
      ) : (
        <>
          {/* ─── GROUPED BY SECTIONS VIEW ─── */}
          {viewMode === 'SECTIONS' && !selectedSection && (
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
              gap: '24px'
            }}>
              {sections.length === 0 ? (
                <div style={{
                  gridColumn: '1 / -1',
                  background: 'var(--bg-secondary)',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--radius-xl)',
                  padding: '48px',
                  textAlign: 'center',
                  color: 'var(--text-secondary)'
                }}>
                  No active course offerings found to show rosters.
                </div>
              ) : (
                sections.map(sec => {
                  const secEnrollments = enrollments.filter(e => e.section_id === sec.id);
                  const activeCount = secEnrollments.filter(e => e.status === 'ACTIVE').length;
                  const pendingCount = secEnrollments.filter(e => e.status === 'PENDING').length;

                  return (
                    <div 
                      key={sec.id}
                      onClick={() => setSelectedSection(sec)}
                      style={{
                        background: 'var(--bg-secondary)',
                        border: '1px solid var(--border)',
                        borderRadius: 'var(--radius-lg)',
                        padding: '24px',
                        cursor: 'pointer',
                        display: 'flex',
                        flexDirection: 'column',
                        justifyContent: 'space-between',
                        gap: '16px',
                        transition: 'transform 0.2s, border-color 0.2s',
                        boxShadow: 'var(--shadow-sm)'
                      }}
                      className="section-card"
                      onMouseEnter={e => {
                        e.currentTarget.style.transform = 'translateY(-2px)';
                        e.currentTarget.style.borderColor = 'var(--accent)';
                      }}
                      onMouseLeave={e => {
                        e.currentTarget.style.transform = 'none';
                        e.currentTarget.style.borderColor = 'var(--border)';
                      }}
                    >
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                          <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--accent-light)', background: 'rgba(13,148,136,0.1)', padding: '4px 8px', borderRadius: '4px', textTransform: 'uppercase' }}>
                            {sec.course_code}
                          </span>
                          
                          {sec.target_student_reg ? (
                            <span className="badge" style={{ fontSize: '10px', fontWeight: 700, background: 'rgba(245, 158, 11, 0.08)', color: 'var(--warning)', border: 'none' }}>
                              Single Student
                            </span>
                          ) : (
                            <span className="badge badge-accent" style={{ fontSize: '10px', fontWeight: 700 }}>
                              {sec.academic_section_label || 'Class-wide'}
                            </span>
                          )}
                        </div>
                        <h3 style={{ fontSize: '16px', fontWeight: 700, margin: '4px 0 0 0', lineHeight: '1.3' }}>
                          {sec.course_name}
                        </h3>
                        <p style={{ fontSize: '12px', color: 'var(--text-secondary)', margin: 0 }}>
                          Section Label: <strong>{sec.section_label}</strong> • Instructor: <strong>{sec.teacher_name || 'TBA'}</strong>
                        </p>
                      </div>

                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderTop: '1px solid var(--border)', paddingTop: '16px', marginTop: '8px' }}>
                        <div style={{ display: 'flex', gap: '12px' }}>
                          <div style={{ display: 'flex', flexDirection: 'column' }}>
                            <span style={{ fontSize: '10px', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Enrolled</span>
                            <span style={{ fontSize: '16px', fontWeight: 800, color: 'var(--success)' }}>{activeCount}</span>
                          </div>
                          {pendingCount > 0 && (
                            <div style={{ display: 'flex', flexDirection: 'column' }}>
                              <span style={{ fontSize: '10px', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>Pending</span>
                              <span style={{ fontSize: '16px', fontWeight: 800, color: 'var(--warning)' }}>{pendingCount}</span>
                            </div>
                          )}
                        </div>
                        
                        <div style={{ color: 'var(--accent-light)', display: 'flex', alignItems: 'center', gap: '4px', fontSize: '12px', fontWeight: 600 }}>
                          <span>Open Roster</span>
                          <ArrowRight size={14} />
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          )}

          {/* ─── GROUPED SECTION ROSTER DETAILED VIEW ─── */}
          {viewMode === 'SECTIONS' && selectedSection && (
            <div>
              <button
                onClick={() => setSelectedSection(null)}
                className="btn btn-secondary"
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  marginBottom: '16px',
                  padding: '8px 14px',
                  borderRadius: 'var(--radius-md)'
                }}
              >
                <ChevronLeft size={16} />
                <span>Back to Sections</span>
              </button>
              
              <div style={{
                background: 'linear-gradient(135deg, var(--bg-secondary) 0%, rgba(13, 148, 136, 0.05) 100%)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-lg)',
                padding: '24px 28px',
                marginBottom: '24px',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                boxShadow: 'var(--shadow-sm)',
                flexWrap: 'wrap',
                gap: '16px'
              }}>
                <div>
                  <span className="badge badge-accent" style={{ marginBottom: '8px', fontSize: '11px', display: 'inline-block' }}>
                    {selectedSection.course_code}
                  </span>
                  <h2 style={{ fontSize: '20px', fontWeight: 800, margin: 0 }}>
                    Roster: {selectedSection.course_name}
                  </h2>
                  <p style={{ fontSize: '13px', color: 'var(--text-secondary)', margin: '6px 0 0 0', display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: '6px' }}>
                    <span>Section: <strong>{selectedSection.section_label}</strong></span>
                    <span>•</span>
                    <span>Instructor:</span>
                    <span 
                      style={{ 
                        display: 'inline-flex', 
                        alignItems: 'center', 
                        gap: '6px', 
                        background: 'rgba(13, 148, 136, 0.08)', 
                        padding: '2px 8px', 
                        borderRadius: '6px', 
                        border: '1px solid rgba(13, 148, 136, 0.15)'
                      }}
                    >
                      <strong style={{ color: 'var(--accent-light)' }}>{selectedSection.teacher_name || 'TBA'}</strong>
                      <button
                        onClick={() => {
                          setEditTeacherId(selectedSection.teacher_id || '');
                          setEditModalOpen(true);
                        }}
                        style={{
                          background: 'none',
                          border: 'none',
                          cursor: 'pointer',
                          color: 'var(--accent-light)',
                          display: 'inline-flex',
                          alignItems: 'center',
                          padding: '2px',
                          borderRadius: '4px',
                          transition: 'all 0.2s',
                        }}
                        title="Change Instructor"
                        onMouseEnter={(e) => e.currentTarget.style.color = 'var(--accent)'}
                        onMouseLeave={(e) => e.currentTarget.style.color = 'var(--accent-light)'}
                      >
                        <Edit2 size={13} />
                      </button>
                    </span>
                    <span>•</span>
                    <span>Target: <strong>{selectedSection.target_student_reg ? `Single Student (${selectedSection.target_student_reg})` : (selectedSection.academic_section_label || 'All Sections')}</strong></span>
                  </p>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <span style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-secondary)', display: 'block', fontWeight: 600 }}>Total Enrolled</span>
                  <span style={{ fontSize: '24px', fontWeight: 800, color: 'var(--success)' }}>
                    {enrollments.filter(e => e.section_id === selectedSection.id && e.status === 'ACTIVE').length} Students
                  </span>
                </div>
              </div>

              {/* DataTable for this Section */}
              <div style={{
                background: 'var(--bg-secondary)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-lg)',
                overflow: 'hidden'
              }}>
                <DataTable
                  headers={sectionRosterHeaders}
                  data={enrollments.filter(e => e.section_id === selectedSection.id)}
                  searchKeys={['student_name', 'student_reg']}
                  searchPlaceholder="Search students in this roster..."
                  renderRow={(e) => {
                    let statusBg = 'rgba(0,0,0,0.05)';
                    let statusColor = 'var(--text-secondary)';
                    if (e.status === 'ACTIVE') {
                      statusBg = 'rgba(16,185,129,0.1)';
                      statusColor = 'var(--success)';
                    } else if (e.status === 'PENDING') {
                      statusBg = 'rgba(245,158,11,0.08)';
                      statusColor = 'var(--warning)';
                    } else if (e.status === 'DROPPED') {
                      statusBg = 'rgba(239,68,68,0.1)';
                      statusColor = 'var(--danger)';
                    }

                    return (
                      <>
                        <td><span className="badge badge-accent" style={{ fontWeight: 700 }}>{e.student_reg}</span></td>
                        <td style={{ fontWeight: 500 }}>{e.student_name}</td>
                        <td>{e.semester_name || <span className="text-muted">-</span>}</td>
                        <td>
                          <span 
                            className="badge" 
                            style={{ 
                              background: statusBg, 
                              color: statusColor, 
                              border: 'none', 
                              fontWeight: 700, 
                              fontSize: '11px',
                              textTransform: 'uppercase'
                            }}
                          >
                            {e.status}
                          </span>
                        </td>
                        <td style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>{new Date(e.enrolled_at).toLocaleDateString()}</td>
                        <td>
                          <div style={{ display: 'flex', gap: '8px' }}>
                            {e.status === 'PENDING' && (
                              <button
                                className="btn btn-success btn-sm btn-icon"
                                onClick={() => handleApproveStatus(e.id, e.student_name)}
                                title="Approve Enrollment"
                                style={{ background: 'var(--success)', color: '#fff', border: 'none', borderRadius: '6px', width: '28px', height: '28px' }}
                              >
                                <Check size={14} />
                              </button>
                            )}
                            
                            {e.status === 'DROPPED' && (
                              <button
                                className="btn btn-success btn-sm btn-icon"
                                onClick={() => handleApproveStatus(e.id, e.student_name)}
                                title="Reactivate Student"
                                style={{ background: 'rgba(16,185,129,0.1)', color: 'var(--success)', border: '1px solid rgba(16,185,129,0.2)', borderRadius: '6px', width: '28px', height: '28px' }}
                              >
                                <UserCheck size={14} />
                              </button>
                            )}

                            {e.status !== 'DROPPED' && (
                              <button
                                className="btn btn-danger btn-sm btn-icon"
                                onClick={() => handleDeactivate(e.id, e.student_name, e.course_name, e.section_label)}
                                title="Drop Student"
                                style={{ borderRadius: '6px', width: '28px', height: '28px' }}
                              >
                                <Trash2 size={14} />
                              </button>
                            )}
                          </div>
                        </td>
                      </>
                    );
                  }}
                />
              </div>
            </div>
          )}

          {/* ─── GLOBAL FLAT LIST VIEW (ALL mode) ─── */}
          {viewMode === 'ALL' && (
            <>
              {/* Filters Card */}
              <div style={{
                background: 'var(--bg-secondary)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-lg)',
                padding: '20px 24px',
                boxShadow: 'var(--shadow-sm)'
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px', color: 'var(--accent-light)' }}>
                  <Filter size={18} />
                  <h3 style={{ fontSize: '14px', fontWeight: 700, margin: 0, textTransform: 'uppercase', letterSpacing: '0.05em' }}>Filter Roster</h3>
                </div>

                <div style={{ display: 'flex', gap: '20px', flexWrap: 'wrap' }}>
                  {/* Course filter */}
                  <div className="form-group" style={{ flex: '1', minWidth: '200px', margin: 0 }}>
                    <label className="form-label" style={{ fontSize: '11px', textTransform: 'uppercase', marginBottom: '6px' }}>Filter by Course</label>
                    <select
                      className="form-control"
                      value={selectedCourseFilter}
                      onChange={(e) => setSelectedCourseFilter(e.target.value)}
                    >
                      <option value="">All Courses</option>
                      {uniqueCourses.map(course => (
                        <option key={course} value={course}>{course}</option>
                      ))}
                    </select>
                  </div>

                  {/* Section filter */}
                  <div className="form-group" style={{ flex: '1', minWidth: '150px', margin: 0 }}>
                    <label className="form-label" style={{ fontSize: '11px', textTransform: 'uppercase', marginBottom: '6px' }}>Filter by Section</label>
                    <select
                      className="form-control"
                      value={selectedSectionFilter}
                      onChange={(e) => setSelectedSectionFilter(e.target.value)}
                    >
                      <option value="">All Sections</option>
                      {uniqueSections.map(sec => (
                        <option key={sec} value={sec}>{sec}</option>
                      ))}
                    </select>
                  </div>

                  {/* Status filter */}
                  <div className="form-group" style={{ flex: '1', minWidth: '150px', margin: 0 }}>
                    <label className="form-label" style={{ fontSize: '11px', textTransform: 'uppercase', marginBottom: '6px' }}>Filter by Status</label>
                    <select
                      className="form-control"
                      value={selectedStatusFilter}
                      onChange={(e) => setSelectedStatusFilter(e.target.value)}
                    >
                      <option value="ALL">All States</option>
                      <option value="ACTIVE">Active (Confirmed)</option>
                      <option value="PENDING">Pending (Self-Registered)</option>
                      <option value="DROPPED">Dropped (Inactive)</option>
                    </select>
                  </div>
                </div>
              </div>

              {/* Table */}
              <div style={{
                background: 'var(--bg-secondary)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-lg)',
                overflow: 'hidden'
              }}>
                <DataTable
                  headers={headers}
                  data={filteredEnrollments}
                  searchKeys={['student_name', 'student_reg', 'course_name', 'section_label', 'teacher_name']}
                  searchPlaceholder="Search by reg number, student name, instructor..."
                  renderRow={(e) => {
                    let statusBg = 'rgba(0,0,0,0.05)';
                    let statusColor = 'var(--text-secondary)';
                    if (e.status === 'ACTIVE') {
                      statusBg = 'rgba(16,185,129,0.1)';
                      statusColor = 'var(--success)';
                    } else if (e.status === 'PENDING') {
                      statusBg = 'rgba(245,158,11,0.08)';
                      statusColor = 'var(--warning)';
                    } else if (e.status === 'DROPPED') {
                      statusBg = 'rgba(239,68,68,0.1)';
                      statusColor = 'var(--danger)';
                    }

                    return (
                      <>
                        <td><span className="badge badge-accent" style={{ fontWeight: 700 }}>{e.student_reg}</span></td>
                        <td style={{ fontWeight: 500 }}>{e.student_name}</td>
                        <td>
                          <div style={{ display: 'flex', flexDirection: 'column' }}>
                            <span style={{ fontWeight: 500 }}>{e.course_name}</span>
                            <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>{e.course_code}</span>
                          </div>
                        </td>
                        <td><span className="badge badge-secondary">{e.credit_hours} Cr</span></td>
                        <td><span className="badge badge-info">{e.section_label}</span></td>
                        <td>{e.teacher_name || <span className="text-muted" style={{ fontStyle: 'italic' }}>TBA</span>}</td>
                        <td>{e.semester_name || <span className="text-muted">-</span>}</td>
                        <td>
                          <span 
                            className="badge" 
                            style={{ 
                              background: statusBg, 
                              color: statusColor, 
                              border: 'none', 
                              fontWeight: 700, 
                              fontSize: '11px',
                              textTransform: 'uppercase'
                            }}
                          >
                            {e.status}
                          </span>
                        </td>
                        <td style={{ fontSize: '13px', color: 'var(--text-secondary)' }}>{new Date(e.enrolled_at).toLocaleDateString()}</td>
                        <td>
                          <div style={{ display: 'flex', gap: '8px' }}>
                            {e.status === 'PENDING' && (
                              <button
                                className="btn btn-success btn-sm btn-icon"
                                onClick={() => handleApproveStatus(e.id, e.student_name)}
                                title="Approve Enrollment"
                                style={{ background: 'var(--success)', color: '#fff', border: 'none', borderRadius: '6px', width: '28px', height: '28px' }}
                              >
                                <Check size={14} />
                              </button>
                            )}
                            
                            {e.status === 'DROPPED' && (
                              <button
                                className="btn btn-success btn-sm btn-icon"
                                onClick={() => handleApproveStatus(e.id, e.student_name)}
                                title="Reactivate Student"
                                style={{ background: 'rgba(16,185,129,0.1)', color: 'var(--success)', border: '1px solid rgba(16,185,129,0.2)', borderRadius: '6px', width: '28px', height: '28px' }}
                              >
                                <UserCheck size={14} />
                              </button>
                            )}

                            {e.status !== 'DROPPED' && (
                              <button
                                className="btn btn-danger btn-sm btn-icon"
                                onClick={() => handleDeactivate(e.id, e.student_name, e.course_name, e.section_label)}
                                title="Drop Student"
                                style={{ borderRadius: '6px', width: '28px', height: '28px' }}
                              >
                                <Trash2 size={14} />
                              </button>
                            )}
                          </div>
                        </td>
                      </>
                    );
                  }}
                />
              </div>
            </>
          )}
        </>
      )}
      {/* Edit Teacher Modal */}
      <Modal
        isOpen={editModalOpen}
        onClose={() => setEditModalOpen(false)}
        title="Assign Instructor"
        footer={
          <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end', width: '100%' }}>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setEditModalOpen(false)}
              disabled={savingTeacher}
            >
              Cancel
            </button>
            <button
              type="submit"
              form="edit-teacher-form"
              className="btn btn-primary"
              disabled={savingTeacher}
            >
              {savingTeacher ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        }
      >
        <form id="edit-teacher-form" onSubmit={handleUpdateTeacher}>
          <div className="form-group" style={{ marginBottom: 0 }}>
            <label className="form-label" style={{ display: 'block', marginBottom: '8px', fontWeight: 600 }}>
              Select Instructor for {selectedSection?.course_name} ({selectedSection?.section_label})
            </label>
            <select
              className="form-control"
              value={editTeacherId}
              onChange={(e) => setEditTeacherId(e.target.value)}
              style={{ width: '100%', padding: '10px 12px', borderRadius: 'var(--radius-md)' }}
            >
              <option value="">Unassigned (N/A / TBA)</option>
              {teachers.map((teacher) => (
                <option key={teacher.id} value={teacher.id}>
                  {teacher.full_name} {teacher.department_name ? `(${teacher.department_name})` : ''}
                </option>
              ))}
            </select>
            <p style={{ fontSize: '12px', color: 'var(--text-secondary)', marginTop: '8px', lineHeight: '1.4' }}>
              Assigning a new instructor will update the class roster owner. Setting it to "Unassigned" will clear the instructor and display TBA, without deleting any enrolled students or course resources.
            </p>
          </div>
        </form>
      </Modal>

    </div>
  );
}
