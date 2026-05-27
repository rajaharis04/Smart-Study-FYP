import { useState, useEffect } from 'react';
import { 
  semesterApi, 
  sectionApi, 
  courseApi, 
  teacherApi, 
  academicSectionApi,
  enrollmentApi 
} from '../services/api';
import { 
  Calendar, 
  AlertCircle, 
  Save, 
  BookOpen, 
  Layers, 
  CheckCircle, 
  Clock, 
  Loader2, 
  Plus, 
  Trash2, 
  CheckSquare, 
  Sparkles, 
  User, 
  X,
  Play,
  EyeOff
} from 'lucide-react';
import { toast } from 'react-hot-toast';

export default function RegistrationWeekPage() {
  const [activeSemester, setActiveSemester] = useState(null);
  const [sections, setSections] = useState([]);
  const [courses, setCourses] = useState([]);
  const [teachers, setTeachers] = useState([]);
  const [academicSections, setAcademicSections] = useState([]);
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  // Modals state
  const [isOfferModalOpen, setIsOfferModalOpen] = useState(false);
  const [isDeadlineModalOpen, setIsDeadlineModalOpen] = useState(false);
  const [submittingOffer, setSubmittingOffer] = useState(false);
  const [savingDeadline, setSavingDeadline] = useState(false);
  const [finalizing, setFinalizing] = useState(false);
  const [togglingSectionId, setTogglingSectionId] = useState(null);
  const [deletingSectionId, setDeletingSectionId] = useState(null);

  // Form states
  const [selectedCourseId, setSelectedCourseId] = useState('');
  const [selectedAcademicSectionId, setSelectedAcademicSectionId] = useState('');
  const [selectedTeacherId, setSelectedTeacherId] = useState('');
  const [customSectionLabel, setCustomSectionLabel] = useState('');
  const [deadlineInput, setDeadlineInput] = useState('');
  const [targetType, setTargetType] = useState('BATCH'); // 'BATCH' | 'STUDENT'
  const [targetStudentReg, setTargetStudentReg] = useState('');

  // Countdown state
  const [timeLeft, setTimeLeft] = useState('');

  const fetchData = async () => {
    setLoading(true);
    setError('');
    try {
      // 1. Fetch active semester
      const semRes = await semesterApi.active();
      const sem = semRes.data;
      setActiveSemester(sem);
      
      if (sem.registration_deadline) {
        const d = new Date(sem.registration_deadline);
        const pad = (num) => String(num).padStart(2, '0');
        const formatted = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
        setDeadlineInput(formatted);
      } else {
        setDeadlineInput('');
      }

      // 2. Fetch data in parallel
      const [sectionsRes, coursesRes, teachersRes, acSectionsRes] = await Promise.all([
        sectionApi.list(),
        courseApi.list(),
        teacherApi.list(),
        academicSectionApi.listFlat()
      ]);

      // Filter sections by active semester
      const filteredSections = sectionsRes.data.filter(s => s.semester_id === sem.id);
      setSections(filteredSections);
      setCourses(coursesRes.data);
      setTeachers(teachersRes.data);
      setAcademicSections(acSectionsRes.data);
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || 'Failed to load registration setup. Please check if active semester is set.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  // Countdown timer calculation
  useEffect(() => {
    if (!activeSemester?.registration_deadline || !activeSemester?.server_time) {
      setTimeLeft('');
      return;
    }

    const initialDiff = new Date(activeSemester.registration_deadline) - new Date(activeSemester.server_time);
    const loadedAt = Date.now();

    const updateTimer = () => {
      const elapsed = Date.now() - loadedAt;
      const diff = initialDiff - elapsed;

      if (diff <= 0) {
        setTimeLeft('Deadline Passed');
      } else {
        const days = Math.floor(diff / (1000 * 60 * 60 * 24));
        const hours = Math.floor((diff / (1000 * 60 * 60)) % 24);
        const minutes = Math.floor((diff / 1000 / 60) % 60);
        const seconds = Math.floor((diff / 1000) % 60);
        
        let display = '';
        if (days > 0) display += `${days}d `;
        display += `${hours}h ${minutes}m ${seconds}s`;
        setTimeLeft(display);
      }
    };

    updateTimer();
    const interval = setInterval(updateTimer, 1000);
    return () => clearInterval(interval);
  }, [activeSemester?.registration_deadline, activeSemester?.server_time]);

  // Sync section label when academic section changes
  useEffect(() => {
    if (selectedAcademicSectionId) {
      const selectedSec = academicSections.find(as => as.id === parseInt(selectedAcademicSectionId));
      if (selectedSec) {
        setCustomSectionLabel(selectedSec.section_name || '');
      }
    }
  }, [selectedAcademicSectionId, academicSections]);

  const handleSaveDeadline = async (e) => {
    e.preventDefault();
    if (!activeSemester) return;

    setSavingDeadline(true);
    try {
      let isoDeadline = null;
      if (deadlineInput) {
        const [datePart, timePart] = deadlineInput.split('T');
        const [year, month, day] = datePart.split('-').map(Number);
        const [hours, minutes] = timePart.split(':').map(Number);
        isoDeadline = new Date(year, month - 1, day, hours, minutes).toISOString();
      }

      const payload = {
        registration_deadline: isoDeadline
      };
      await semesterApi.update(activeSemester.id, payload);
      toast.success('Registration deadline updated');
      
      const semRes = await semesterApi.active();
      setActiveSemester(semRes.data);
      setIsDeadlineModalOpen(false);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to update deadline.');
    } finally {
      setSavingDeadline(false);
    }
  };

  const handleToggleRegistration = async (section) => {
    setTogglingSectionId(section.id);
    try {
      const newStatus = !section.is_registration_open;
      await sectionApi.update(section.id, {
        is_registration_open: newStatus
      });
      
      setSections(prev => prev.map(s => s.id === section.id ? { ...s, is_registration_open: newStatus } : s));
      toast.success(`Course offering is now ${newStatus ? 'LIVE' : 'HIDDEN'}`);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to toggle registration.');
    } finally {
      setTogglingSectionId(null);
    }
  };

  const handleDeleteSection = async (sectionId) => {
    if (!window.confirm('Are you sure you want to remove this course offering? This will also remove any students registered in it.')) {
      return;
    }
    setDeletingSectionId(sectionId);
    try {
      await sectionApi.delete(sectionId);
      setSections(prev => prev.filter(s => s.id !== sectionId));
      toast.success('Course offering removed');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to delete section.');
    } finally {
      setDeletingSectionId(null);
    }
  };

  const handleOfferCourse = async (e) => {
    e.preventDefault();
    if (!selectedCourseId || !customSectionLabel) {
      toast.error('Please fill in all required fields');
      return;
    }
    if (targetType === 'BATCH' && !selectedAcademicSectionId) {
      toast.error('Please select a target academic section');
      return;
    }
    if (targetType === 'STUDENT' && !targetStudentReg) {
      toast.error('Please enter a target student registration number');
      return;
    }

    setSubmittingOffer(true);
    try {
      const payload = {
        course_id: parseInt(selectedCourseId),
        academic_section_id: targetType === 'BATCH' ? parseInt(selectedAcademicSectionId) : null,
        target_student_reg: targetType === 'STUDENT' ? targetStudentReg.trim() : null,
        teacher_id: selectedTeacherId ? parseInt(selectedTeacherId) : null,
        section_label: customSectionLabel,
        semester_id: activeSemester.id,
        schedule: null,
        room: null,
        is_registration_open: false // Default to false/hidden
      };

      await sectionApi.create(payload);
      toast.success('Course offered successfully!');
      
      // Reset form & close
      setSelectedCourseId('');
      setSelectedAcademicSectionId('');
      setSelectedTeacherId('');
      setCustomSectionLabel('');
      setTargetType('BATCH');
      setTargetStudentReg('');
      setIsOfferModalOpen(false);

      // Refresh list
      const sectionsRes = await sectionApi.list();
      const filteredSections = sectionsRes.data.filter(s => s.semester_id === activeSemester.id);
      setSections(filteredSections);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to offer course.');
    } finally {
      setSubmittingOffer(false);
    }
  };

  const handleFinalizeRegistrations = async () => {
    if (!window.confirm('Are you sure you want to finalize all pending student registrations? This will convert all PENDING registrations to ACTIVE.')) {
      return;
    }
    setFinalizing(true);
    try {
      const res = await enrollmentApi.finalize();
      toast.success(res.data?.message || 'Registrations finalized successfully!');
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to finalize registrations.');
    } finally {
      setFinalizing(false);
    }
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '50vh', gap: '16px' }}>
        <Loader2 size={40} className="spin text-accent" />
        <span style={{ color: 'var(--text-secondary)', fontWeight: 500 }}>Loading registration dashboard...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="result-box error" style={{ display: 'flex', alignItems: 'center', gap: '12px', padding: '20px', borderRadius: 'var(--radius-lg)' }}>
        <AlertCircle size={24} />
        <div>
          <h4 style={{ margin: 0, fontWeight: 600 }}>Configuration Error</h4>
          <span style={{ fontSize: '14px', color: 'rgba(255,255,255,0.7)' }}>{error}</span>
        </div>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '28px' }}>
      
      {/* ─── Top Control Panel ─── */}
      <div style={{
        background: 'linear-gradient(135deg, var(--bg-secondary) 0%, rgba(99, 102, 241, 0.07) 100%)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius-xl)',
        padding: '24px 32px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '24px',
        boxShadow: 'var(--shadow-md)'
      }}>
        <div style={{ display: 'flex', gap: '20px', alignItems: 'center' }}>
          <div style={{
            background: 'rgba(99, 102, 241, 0.15)',
            color: 'var(--accent-light)',
            width: '56px',
            height: '56px',
            borderRadius: '16px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 8px 16px rgba(99, 102, 241, 0.1)'
          }}>
            <Calendar size={28} />
          </div>
          <div>
            <h2 style={{ fontSize: '20px', fontWeight: 800, margin: 0, letterSpacing: '-0.02em' }}>
              Registration Week: <span className="text-accent" style={{ color: 'var(--accent-light)' }}>{activeSemester?.name}</span>
            </h2>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)', margin: '6px 0 0 0' }}>
              Offer courses to academic sections, manage visibility, and control deadlines.
            </p>
          </div>
        </div>

        {/* Info & Badges */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px', flexWrap: 'wrap' }}>
          {activeSemester?.registration_deadline ? (
            <div style={{
              background: timeLeft === 'Deadline Passed' ? 'rgba(239, 68, 68, 0.1)' : 'rgba(245, 158, 11, 0.08)',
              border: `1px solid ${timeLeft === 'Deadline Passed' ? 'rgba(239, 68, 68, 0.2)' : 'rgba(245, 158, 11, 0.2)'}`,
              borderRadius: 'var(--radius-md)',
              padding: '10px 18px',
              display: 'flex',
              flexDirection: 'column',
              gap: '2px',
              minWidth: '180px'
            }}>
              <span style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-secondary)', fontWeight: 600, letterSpacing: '0.05em' }}>
                Time Remaining
              </span>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '14px', fontWeight: 700, color: timeLeft === 'Deadline Passed' ? 'var(--danger)' : 'var(--warning)' }}>
                <Clock size={15} />
                <span>{timeLeft}</span>
              </div>
            </div>
          ) : (
            <div style={{
              background: 'rgba(239, 68, 68, 0.08)',
              border: '1px solid rgba(239, 68, 68, 0.2)',
              borderRadius: 'var(--radius-md)',
              padding: '10px 18px',
              display: 'flex',
              flexDirection: 'column',
              gap: '2px',
              minWidth: '180px'
            }}>
              <span style={{ fontSize: '11px', textTransform: 'uppercase', color: 'var(--text-secondary)', fontWeight: 600, letterSpacing: '0.05em' }}>
                Registration Status
              </span>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '14px', fontWeight: 700, color: 'var(--danger)' }}>
                <AlertCircle size={15} />
                <span>No Deadline Configured</span>
              </div>
            </div>
          )}

          {/* Quick Actions */}
          <div style={{ display: 'flex', gap: '10px' }}>
            <button 
              className="btn btn-secondary"
              onClick={() => setIsDeadlineModalOpen(true)}
              style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '10px 16px', borderRadius: 'var(--radius-md)' }}
            >
              <Clock size={16} />
              <span>Set Deadline</span>
            </button>

            <button 
              className="btn btn-success"
              onClick={handleFinalizeRegistrations}
              disabled={finalizing}
              style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '10px 16px', borderRadius: 'var(--radius-md)' }}
            >
              {finalizing ? (
                <Loader2 size={16} className="spin" />
              ) : (
                <CheckSquare size={16} />
              )}
              <span>Finalize</span>
            </button>

            <button 
              className="btn btn-primary"
              onClick={() => setIsOfferModalOpen(true)}
              style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '10px 18px', borderRadius: 'var(--radius-md)' }}
            >
              <Plus size={18} />
              <span>Offer Course</span>
            </button>
          </div>
        </div>
      </div>

      {/* ─── Main Content Body ─── */}
      {sections.length === 0 || timeLeft === 'Deadline Passed' ? (
        /* Empty State / Closed State */
        <div style={{
          background: 'var(--bg-secondary)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--radius-xl)',
          padding: '60px 40px',
          textAlign: 'center',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '24px',
          boxShadow: 'var(--shadow-md)'
        }}>
          <div style={{
            width: '80px',
            height: '80px',
            borderRadius: '50%',
            background: timeLeft === 'Deadline Passed' ? 'rgba(239, 68, 68, 0.05)' : 'rgba(99, 102, 241, 0.05)',
            border: timeLeft === 'Deadline Passed' ? '2px dashed rgba(239, 68, 68, 0.3)' : '2px dashed rgba(99, 102, 241, 0.3)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: timeLeft === 'Deadline Passed' ? 'var(--danger)' : 'var(--accent-light)',
            marginBottom: '8px'
          }}>
            {timeLeft === 'Deadline Passed' ? <Clock size={40} /> : <Sparkles size={40} />}
          </div>
          <div>
            <h3 style={{ fontSize: '20px', fontWeight: 700, margin: '0 0 8px 0', color: timeLeft === 'Deadline Passed' ? 'var(--danger)' : 'inherit' }}>
              {timeLeft === 'Deadline Passed' ? 'Registration Period Closed' : 'No Courses Offered Yet'}
            </h3>
            <p style={{ color: 'var(--text-secondary)', maxWidth: '460px', margin: 0, fontSize: '14px', lineHeight: 1.5 }}>
              {timeLeft === 'Deadline Passed'
                ? 'The registration deadline has passed. All student course offerings have closed and pending registrations are finalized.'
                : 'Offer courses to academic sections (e.g., SP23-BCS-A) so students can view and self-register for them through their mobile app.'}
            </p>
          </div>
          {timeLeft !== 'Deadline Passed' && (
            <button 
              className="btn btn-primary" 
              onClick={() => setIsOfferModalOpen(true)}
              style={{ 
                padding: '12px 24px', 
                fontSize: '15px', 
                fontWeight: 600, 
                display: 'flex', 
                alignItems: 'center', 
                gap: '10px',
                borderRadius: 'var(--radius-lg)'
              }}
            >
              <Plus size={18} />
              <span>Start Offering Course</span>
            </button>
          )}
        </div>
      ) : (
        /* Offered Courses Grid */
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3 style={{ fontSize: '16px', fontWeight: 700, margin: 0 }}>Currently Offered Courses ({sections.length})</h3>
          </div>

          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))',
            gap: '24px'
          }}>
            {sections.map((sec) => (
              <div 
                key={sec.id}
                style={{
                  background: 'var(--bg-secondary)',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--radius-lg)',
                  display: 'flex',
                  flexDirection: 'column',
                  transition: 'transform var(--transition), border-color var(--transition)',
                  position: 'relative',
                  overflow: 'hidden'
                }}
                className="section-card"
              >
                {/* Status Bar Indicator */}
                <div style={{
                  height: '4px',
                  background: sec.is_registration_open ? 'var(--success)' : 'var(--text-muted)',
                  width: '100%'
                }} />

                {/* Card Header */}
                <div style={{ padding: '20px 20px 16px 20px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '12px' }}>
                  <div>
                    <span style={{
                      fontSize: '11px',
                      fontWeight: 700,
                      color: 'var(--accent-light)',
                      background: 'rgba(99,102,241,0.1)',
                      padding: '4px 8px',
                      borderRadius: '4px',
                      textTransform: 'uppercase',
                      letterSpacing: '0.05em'
                    }}>
                      {sec.course_code}
                    </span>
                    <h4 style={{ fontSize: '16px', fontWeight: 700, margin: '8px 0 0 0', lineHeight: 1.3, color: 'var(--text-primary)' }}>
                      {sec.course_name}
                    </h4>
                  </div>
                  
                  <button 
                    onClick={() => handleDeleteSection(sec.id)}
                    disabled={deletingSectionId === sec.id}
                    style={{
                      background: 'transparent',
                      border: 'none',
                      color: 'var(--text-secondary)',
                      cursor: 'pointer',
                      padding: '4px',
                      borderRadius: '6px',
                      transition: 'background 0.2s, color 0.2s'
                    }}
                    onMouseEnter={(e) => { e.currentTarget.style.background = 'rgba(239,68,68,0.1)'; e.currentTarget.style.color = 'var(--danger)'; }}
                    onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--text-secondary)'; }}
                  >
                    {deletingSectionId === sec.id ? (
                      <Loader2 size={16} className="spin text-danger" />
                    ) : (
                      <Trash2 size={16} />
                    )}
                  </button>
                </div>

                {/* Card Details */}
                <div style={{ padding: '0 20px 16px 20px', display: 'flex', flexDirection: 'column', gap: '12px', flex: 1 }}>
                  {/* Target Academic Section Badge */}
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', alignItems: 'center' }}>
                    {sec.target_student_reg ? (
                      <span className="badge" style={{ fontWeight: 700, fontSize: '11px', background: 'linear-gradient(90deg, #f59e0b 0%, #d97706 100%)', color: '#fff', border: 'none' }}>
                        Student: {sec.target_student_reg}
                      </span>
                    ) : (
                      <span className="badge badge-accent" style={{ fontWeight: 700, fontSize: '12px', background: 'linear-gradient(90deg, var(--accent) 0%, var(--accent-dark) 100%)', color: '#fff', border: 'none' }}>
                        {sec.academic_section_label || 'All Sections'}
                      </span>
                    )}
                    <span className="badge badge-secondary" style={{ fontSize: '11px', fontWeight: 600 }}>
                      Section Label: {sec.section_label}
                    </span>
                    <span className="badge badge-secondary" style={{ fontSize: '11px', fontWeight: 600 }}>
                      {sec.credit_hours} Cr. Hrs
                    </span>
                  </div>

                  <div style={{ fontSize: '13px', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: '8px', marginTop: '4px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <User size={14} className="text-accent" style={{ color: 'var(--accent-light)' }} />
                      <span>Instructor: <strong style={{ color: 'var(--text-primary)' }}>{sec.teacher_name || 'TBA'}</strong></span>
                    </div>
                  </div>
                </div>

                {/* Card Footer Control */}
                <div style={{
                  padding: '16px 20px',
                  borderTop: '1px solid var(--border)',
                  background: 'rgba(0,0,0,0.15)',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center'
                }}>
                  <div style={{ display: 'flex', flexDirection: 'column' }}>
                    <span style={{ fontSize: '11px', color: 'var(--text-secondary)', fontWeight: 500 }}>Enrolled</span>
                    <span style={{ fontSize: '15px', fontWeight: 700, color: 'var(--text-primary)' }}>{sec.enrolled_count} Students</span>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    {togglingSectionId === sec.id ? (
                      <Loader2 size={16} className="spin text-accent" />
                    ) : (
                      <button
                        onClick={() => handleToggleRegistration(sec)}
                        style={{
                          background: sec.is_registration_open ? 'rgba(16,185,129,0.1)' : 'rgba(255,255,255,0.05)',
                          color: sec.is_registration_open ? 'var(--success)' : 'var(--text-secondary)',
                          border: `1px solid ${sec.is_registration_open ? 'rgba(16,185,129,0.2)' : 'var(--border)'}`,
                          borderRadius: '8px',
                          padding: '6px 12px',
                          fontSize: '12px',
                          fontWeight: 700,
                          display: 'flex',
                          alignItems: 'center',
                          gap: '6px',
                          cursor: 'pointer',
                          transition: 'all 0.2s'
                        }}
                      >
                        {sec.is_registration_open ? (
                          <>
                            <Play size={12} fill="var(--success)" />
                            <span>Live</span>
                          </>
                        ) : (
                          <>
                            <EyeOff size={12} />
                            <span>Hidden</span>
                          </>
                        )}
                      </button>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ─── Modal: Offer Course ─── */}
      {isOfferModalOpen && (
        <div className="modal-overlay" style={{ zIndex: 1000 }}>
          <div className="modal" style={{ width: '100%', maxWidth: '540px' }}>
            <div className="modal-header">
              <h3 className="modal-title">Offer Course for Registration</h3>
              <button className="modal-close" onClick={() => setIsOfferModalOpen(false)}>
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleOfferCourse}>
              <div className="modal-body">
                {/* Course Selection */}
                <div className="form-group">
                  <label className="form-label">Select Course *</label>
                  <select 
                    className="form-control" 
                    value={selectedCourseId}
                    onChange={(e) => setSelectedCourseId(e.target.value)}
                    required
                  >
                    <option value="">-- Choose Course --</option>
                    {courses.map(c => (
                      <option key={c.id} value={c.id}>
                        [{c.code}] {c.name} ({c.credit_hours} Cr)
                      </option>
                    ))}
                  </select>
                </div>

                {/* Target Type Toggle */}
                <div className="form-group">
                  <label className="form-label" style={{ fontWeight: 600 }}>Target Audience *</label>
                  <div style={{ display: 'flex', gap: '20px', marginTop: '6px', marginBottom: '12px' }}>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '14px' }}>
                      <input 
                        type="radio" 
                        name="targetType" 
                        value="BATCH" 
                        checked={targetType === 'BATCH'} 
                        onChange={() => setTargetType('BATCH')} 
                      />
                      <span>Whole Batch Section</span>
                    </label>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '14px' }}>
                      <input 
                        type="radio" 
                        name="targetType" 
                        value="STUDENT" 
                        checked={targetType === 'STUDENT'} 
                        onChange={() => setTargetType('STUDENT')} 
                      />
                      <span>Single Student (by Reg No)</span>
                    </label>
                  </div>
                </div>

                {/* Target Academic Section (BATCH mode) */}
                {targetType === 'BATCH' && (
                  <div className="form-group">
                    <label className="form-label">Target Academic Section *</label>
                    <select 
                      className="form-control" 
                      value={selectedAcademicSectionId}
                      onChange={(e) => setSelectedAcademicSectionId(e.target.value)}
                      required={targetType === 'BATCH'}
                    >
                      <option value="">-- Choose Academic Section (Batch-Dept-Sec) --</option>
                      {academicSections.map(as => (
                        <option key={as.id} value={as.id}>
                          {as.batch}-{as.department_code}-{as.section_name}
                        </option>
                      ))}
                    </select>
                  </div>
                )}

                {/* Single Student Registration Number (STUDENT mode) */}
                {targetType === 'STUDENT' && (
                  <div className="form-group">
                    <label className="form-label">Student Registration Number *</label>
                    <input 
                      type="text" 
                      className="form-control" 
                      placeholder="e.g. SP23-BCS-001"
                      value={targetStudentReg}
                      onChange={(e) => setTargetStudentReg(e.target.value.toUpperCase())}
                      required={targetType === 'STUDENT'}
                    />
                  </div>
                )}

                {/* Custom Section Label & Teacher */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 2fr', gap: '16px' }}>
                  <div className="form-group">
                    <label className="form-label">Section Label *</label>
                    <input 
                      type="text" 
                      className="form-control" 
                      placeholder="e.g. A"
                      value={customSectionLabel}
                      onChange={(e) => setCustomSectionLabel(e.target.value)}
                      maxLength={5}
                      required
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label">Instructor / Teacher</label>
                    <select 
                      className="form-control" 
                      value={selectedTeacherId}
                      onChange={(e) => setSelectedTeacherId(e.target.value)}
                    >
                      <option value="">-- Select Instructor (TBA) --</option>
                      {teachers.map(t => (
                        <option key={t.id} value={t.id}>
                          {t.full_name} ({t.employee_id})
                        </option>
                      ))}
                    </select>
                  </div>
                </div>


              </div>

              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setIsOfferModalOpen(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={submittingOffer}>
                  {submittingOffer ? (
                    <Loader2 size={16} className="spin" />
                  ) : (
                    <span>Create & Offer</span>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ─── Modal: Set Deadline ─── */}
      {isDeadlineModalOpen && (
        <div className="modal-overlay" style={{ zIndex: 1000 }}>
          <div className="modal" style={{ width: '100%', maxWidth: '400px' }}>
            <div className="modal-header">
              <h3 className="modal-title">Set Registration Deadline</h3>
              <button className="modal-close" onClick={() => setIsDeadlineModalOpen(false)}>
                <X size={18} />
              </button>
            </div>

            <form onSubmit={handleSaveDeadline}>
              <div className="modal-body">
                <div className="form-group">
                  <label className="form-label">Deadline (Local Date & Time)</label>
                  <input
                    type="datetime-local"
                    className="form-control"
                    value={deadlineInput}
                    onChange={(e) => setDeadlineInput(e.target.value)}
                    required
                  />
                  <p style={{ fontSize: '11px', color: 'var(--text-secondary)', marginTop: '6px' }}>
                    After this deadline, students will no longer be able to register or withdraw from offered courses.
                  </p>
                </div>
              </div>

              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setIsDeadlineModalOpen(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={savingDeadline}>
                  {savingDeadline ? (
                    <Loader2 size={16} className="spin" />
                  ) : (
                    <span>Apply Deadline</span>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
