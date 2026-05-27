import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { studentApi, deptApi } from '../services/api';
import DataTable from '../components/DataTable';
import Modal from '../components/Modal';
import CSVUploader from '../components/CSVUploader';
import { Plus, Upload, Key, ToggleLeft, ToggleRight, AlertCircle, Eye, EyeOff, Edit2, Trash2, X } from 'lucide-react';
import { toast } from 'react-hot-toast';

export default function StudentsPage() {
  const navigate = useNavigate();
  const [students, setStudents] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Modals
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [passwordModalOpen, setPasswordModalOpen] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  // Editing state
  const [editingStudent, setEditingStudent] = useState(null);

  // Password reset state
  const [generatedPassword, setGeneratedPassword] = useState('');
  const [passwordModalTitle, setPasswordModalTitle] = useState('');

  // Form states
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [regNumber, setRegNumber] = useState('');
  const [batch, setBatch] = useState('');
  const [departmentId, setDepartmentId] = useState('');

  const handleOpenDetails = (student) => {
    navigate(`/students/${student.id}`);
  };

  const fetchData = async () => {
    setLoading(true);
    try {
      const [sRes, dRes] = await Promise.all([studentApi.list(), deptApi.list()]);
      setStudents(sRes.data);
      setDepartments(dRes.data);
    } catch (err) {
      setError('Failed to fetch students or departments.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const openCreateModal = () => {
    setEditingStudent(null);
    setFullName('');
    setEmail('');
    setRegNumber('');
    setBatch('');
    setDepartmentId('');
    setCreateModalOpen(true);
  };

  const openEditModal = (student) => {
    setEditingStudent(student);
    setFullName(student.full_name);
    setEmail(student.email);
    setRegNumber(student.reg_number);
    setBatch(student.batch);
    const dept = departments.find((d) => d.name === student.department_name);
    setDepartmentId(dept ? String(dept.id) : '');
    setCreateModalOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editingStudent) {
        const payload = {
          full_name: fullName,
          email,
          batch,
          department_id: departmentId ? parseInt(departmentId) : null,
        };
        await studentApi.update(editingStudent.id, payload);
        setCreateModalOpen(false);
        toast.success('Student details updated successfully.');
      } else {
        const payload = {
          full_name: fullName,
          email,
          reg_number: regNumber,
          batch,
          department_id: departmentId ? parseInt(departmentId) : null,
        };
        const res = await studentApi.create(payload);
        setCreateModalOpen(false);
        toast.success(res.data.message || 'Student account created successfully.');
      }
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Operation failed.');
    }
  };

  const handleResetPassword = async (id, name) => {
    if (!window.confirm(`Are you sure you want to reset password for ${name}?`)) return;
    try {
      const res = await studentApi.resetPassword(id);
      setGeneratedPassword(res.data.new_password);
      setPasswordModalTitle(`Password Reset for ${name}`);
      setPasswordModalOpen(true);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to reset password.');
    }
  };

  const handleToggleActive = async (student) => {
    const action = student.is_active ? 'deactivate' : 'activate';
    if (!window.confirm(`Are you sure you want to ${action} this student account?`)) return;
    try {
      await studentApi.update(student.id, { is_active: !student.is_active });
      toast.success(`Student ${action}d successfully`);
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to toggle account status.');
    }
  };

  const handleDelete = async (id, name) => {
    if (!window.confirm(`Are you sure you want to delete ${name} permanently? This will remove their record from the database and drop them from all registered class sections.`)) return;
    try {
      await studentApi.delete(id);
      toast.success('Student account deleted permanently.');
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to delete student.');
    }
  };

  const handleCSVUpload = async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await studentApi.bulkUpload(formData);
    fetchData();
    return res.data;
  };

  const headers = [
    { key: 'reg_number', label: 'Registration No' },
    { key: 'full_name', label: 'Full Name' },
    { key: 'email', label: 'Email' },
    { key: 'batch', label: 'Batch' },
    { key: 'department_name', label: 'Department' },
    { key: 'is_active', label: 'Status' },
    { key: 'actions', label: 'Actions', sortable: false },
  ];

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Students</h1>
          <p className="page-subtitle">Provision student accounts via manual form or bulk CSV upload.</p>
        </div>
        <div style={{ display: 'flex', gap: '12px' }}>
          <button className="btn btn-secondary" onClick={() => setUploadModalOpen(true)}>
            <Upload size={16} />
            <span>Bulk CSV Upload</span>
          </button>
          <button className="btn btn-primary" onClick={openCreateModal}>
            <Plus size={16} />
            <span>Add Student</span>
          </button>
        </div>
      </div>

      {error && (
        <div className="result-box error mb-4" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      {loading ? (
        <div className="loading" style={{ textAlign: 'center', padding: '24px' }}>Loading students directory...</div>
      ) : (
        <DataTable
          headers={headers}
          data={students}
          searchKeys={['full_name', 'reg_number', 'email', 'batch', 'department_name']}
          searchPlaceholder="Search students..."
          renderRow={(s) => (
            <>
              <td 
                style={{ cursor: 'pointer', fontWeight: 600, color: 'var(--accent-light)' }}
                onClick={() => handleOpenDetails(s)}
              >
                <span className="badge badge-accent" style={{ cursor: 'pointer' }}>{s.reg_number}</span>
              </td>
              <td 
                style={{ cursor: 'pointer', fontWeight: 500 }}
                onClick={() => handleOpenDetails(s)}
              >
                {s.full_name}
              </td>
              <td style={{ cursor: 'pointer' }} onClick={() => handleOpenDetails(s)}>{s.email}</td>
              <td style={{ cursor: 'pointer' }} onClick={() => handleOpenDetails(s)}>{s.batch}</td>
              <td style={{ cursor: 'pointer' }} onClick={() => handleOpenDetails(s)}>{s.department_name || <span className="text-muted">Unassigned</span>}</td>
              <td style={{ cursor: 'pointer' }} onClick={() => handleOpenDetails(s)}>
                <span className={`badge ${s.is_active ? 'badge-success' : 'badge-danger'}`}>
                  {s.is_active ? 'Active' : 'Inactive'}
                </span>
              </td>
              <td>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button
                    className="btn btn-secondary btn-sm btn-icon"
                    onClick={() => handleOpenDetails(s)}
                    title="View Details"
                  >
                    <Eye size={14} />
                  </button>
                  <button
                    className="btn btn-secondary btn-sm btn-icon"
                    onClick={() => openEditModal(s)}
                    title="Edit Student"
                  >
                    <Edit2 size={14} />
                  </button>
                  <button
                    className="btn btn-secondary btn-sm btn-icon"
                    onClick={() => handleResetPassword(s.id, s.full_name)}
                    title="Reset Password"
                  >
                    <Key size={14} />
                  </button>
                  <button
                    className={`btn btn-sm btn-icon ${s.is_active ? 'btn-danger' : 'btn-success'}`}
                    onClick={() => handleToggleActive(s)}
                    title={s.is_active ? 'Deactivate' : 'Activate'}
                  >
                    {s.is_active ? <ToggleLeft size={16} /> : <ToggleRight size={16} />}
                  </button>
                  <button
                    className="btn btn-danger btn-sm btn-icon"
                    onClick={() => handleDelete(s.id, s.full_name)}
                    title="Delete Student"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </td>
            </>
          )}
        />
      )}

      {/* CREATE/EDIT STUDENT MODAL */}
      <Modal
        isOpen={createModalOpen}
        onClose={() => setCreateModalOpen(false)}
        title={editingStudent ? 'Edit Student Details' : 'Create Student Account'}
        footer={
          <>
            <button className="btn btn-secondary" onClick={() => setCreateModalOpen(false)}>Cancel</button>
            <button className="btn btn-primary" onClick={handleSubmit}>
              {editingStudent ? 'Save Changes' : 'Create Account'}
            </button>
          </>
        }
      >
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div className="form-group">
            <label className="form-label">Registration Number</label>
            <input
              type="text"
              className="form-control"
              placeholder="e.g. SP23-BCS-011"
              required
              value={regNumber}
              onChange={(e) => setRegNumber(e.target.value)}
              disabled={!!editingStudent}
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
                    {dept.code}
                  </option>
                ))}
              </select>
            </div>
          </div>
        </form>
      </Modal>

      {/* CSV UPLOAD MODAL */}
      <Modal
        isOpen={uploadModalOpen}
        onClose={() => setUploadModalOpen(false)}
        title="Bulk Student Upload"
        footer={
          <button className="btn btn-secondary w-full" onClick={() => setUploadModalOpen(false)}>Close</button>
        }
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <CSVUploader
            title="Drag & Drop Student CSV"
            subtitle="Columns: Name, Email, RegNumber, Batch, Department"
            onUpload={handleCSVUpload}
          />
          <div style={{ fontSize: '12px', color: 'var(--text-muted)', lineHeight: '1.4' }}>
            <strong>Note:</strong> Make sure the department code in the CSV matches the code in the database (e.g. CS, EE). If matching department code isn't found, the student's department will be set to unassigned.
          </div>
        </div>
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
            The student account has been successfully created. Copy the temporary password to share with them:
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
