import { useState, useEffect } from 'react';
import { semesterApi, sectionApi } from '../services/api';
import DataTable from '../components/DataTable';
import { Calendar, AlertCircle, Save, BookOpen, Layers, CheckCircle, Clock, Loader2 } from 'lucide-react';
import { toast } from 'react-hot-toast';

export default function RegistrationWeekPage() {
  const [activeSemester, setActiveSemester] = useState(null);
  const [sections, setSections] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [deadlineInput, setDeadlineInput] = useState('');
  const [savingDeadline, setSavingDeadline] = useState(false);
  const [togglingSectionId, setTogglingSectionId] = useState(null);

  const fetchData = async () => {
    setLoading(true);
    setError('');
    try {
      // 1. Fetch active semester
      const semRes = await semesterApi.active();
      const sem = semRes.data;
      setActiveSemester(sem);
      
      if (sem.registration_deadline) {
        // Convert to local format for datetime-local input (YYYY-MM-DDTHH:mm)
        const d = new Date(sem.registration_deadline);
        const pad = (num) => String(num).padStart(2, '0');
        const formatted = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
        setDeadlineInput(formatted);
      } else {
        setDeadlineInput('');
      }

      // 2. Fetch all sections and filter by active semester
      const sectionsRes = await sectionApi.list();
      const filteredSections = sectionsRes.data.filter(s => s.semester_id === sem.id);
      setSections(filteredSections);
    } catch (err) {
      console.error(err);
      setError(err.response?.data?.detail || 'Failed to fetch registration data. Please ensure an active semester is configured.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleSaveDeadline = async (e) => {
    e.preventDefault();
    if (!activeSemester) return;

    setSavingDeadline(true);
    try {
      const payload = {
        registration_deadline: deadlineInput ? new Date(deadlineInput).toISOString() : null
      };
      await semesterApi.update(activeSemester.id, payload);
      toast.success('Registration deadline updated successfully');
      // Refresh active semester state
      const semRes = await semesterApi.active();
      setActiveSemester(semRes.data);
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
      
      // Update local state
      setSections(prev => prev.map(s => s.id === section.id ? { ...s, is_registration_open: newStatus } : s));
      toast.success(`Registration ${newStatus ? 'opened' : 'closed'} for ${section.course_code} - Section ${section.section_label}`);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to toggle registration.');
    } finally {
      setTogglingSectionId(null);
    }
  };

  const headers = [
    { key: 'course_code', label: 'Course Code' },
    { key: 'course_name', label: 'Course Name' },
    { key: 'section_label', label: 'Section' },
    { key: 'teacher_name', label: 'Instructor' },
    { key: 'schedule', label: 'Schedule' },
    { key: 'room', label: 'Room' },
    { key: 'is_registration_open', label: 'Offered for Registration', sortable: false },
  ];

  if (loading) {
    return <div className="loading" style={{ textAlign: 'center', padding: '48px' }}>Loading registration configurations...</div>;
  }

  if (error) {
    return (
      <div className="result-box error mb-4" style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '16px' }}>
        <AlertCircle size={20} />
        <span>{error}</span>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Semester Header Info */}
      <div style={{
        background: 'linear-gradient(135deg, var(--bg-secondary) 0%, rgba(29, 158, 117, 0.05) 100%)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius-lg)',
        padding: '24px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        flexWrap: 'wrap',
        gap: '20px'
      }}>
        <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
          <div style={{
            background: 'rgba(29, 158, 117, 0.1)',
            color: 'var(--accent)',
            width: '48px',
            height: '48px',
            borderRadius: '12px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}>
            <Calendar size={24} />
          </div>
          <div>
            <h2 style={{ fontSize: '18px', fontWeight: 700, margin: 0 }}>Active Session: {activeSemester?.name}</h2>
            <p style={{ fontSize: '13px', color: 'var(--text-secondary)', margin: '4px 0 0 0' }}>
              Define registration deadlines and manage offered sections for self-enrollment.
            </p>
          </div>
        </div>

        {activeSemester?.registration_deadline ? (
          <div style={{
            background: 'rgba(245, 158, 11, 0.08)',
            border: '1px solid rgba(245, 158, 11, 0.2)',
            borderRadius: 'var(--radius-md)',
            padding: '8px 16px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            fontSize: '13px',
            color: 'var(--warning)',
            fontWeight: 600
          }}>
            <Clock size={16} />
            <span>Deadline: {new Date(activeSemester.registration_deadline).toLocaleString()}</span>
          </div>
        ) : (
          <div style={{
            background: 'rgba(239, 68, 68, 0.08)',
            border: '1px solid rgba(239, 68, 68, 0.2)',
            borderRadius: 'var(--radius-md)',
            padding: '8px 16px',
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            fontSize: '13px',
            color: 'var(--text-danger)',
            fontWeight: 600
          }}>
            <AlertCircle size={16} />
            <span>No deadline configured!</span>
          </div>
        )}
      </div>

      {/* Deadline Form Card */}
      <div style={{
        background: 'var(--bg-secondary)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius-lg)',
        padding: '24px'
      }}>
        <h3 style={{ fontSize: '15px', fontWeight: 600, marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}>
          <Clock size={18} className="text-accent" />
          <span>Set Registration Deadline</span>
        </h3>
        <form onSubmit={handleSaveDeadline} style={{ display: 'flex', alignItems: 'flex-end', gap: '16px', flexWrap: 'wrap' }}>
          <div className="form-group" style={{ flex: '1', minWidth: '250px' }}>
            <label className="form-label">Withdrawal & Registration Limit (Local Time)</label>
            <input
              type="datetime-local"
              className="form-control"
              value={deadlineInput}
              onChange={(e) => setDeadlineInput(e.target.value)}
              required
            />
          </div>
          <button
            type="submit"
            className="btn btn-primary"
            disabled={savingDeadline}
            style={{ height: '40px', padding: '0 20px', display: 'flex', alignItems: 'center', gap: '8px' }}
          >
            {savingDeadline ? (
              <Loader2 size={16} className="spin" />
            ) : (
              <Save size={16} />
            )}
            <span>Save Deadline</span>
          </button>
        </form>
      </div>

      {/* Sections List Card */}
      <div style={{
        background: 'var(--bg-secondary)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius-lg)',
        padding: '24px'
      }}>
        <div style={{ marginBottom: '20px' }}>
          <h3 style={{ fontSize: '15px', fontWeight: 600, margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Layers size={18} className="text-accent" />
            <span>Manage Course Sections for Registration</span>
          </h3>
          <p style={{ fontSize: '13px', color: 'var(--text-secondary)', marginTop: '4px' }}>
            Toggle sections to add or remove them from the student self-registration catalog.
          </p>
        </div>

        {sections.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '32px', color: 'var(--text-secondary)' }}>
            No sections found in the active semester. Please create sections first.
          </div>
        ) : (
          <DataTable
            headers={headers}
            data={sections}
            searchKeys={['course_code', 'course_name', 'section_label', 'teacher_name']}
            searchPlaceholder="Search courses or instructors..."
            renderRow={(sec) => (
              <>
                <td><span className="badge badge-accent" style={{ fontWeight: 700 }}>{sec.course_code}</span></td>
                <td style={{ fontWeight: 500 }}>{sec.course_name}</td>
                <td><span className="badge badge-secondary">{sec.section_label}</span></td>
                <td>{sec.teacher_name || <span className="text-muted">TBA</span>}</td>
                <td>{sec.schedule || <span className="text-muted">-</span>}</td>
                <td>{sec.room || <span className="text-muted">-</span>}</td>
                <td>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    {togglingSectionId === sec.id ? (
                      <Loader2 size={16} className="spin text-accent" />
                    ) : (
                      <label className="switch" style={{
                        position: 'relative',
                        display: 'inline-block',
                        width: '38px',
                        height: '20px'
                      }}>
                        <input
                          type="checkbox"
                          checked={sec.is_registration_open}
                          onChange={() => handleToggleRegistration(sec)}
                          style={{
                            opacity: 0,
                            width: 0,
                            height: 0
                          }}
                        />
                        <span style={{
                          position: 'absolute',
                          cursor: 'pointer',
                          top: 0,
                          left: 0,
                          right: 0,
                          bottom: 0,
                          backgroundColor: sec.is_registration_open ? 'var(--accent)' : 'var(--border)',
                          transition: '0.3s',
                          borderRadius: '20px'
                        }}>
                          <span style={{
                            position: 'absolute',
                            content: '""',
                            height: '14px',
                            width: '14px',
                            left: sec.is_registration_open ? '20px' : '3px',
                            bottom: '3px',
                            backgroundColor: 'white',
                            transition: '0.3s',
                            borderRadius: '50%'
                          }} />
                        </span>
                      </label>
                    )}
                    <span style={{
                      fontSize: '12px',
                      fontWeight: 600,
                      color: sec.is_registration_open ? 'var(--accent)' : 'var(--text-secondary)'
                    }}>
                      {sec.is_registration_open ? 'Offered' : 'Hidden'}
                    </span>
                  </div>
                </td>
              </>
            )}
          />
        )}
      </div>
    </div>
  );
}
