import { useState, useEffect } from 'react';
import { teacherApi, deptApi } from '../services/api';
import DataTable from '../components/DataTable';
import Modal from '../components/Modal';
import { Plus, Key, ToggleLeft, ToggleRight, AlertCircle, Eye, EyeOff, Edit2, Trash2, X } from 'lucide-react';
import { toast } from 'react-hot-toast';

export default function TeachersPage() {
  const [teachers, setTeachers] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Modals
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [passwordModalOpen, setPasswordModalOpen] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  // Editing state
  const [editingTeacher, setEditingTeacher] = useState(null);

  // Password reset / Generated password storage
  const [generatedPassword, setGeneratedPassword] = useState('');
  const [passwordModalTitle, setPasswordModalTitle] = useState('');

  // Form states
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [employeeId, setEmployeeId] = useState('');
  const [departmentId, setDepartmentId] = useState('');
  const [manualPassword, setManualPassword] = useState('');

  // Teacher detail state
  const [selectedTeacher, setSelectedTeacher] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const handleOpenDetails = async (teacher) => {
    console.log("handleOpenDetails triggered for teacher:", teacher);
    setSelectedTeacher(teacher);
    setDetailLoading(true);
    try {
      const res = await teacherApi.detail(teacher.id);
      console.log("teacherApi.detail response data:", res.data);
      setSelectedTeacher((prev) => ({
        ...prev,
        ...res.data,
      }));
    } catch (err) {
      console.error("Error fetching teacher details:", err);
      toast.error('Failed to load teacher details.');
    } finally {
      setDetailLoading(false);
    }
  };

  const fetchData = async () => {
    setLoading(true);
    try {
      const [tRes, dRes] = await Promise.all([teacherApi.list(), deptApi.list()]);
      setTeachers(tRes.data);
      setDepartments(dRes.data);
    } catch (err) {
      setError('Failed to fetch teachers or departments data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const openCreateModal = () => {
    setEditingTeacher(null);
    setFullName('');
    setEmail('');
    setEmployeeId('');
    setDepartmentId('');
    setManualPassword('');
    setCreateModalOpen(true);
  };

  const openEditModal = (teacher) => {
    setEditingTeacher(teacher);
    setFullName(teacher.full_name);
    setEmail(teacher.email);
    setEmployeeId(teacher.employee_id);
    const dept = departments.find((d) => d.name === teacher.department_name);
    setDepartmentId(dept ? String(dept.id) : '');
    setCreateModalOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editingTeacher) {
        const payload = {
          full_name: fullName,
          email,
          department_id: departmentId ? parseInt(departmentId) : null,
        };
        await teacherApi.update(editingTeacher.id, payload);
        setCreateModalOpen(false);
        toast.success('Teacher details updated successfully.');
      } else {
        const payload = {
          full_name: fullName,
          email,
          employee_id: employeeId,
          department_id: departmentId ? parseInt(departmentId) : null,
        };
        const res = await teacherApi.create(payload);
        setCreateModalOpen(false);
        toast.success(res.data.message || 'Teacher account created successfully.');
      }
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Operation failed.');
    }
  };

  const handleResetPassword = async (id, name) => {
    if (!window.confirm(`Are you sure you want to reset password for ${name}?`)) return;
    try {
      const res = await teacherApi.resetPassword(id);
      setGeneratedPassword(res.data.new_password);
      setPasswordModalTitle(`Password Reset for ${name}`);
      setPasswordModalOpen(true);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to reset password.');
    }
  };

  const handleToggleActive = async (teacher) => {
    const action = teacher.is_active ? 'deactivate' : 'activate';
    if (!window.confirm(`Are you sure you want to ${action} this teacher account?`)) return;
    try {
      if (teacher.is_active) {
        await teacherApi.deactivate(teacher.id);
        toast.success('Teacher deactivated');
      } else {
        await teacherApi.update(teacher.id, { is_active: true });
        toast.success('Teacher activated');
      }
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to toggle account status.');
    }
  };

  const handleDelete = async (id, name) => {
    if (!window.confirm(`Are you sure you want to delete ${name} permanently? This will remove their record from the database and unassign them from all class sections.`)) return;
    try {
      await teacherApi.deactivate(id);
      toast.success('Teacher account deleted permanently.');
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to delete teacher.');
    }
  };

  const headers = [
    { key: 'employee_id', label: 'Employee ID' },
    { key: 'full_name', label: 'Full Name' },
    { key: 'email', label: 'Email' },
    { key: 'department_name', label: 'Department' },
    { key: 'is_active', label: 'Status' },
    { key: 'actions', label: 'Actions', sortable: false },
  ];

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Teachers</h1>
          <p className="page-subtitle">Add teacher profiles, assign departments, and reset credentials.</p>
        </div>
        <button className="btn btn-primary" onClick={openCreateModal}>
          <Plus size={16} />
          <span>Add Teacher</span>
        </button>
      </div>

      {error && (
        <div className="result-box error mb-4" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      {loading ? (
        <div className="loading" style={{ textAlign: 'center', padding: '24px' }}>Loading teachers directory...</div>
      ) : (
        <DataTable
          headers={headers}
          data={teachers}
          searchKeys={['full_name', 'employee_id', 'email', 'department_name']}
          searchPlaceholder="Search teachers..."
          renderRow={(t) => (
            <>
              <td 
                style={{ cursor: 'pointer', fontWeight: 600, color: 'var(--accent-light)' }}
                onClick={() => handleOpenDetails(t)}
              >
                <span className="badge badge-accent" style={{ cursor: 'pointer' }}>{t.employee_id}</span>
              </td>
              <td 
                style={{ cursor: 'pointer', fontWeight: 500 }}
                onClick={() => handleOpenDetails(t)}
              >
                {t.full_name}
              </td>
              <td style={{ cursor: 'pointer' }} onClick={() => handleOpenDetails(t)}>{t.email}</td>
              <td style={{ cursor: 'pointer' }} onClick={() => handleOpenDetails(t)}>{t.department_name || <span className="text-muted">Unassigned</span>}</td>
              <td style={{ cursor: 'pointer' }} onClick={() => handleOpenDetails(t)}>
                <span className={`badge ${t.is_active ? 'badge-success' : 'badge-danger'}`}>
                  {t.is_active ? 'Active' : 'Inactive'}
                </span>
              </td>
              <td>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button
                    className="btn btn-secondary btn-sm btn-icon"
                    onClick={() => handleOpenDetails(t)}
                    title="View Details"
                  >
                    <Eye size={14} />
                  </button>
                  <button
                    className="btn btn-secondary btn-sm btn-icon"
                    onClick={() => openEditModal(t)}
                    title="Edit Teacher"
                  >
                    <Edit2 size={14} />
                  </button>
                  <button
                    className="btn btn-secondary btn-sm btn-icon"
                    onClick={() => handleResetPassword(t.id, t.full_name)}
                    title="Reset Password"
                  >
                    <Key size={14} />
                  </button>
                  <button
                    className={`btn btn-sm btn-icon ${t.is_active ? 'btn-danger' : 'btn-success'}`}
                    onClick={() => handleToggleActive(t)}
                    title={t.is_active ? 'Deactivate' : 'Activate'}
                  >
                    {t.is_active ? <ToggleLeft size={16} /> : <ToggleRight size={16} />}
                  </button>
                  <button
                    className="btn btn-danger btn-sm btn-icon"
                    onClick={() => handleDelete(t.id, t.full_name)}
                    title="Delete Teacher"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </td>
            </>
          )}
        />
      )}

      {/* CREATE/EDIT TEACHER MODAL */}
      <Modal
        isOpen={createModalOpen}
        onClose={() => setCreateModalOpen(false)}
        title={editingTeacher ? 'Edit Teacher Details' : 'Create Teacher Account'}
        footer={
          <>
            <button className="btn btn-secondary" onClick={() => setCreateModalOpen(false)}>Cancel</button>
            <button className="btn btn-primary" onClick={handleSubmit}>
              {editingTeacher ? 'Save Changes' : 'Create Account'}
            </button>
          </>
        }
      >
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div className="form-group">
            <label className="form-label">Employee ID</label>
            <input
              type="text"
              className="form-control"
              placeholder="e.g. EMP-2021-045"
              required
              value={employeeId}
              onChange={(e) => setEmployeeId(e.target.value)}
              disabled={!!editingTeacher}
            />
          </div>
          <div className="form-group">
            <label className="form-label">Full Name</label>
            <input
              type="text"
              className="form-control"
              placeholder="e.g. Dr. Ahmad Khan"
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
              placeholder="e.g. ahmad.khan@comsats.edu.pk"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          <div className="form-group">
            <label className="form-label">Department Assignment</label>
            <select
              className="form-control"
              value={departmentId}
              onChange={(e) => setDepartmentId(e.target.value)}
            >
              <option value="">-- Select Department --</option>
              {departments.map((dept) => (
                <option key={dept.id} value={dept.id}>
                  {dept.code} - {dept.name}
                </option>
              ))}
            </select>
          </div>
        </form>
      </Modal>

      {/* PASSWORD SHOW MODAL */}
      <Modal
        isOpen={passwordModalOpen}
        onClose={() => setPasswordModalOpen(false)}
        title={passwordModalTitle}
        footer={
          <button className="btn btn-primary w-full" onClick={() => setPasswordModalOpen(false)}>Done</button>
        }
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <p style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>
            Please copy this password. It will only be shown once. Share this with the teacher securely so they can log in and change it.
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

      {/* ─── SLIDE-OVER DETAIL DRAWER ─── */}
      <div 
        className={`drawer-overlay ${selectedTeacher ? 'active' : ''}`} 
        onClick={() => setSelectedTeacher(null)}
      >
        <div 
          className={`drawer-content ${selectedTeacher ? 'active' : ''}`} 
          onClick={(e) => e.stopPropagation()}
        >
          {selectedTeacher && (
            <>
              <div className="drawer-header">
                <h2 style={{ fontSize: '18px', fontWeight: 800, margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span className="badge badge-accent" style={{ fontSize: '13px', padding: '6px 10px' }}>
                    {selectedTeacher.employee_id}
                  </span>
                </h2>
                <button className="drawer-close" onClick={() => setSelectedTeacher(null)}>
                  <X size={20} />
                </button>
              </div>

              <div className="drawer-body">
                {/* Teacher Header Card */}
                <div style={{
                  background: 'linear-gradient(135deg, rgba(255,255,255,0.03) 0%, rgba(99,102,241,0.05) 100%)',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--radius-lg)',
                  padding: '20px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '16px'
                }}>
                  <div style={{
                    width: '60px',
                    height: '60px',
                    borderRadius: '50%',
                    background: 'var(--accent)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '24px',
                    fontWeight: 700,
                    color: '#fff',
                    textTransform: 'uppercase',
                    boxShadow: 'var(--shadow-accent)'
                  }}>
                    {selectedTeacher.full_name?.charAt(0)}
                  </div>
                  <div>
                    <h3 style={{ fontSize: '18px', fontWeight: 700, margin: 0 }}>{selectedTeacher.full_name}</h3>
                    <span className={`badge ${selectedTeacher.is_active ? 'badge-success' : 'badge-danger'}`} style={{ marginTop: '6px', display: 'inline-block' }}>
                      {selectedTeacher.is_active ? 'Active Account' : 'Inactive'}
                    </span>
                  </div>
                </div>

                {/* Profile Info Details Grid */}
                <div>
                  <h4 className="drawer-section-title">Teacher Profile</h4>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
                    <div style={{ background: 'rgba(255,255,255,0.02)', padding: '12px 16px', borderRadius: '8px', border: '1px solid var(--border)' }}>
                      <span style={{ fontSize: '10px', textTransform: 'uppercase', color: 'var(--text-secondary)' }}>Email Address</span>
                      <div style={{ fontSize: '13px', fontWeight: 600, marginTop: '4px', wordBreak: 'break-all' }}>{selectedTeacher.email}</div>
                    </div>
                    <div style={{ background: 'rgba(255,255,255,0.02)', padding: '12px 16px', borderRadius: '8px', border: '1px solid var(--border)' }}>
                      <span style={{ fontSize: '10px', textTransform: 'uppercase', color: 'var(--text-secondary)' }}>Department</span>
                      <div style={{ fontSize: '13px', fontWeight: 600, marginTop: '4px' }}>{selectedTeacher.department_name || 'Unassigned'}</div>
                    </div>
                    <div style={{ background: 'rgba(255,255,255,0.02)', padding: '12px 16px', borderRadius: '8px', border: '1px solid var(--border)', gridColumn: 'span 2' }}>
                      <span style={{ fontSize: '10px', textTransform: 'uppercase', color: 'var(--text-secondary)' }}>Joined Date</span>
                      <div style={{ fontSize: '13px', fontWeight: 600, marginTop: '4px' }}>{selectedTeacher.created_at ? new Date(selectedTeacher.created_at).toLocaleDateString() : '-'}</div>
                    </div>
                  </div>
                </div>

                {/* Assigned Sections list */}
                <div>
                  <h4 className="drawer-section-title">Assigned Class Sections</h4>
                  {detailLoading ? (
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '24px' }}>
                      <div className="loading" style={{ color: 'var(--accent-light)', fontSize: '13px' }}>Loading assigned classes...</div>
                    </div>
                  ) : !selectedTeacher.sections || selectedTeacher.sections.length === 0 ? (
                    <div style={{
                      padding: '24px',
                      background: 'rgba(255,255,255,0.01)',
                      border: '1px dashed var(--border)',
                      borderRadius: 'var(--radius-md)',
                      textAlign: 'center',
                      color: 'var(--text-secondary)',
                      fontSize: '13px'
                    }}>
                      No assigned classes active for this teacher.
                    </div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                      {selectedTeacher.sections.map((sec) => (
                        <div 
                          key={sec.section_id} 
                          style={{
                            background: 'rgba(255,255,255,0.02)',
                            border: '1px solid var(--border)',
                            borderRadius: 'var(--radius-md)',
                            padding: '16px',
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center'
                          }}
                        >
                          <div>
                            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                              <span className="badge badge-accent" style={{ fontSize: '10px' }}>
                                {sec.course_code}
                              </span>
                              <span style={{ fontSize: '11px', fontWeight: 700, color: 'var(--text-secondary)' }}>
                                Section {sec.section_label}
                              </span>
                            </div>
                            <h5 style={{ fontSize: '13px', fontWeight: 700, margin: '6px 0 2px 0' }}>{sec.course_name}</h5>
                            <p style={{ fontSize: '11px', color: 'var(--text-secondary)', margin: 0 }}>Target: {sec.academic_section_label}</p>
                            {sec.semester_name && <p style={{ fontSize: '11px', color: 'var(--text-muted)', margin: '2px 0 0 0' }}>Semester: {sec.semester_name}</p>}
                          </div>
                          <div style={{ textAlign: 'right' }}>
                            <div style={{ fontSize: '14px', fontWeight: 800, color: 'var(--success)' }}>
                              {sec.enrolled_count} <span style={{ fontSize: '10px', color: 'var(--text-secondary)', fontWeight: 500 }}>Active</span>
                            </div>
                            {sec.pending_count > 0 && (
                              <div style={{ fontSize: '11px', fontWeight: 600, color: 'var(--warning)', marginTop: '2px' }}>
                                {sec.pending_count} Pending
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              <div className="drawer-footer">
                <button 
                  className="btn btn-danger" 
                  onClick={() => {
                    handleDelete(selectedTeacher.id, selectedTeacher.full_name);
                    setSelectedTeacher(null);
                  }}
                  style={{ marginRight: 'auto', display: 'flex', alignItems: 'center', gap: '6px' }}
                >
                  <Trash2 size={14} />
                  <span>Delete Teacher</span>
                </button>
                <button className="btn btn-secondary" onClick={() => setSelectedTeacher(null)}>Close</button>
                <button 
                  className="btn btn-primary" 
                  onClick={() => {
                    openEditModal(selectedTeacher);
                    setSelectedTeacher(null);
                  }}
                  style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
                >
                  <Edit2 size={14} />
                  <span>Edit Profile</span>
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
