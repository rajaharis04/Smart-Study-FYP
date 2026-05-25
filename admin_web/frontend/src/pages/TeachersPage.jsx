import { useState, useEffect } from 'react';
import { teacherApi, deptApi } from '../services/api';
import DataTable from '../components/DataTable';
import Modal from '../components/Modal';
import { Plus, Key, ToggleLeft, ToggleRight, AlertCircle, Eye, EyeOff, Edit2, Trash2 } from 'lucide-react';
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
              <td><span className="badge badge-accent">{t.employee_id}</span></td>
              <td>{t.full_name}</td>
              <td>{t.email}</td>
              <td>{t.department_name || <span className="text-muted">Unassigned</span>}</td>
              <td>
                <span className={`badge ${t.is_active ? 'badge-success' : 'badge-danger'}`}>
                  {t.is_active ? 'Active' : 'Inactive'}
                </span>
              </td>
              <td>
                <div style={{ display: 'flex', gap: '8px' }}>
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
    </div>
  );
}
