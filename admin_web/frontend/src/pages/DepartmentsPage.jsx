import { useState, useEffect } from 'react';
import { deptApi } from '../services/api';
import DataTable from '../components/DataTable';
import Modal from '../components/Modal';
import { Building2, Plus, Edit2, Trash2, AlertCircle } from 'lucide-react';
import { toast } from 'react-hot-toast';

export default function DepartmentsPage() {
  const [departments, setDepartments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [editingDept, setEditingDept] = useState(null);

  // Form states
  const [name, setName] = useState('');
  const [code, setCode] = useState('');
  const [hodName, setHodName] = useState('');

  const fetchDepartments = async () => {
    setLoading(true);
    try {
      const res = await deptApi.list();
      setDepartments(res.data);
    } catch (err) {
      setError('Failed to fetch departments.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDepartments();
  }, []);

  const openCreateModal = () => {
    setEditingDept(null);
    setName('');
    setCode('');
    setHodName('');
    setModalOpen(true);
  };

  const openEditModal = (dept) => {
    setEditingDept(dept);
    setName(dept.name);
    setCode(dept.code);
    setHodName(dept.hod_name);
    setModalOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      if (editingDept) {
        await deptApi.update(editingDept.id, { name, code, hod_name: hodName });
        toast.success('Department updated successfully');
      } else {
        await deptApi.create({ name, code, hod_name: hodName });
        toast.success('Department created successfully');
      }
      setModalOpen(false);
      fetchDepartments();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Operation failed.');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this department?')) return;
    try {
      await deptApi.delete(id);
      toast.success('Department deleted');
      fetchDepartments();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to delete department.');
    }
  };

  const headers = [
    { key: 'code', label: 'Code' },
    { key: 'name', label: 'Department Name' },
    { key: 'hod_name', label: 'Head of Department (HOD)' },
    { key: 'actions', label: 'Actions', sortable: false },
  ];

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Departments</h1>
          <p className="page-subtitle">Manage university departments, code prefixes, and HODs.</p>
        </div>
        <button className="btn btn-primary" onClick={openCreateModal}>
          <Plus size={16} />
          <span>Add Department</span>
        </button>
      </div>

      {error && (
        <div className="result-box error mb-4" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      {loading ? (
        <div className="loading" style={{ textAlign: 'center', padding: '24px' }}>Loading departments...</div>
      ) : (
        <DataTable
          headers={headers}
          data={departments}
          searchKeys={['name', 'code', 'hod_name']}
          searchPlaceholder="Search departments..."
          renderRow={(dept) => (
            <>
              <td><span className="badge badge-accent">{dept.code}</span></td>
              <td>{dept.name}</td>
              <td>{dept.hod_name}</td>
              <td>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button className="btn btn-secondary btn-sm btn-icon" onClick={() => openEditModal(dept)} title="Edit">
                    <Edit2 size={14} />
                  </button>
                  <button className="btn btn-danger btn-sm btn-icon" onClick={() => handleDelete(dept.id)} title="Delete">
                    <Trash2 size={14} />
                  </button>
                </div>
              </td>
            </>
          )}
        />
      )}

      <Modal
        isOpen={modalOpen}
        onClose={() => setModalOpen(false)}
        title={editingDept ? 'Edit Department' : 'Create Department'}
        footer={
          <>
            <button className="btn btn-secondary" onClick={() => setModalOpen(false)}>Cancel</button>
            <button className="btn btn-primary" onClick={handleSubmit}>
              {editingDept ? 'Save Changes' : 'Create'}
            </button>
          </>
        }
      >
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div className="form-group">
            <label className="form-label">Department Code</label>
            <input
              type="text"
              className="form-control"
              placeholder="e.g. CS"
              required
              value={code}
              onChange={(e) => setCode(e.target.value)}
              disabled={!!editingDept} // Code cannot be edited if updating to protect data integrity
            />
          </div>
          <div className="form-group">
            <label className="form-label">Department Name</label>
            <input
              type="text"
              className="form-control"
              placeholder="e.g. Computer Science"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          <div className="form-group">
            <label className="form-label">HOD Name</label>
            <input
              type="text"
              className="form-control"
              placeholder="e.g. Dr. Muhammad Sharif"
              required
              value={hodName}
              onChange={(e) => setHodName(e.target.value)}
            />
          </div>
        </form>
      </Modal>
    </div>
  );
}
