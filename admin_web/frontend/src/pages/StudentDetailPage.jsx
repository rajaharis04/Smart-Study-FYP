import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { studentApi, deptApi, enrollmentApi } from '../services/api';
import Modal from '../components/Modal';
import {
  ArrowLeft, Trash2, Edit2, Key, ToggleLeft, ToggleRight,
  Eye, EyeOff, AlertCircle, Mail, GraduationCap, Building2,
  Calendar, Shield, X, User
} from 'lucide-react';
import { toast } from 'react-hot-toast';

export default function StudentDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [student, setStudent] = useState(null);
  const [departments, setDepartments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState('');

  // Modals
  const [editOpen, setEditOpen] = useState(false);
  const [passwordModalOpen, setPasswordModalOpen] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  // Password reset state
  const [generatedPassword, setGeneratedPassword] = useState('');

  // Edit form states
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [batch, setBatch] = useState('');
  const [departmentId, setDepartmentId] = useState('');

  const fetchStudentData = async () => {
    setLoading(true);
    try {
      const [sRes, dRes] = await Promise.all([
        studentApi.detail(id),
        deptApi.list()
      ]);
      setStudent(sRes.data);
      setDepartments(dRes.data);

      // Prepopulate form states
      setFullName(sRes.data.full_name);
      setEmail(sRes.data.email);
      setBatch(sRes.data.batch);
      const dept = dRes.data.find((d) => d.name === sRes.data.department_name);
      setDepartmentId(dept ? String(dept.id) : '');
      setError('');
    } catch (err) {
      console.error('Error fetching student details:', err);
      setError('Student details load nahi ho paaye.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStudentData();
  }, [id]);

  const handleEditSave = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        full_name: fullName,
        email,
        batch,
        department_id: departmentId ? parseInt(departmentId) : null,
      };
      await studentApi.update(id, payload);
      toast.success('Student details updated successfully.');
      setEditOpen(false);
      fetchStudentData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Update failed.');
    }
  };

  const handleResetPassword = async () => {
    if (!window.confirm(`Are you sure you want to reset password for ${student.full_name}?`)) return;
    try {
      const res = await studentApi.resetPassword(id);
      setGeneratedPassword(res.data.new_password);
      setPasswordModalOpen(true);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to reset password.');
    }
  };

  const handleToggleActive = async () => {
    const action = student.is_active ? 'deactivate' : 'activate';
    if (!window.confirm(`Are you sure you want to ${action} this student account?`)) return;
    try {
      await studentApi.update(id, { is_active: !student.is_active });
      toast.success(`Student account ${action}d successfully.`);
      fetchStudentData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to toggle account status.');
    }
  };

  const handleDeleteStudent = async () => {
    if (!window.confirm(`Are you sure you want to delete ${student.full_name} permanently? This will remove their record from the database and drop them from all registered class sections.`)) return;
    try {
      await studentApi.delete(id);
      toast.success('Student account deleted permanently.');
      navigate('/students');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to delete student.');
    }
  };

  const handleDropCourse = async (enrollmentId, courseName) => {
    if (!window.confirm(`Are you sure you want to drop ${student.full_name} from the course "${courseName}"?`)) return;
    setDetailLoading(true);
    try {
      await enrollmentApi.deactivate(enrollmentId);
      toast.success('Student dropped from course successfully.');
      fetchStudentData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to drop course.');
    } finally {
      setDetailLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="loading" style={{ textAlign: 'center', padding: '48px', color: 'var(--accent-light)' }}>
        Loading student workspace...
      </div>
    );
  }

  if (error || !student) {
    return (
      <div style={{ padding: '24px', maxWidth: '600px', margin: '0 auto' }}>
        <div className="result-box error mb-4" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <AlertCircle size={18} />
          <span>{error || 'Student records not found.'}</span>
        </div>
        <button className="btn btn-secondary" onClick={() => navigate('/students')}>
          <ArrowLeft size={16} /> Back to Directory
        </button>
      </div>
    );
  }

  return (
    <div style={{ animation: 'fadeIn 0.2s ease', display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Page Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '16px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
          <button className="btn btn-secondary btn-sm btn-icon" onClick={() => navigate('/students')} title="Back to Directory">
            <ArrowLeft size={18} />
          </button>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <h1 className="page-title" style={{ margin: 0 }}>{student.full_name}</h1>
              <span className="badge badge-accent" style={{ fontSize: '12px', padding: '4px 10px' }}>
                {student.reg_number}
              </span>
            </div>
            <p className="page-subtitle" style={{ marginTop: '4px' }}>Student profile workspace and enrollment management.</p>
          </div>
        </div>
        
        <div style={{ display: 'flex', gap: '10px' }}>
          <button className="btn btn-secondary" onClick={() => setEditOpen(true)}>
            <Edit2 size={16} />
            <span>Edit Profile</span>
          </button>
          <button className="btn btn-secondary" onClick={handleResetPassword}>
            <Key size={16} />
            <span>Reset Password</span>
          </button>
          <button 
            className={`btn ${student.is_active ? 'btn-danger' : 'btn-success'}`} 
            onClick={handleToggleActive}
          >
            {student.is_active ? <ToggleLeft size={16} /> : <ToggleRight size={16} />}
            <span>{student.is_active ? 'Deactivate' : 'Activate'}</span>
          </button>
        </div>
      </div>

      {/* Main Workspace Layout */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1.8fr', gap: '24px', alignItems: 'start' }}>
        
        {/* Left Column: Student Profile Details */}
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Student Profile</h2>
          </div>
          <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            
            {/* Header Initials / Info */}
            <div style={{
              background: 'linear-gradient(135deg, rgba(255,255,255,0.03) 0%, rgba(99,102,241,0.05) 100%)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius-lg)',
              padding: '24px',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              textAlign: 'center',
              gap: '12px'
            }}>
              {student.profile_picture ? (
                <img 
                  src={`http://localhost:8001${student.profile_picture}`} 
                  alt="" 
                  style={{
                    width: '90px',
                    height: '90px',
                    borderRadius: '50%',
                    objectFit: 'cover',
                    border: '2px solid var(--accent)',
                    boxShadow: 'var(--shadow-accent)'
                  }}
                />
              ) : (
                <div style={{
                  width: '90px',
                  height: '90px',
                  borderRadius: '50%',
                  background: 'var(--accent)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '32px',
                  fontWeight: 800,
                  color: '#fff',
                  boxShadow: 'var(--shadow-accent)'
                }}>
                  {student.full_name?.charAt(0).toUpperCase()}
                </div>
              )}
              <div>
                <h3 style={{ fontSize: '18px', fontWeight: 700, margin: 0 }}>{student.full_name}</h3>
                <span className={`badge ${student.is_active ? 'badge-success' : 'badge-danger'}`} style={{ marginTop: '8px' }}>
                  {student.is_active ? 'Active Account' : 'Inactive'}
                </span>
              </div>
            </div>

            {/* Profile Grid fields */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', background: 'rgba(255,255,255,0.02)', padding: '12px 16px', borderRadius: '8px', border: '1px solid var(--border)' }}>
                <Mail size={16} color="var(--text-secondary)" />
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  <span style={{ fontSize: '10px', textTransform: 'uppercase', color: 'var(--text-secondary)' }}>Email Address</span>
                  <span style={{ fontSize: '13px', fontWeight: 600, marginTop: '2px', wordBreak: 'break-all' }}>{student.email}</span>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', background: 'rgba(255,255,255,0.02)', padding: '12px 16px', borderRadius: '8px', border: '1px solid var(--border)' }}>
                <Building2 size={16} color="var(--text-secondary)" />
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  <span style={{ fontSize: '10px', textTransform: 'uppercase', color: 'var(--text-secondary)' }}>Department</span>
                  <span style={{ fontSize: '13px', fontWeight: 600, marginTop: '2px' }}>{student.department_name || 'Unassigned'}</span>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', background: 'rgba(255,255,255,0.02)', padding: '12px 16px', borderRadius: '8px', border: '1px solid var(--border)' }}>
                <GraduationCap size={16} color="var(--text-secondary)" />
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  <span style={{ fontSize: '10px', textTransform: 'uppercase', color: 'var(--text-secondary)' }}>Academic Section</span>
                  <span style={{ fontSize: '13px', fontWeight: 600, marginTop: '2px' }}>{student.academic_section_label || 'Unassigned'}</span>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', background: 'rgba(255,255,255,0.02)', padding: '12px 16px', borderRadius: '8px', border: '1px solid var(--border)' }}>
                <Calendar size={16} color="var(--text-secondary)" />
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  <span style={{ fontSize: '10px', textTransform: 'uppercase', color: 'var(--text-secondary)' }}>Batch Year</span>
                  <span style={{ fontSize: '13px', fontWeight: 600, marginTop: '2px' }}>{student.batch}</span>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '12px', background: 'rgba(255,255,255,0.02)', padding: '12px 16px', borderRadius: '8px', border: '1px solid var(--border)' }}>
                <Shield size={16} color="var(--text-secondary)" />
                <div style={{ display: 'flex', flexDirection: 'column' }}>
                  <span style={{ fontSize: '10px', textTransform: 'uppercase', color: 'var(--text-secondary)' }}>Account Created</span>
                  <span style={{ fontSize: '13px', fontWeight: 600, marginTop: '2px' }}>
                    {student.created_at ? new Date(student.created_at).toLocaleDateString() : '-'}
                  </span>
                </div>
              </div>
            </div>

            {/* Permanent delete control */}
            <div style={{ borderTop: '1px solid var(--border)', paddingTop: '16px', marginTop: '8px' }}>
              <button className="btn btn-danger w-full" onClick={handleDeleteStudent} style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', gap: '6px' }}>
                <Trash2 size={16} />
                <span>Delete Student Profile</span>
              </button>
            </div>

          </div>
        </div>

        {/* Right Column: Active Course Registrations */}
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Registered Class Sections</h2>
          </div>
          <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: '16px', minHeight: '300px', position: 'relative' }}>
            
            {detailLoading && (
              <div style={{
                position: 'absolute', inset: 0, background: 'rgba(10, 14, 26, 0.7)',
                backdropFilter: 'blur(3px)', zIndex: 10, display: 'flex',
                alignItems: 'center', justifyContent: 'center', borderRadius: 'var(--radius-lg)'
              }}>
                <div className="loading" style={{ color: 'var(--accent-light)' }}>Updating enrollments...</div>
              </div>
            )}

            {!student.enrollments || student.enrollments.length === 0 ? (
              <div style={{
                padding: '48px',
                background: 'rgba(255,255,255,0.01)',
                border: '1px dashed var(--border)',
                borderRadius: 'var(--radius-lg)',
                textAlign: 'center',
                color: 'var(--text-secondary)'
              }}>
                <div style={{ fontSize: '40px', marginBottom: '12px', opacity: 0.5 }}>📚</div>
                <h3>No Active Course Enrollments</h3>
                <p style={{ fontSize: '13px', marginTop: '6px' }}>This student is currently not registered in any class sections.</p>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {student.enrollments.map((enroll) => (
                  <div 
                    key={enroll.id} 
                    style={{
                      background: 'rgba(255,255,255,0.02)',
                      border: '1px solid var(--border)',
                      borderRadius: 'var(--radius-md)',
                      padding: '18px',
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      transition: 'all 0.2s',
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.borderColor = 'rgba(239, 68, 68, 0.2)'}
                    onMouseLeave={(e) => e.currentTarget.style.borderColor = 'var(--border)'}
                  >
                    <div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                        <span className="badge badge-accent" style={{ fontSize: '10px' }}>
                          {enroll.course_code}
                        </span>
                        <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-secondary)' }}>
                          Section {enroll.section_label}
                        </span>
                      </div>
                      <h4 style={{ fontSize: '14px', fontWeight: 700, margin: '8px 0 4px 0' }}>{enroll.course_name}</h4>
                      <p style={{ fontSize: '12px', color: 'var(--text-secondary)', margin: 0 }}>Instructor: {enroll.instructor_name}</p>
                    </div>
                    
                    <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                      <span 
                        className="badge" 
                        style={{
                          background: enroll.status === 'ACTIVE' ? 'rgba(16,185,129,0.1)' : 'rgba(245,158,11,0.08)',
                          color: enroll.status === 'ACTIVE' ? 'var(--success)' : 'var(--warning)',
                          border: 'none',
                          fontWeight: 700,
                          fontSize: '10px'
                        }}
                      >
                        {enroll.status}
                      </span>
                      
                      <button
                        className="btn btn-danger btn-sm btn-icon"
                        onClick={() => handleDropCourse(enroll.id, enroll.course_name)}
                        title="Drop Student from Course"
                        style={{ width: '32px', height: '32px' }}
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

      </div>

      {/* EDIT STUDENT DETAILS MODAL */}
      <Modal
        isOpen={editOpen}
        onClose={() => setEditOpen(false)}
        title="Edit Student Details"
        footer={
          <>
            <button className="btn btn-secondary" onClick={() => setEditOpen(false)}>Cancel</button>
            <button className="btn btn-primary" onClick={handleEditSave}>Save Changes</button>
          </>
        }
      >
        <form onSubmit={handleEditSave} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div className="form-group">
            <label className="form-label">Registration Number</label>
            <input
              type="text"
              className="form-control"
              value={student.reg_number}
              disabled
              style={{ opacity: 0.6, cursor: 'not-allowed' }}
            />
          </div>
          <div className="form-group">
            <label className="form-label">Full Name</label>
            <input
              type="text"
              className="form-control"
              placeholder="e.g. Ali Hassan"
              required
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
            />
          </div>
          <div className="form-group">
            <label className="form-label">Email Address</label>
            <input
              type="email"
              className="form-control"
              placeholder="e.g. ali@std.comsats.edu.pk"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          <div className="form-grid">
            <div className="form-group">
              <label className="form-label">Batch</label>
              <input
                type="text"
                className="form-control"
                placeholder="e.g. SP23"
                required
                value={batch}
                onChange={(e) => setBatch(e.target.value)}
              />
            </div>
            <div className="form-group">
              <label className="form-label">Department</label>
              <select
                className="form-control"
                value={departmentId}
                onChange={(e) => setDepartmentId(e.target.value)}
              >
                <option value="">-- Select --</option>
                {departments.map((dept) => (
                  <option key={dept.id} value={dept.id}>
                    {dept.code} - {dept.name}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </form>
      </Modal>

      {/* PASSWORD SHOW MODAL */}
      <Modal
        isOpen={passwordModalOpen}
        onClose={() => setPasswordModalOpen(false)}
        title={`Password Reset for ${student.full_name}`}
        footer={
          <button className="btn btn-primary w-full" onClick={() => setPasswordModalOpen(false)}>Done</button>
        }
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <p style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>
            The temporary password has been reset successfully. Share this copy with the student securely:
          </p>
          <div style={{ position: 'relative' }}>
            <div className="password-box">
              {showPassword ? generatedPassword : '••••••••••••'}
            </div>
            <button
              type="button"
              className="btn btn-secondary btn-sm"
              onClick={() => setShowPassword(!showPassword)}
              style={{
                position: 'absolute',
                right: '12px',
                top: '50%',
                transform: 'translateY(-50%)',
                padding: '4px 8px',
              }}
            >
              {showPassword ? <EyeOff size={14} /> : <Eye size={14} />}
            </button>
          </div>
          <button
            className="btn btn-secondary btn-sm w-full"
            onClick={() => {
              navigator.clipboard.writeText(generatedPassword);
              toast.success('Password copied to clipboard!');
            }}
          >
            Copy Password
          </button>
        </div>
      </Modal>
    </div>
  );
}
