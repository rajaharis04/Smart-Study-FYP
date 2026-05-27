import { useState, useEffect } from 'react';
import { deptApi } from '../services/api';
import DataTable from '../components/DataTable';
import Modal from '../components/Modal';
import { Building2, Plus, Edit2, Trash2, AlertCircle, Eye, X } from 'lucide-react';
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

  // Department detail state
  const [selectedDept, setSelectedDept] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const handleOpenDetails = async (dept) => {
    console.log("handleOpenDetails triggered for department:", dept);
    setSelectedDept(dept);
    setDetailLoading(true);
    try {
      const res = await deptApi.detail(dept.id);
      console.log("deptApi.detail response data:", res.data);
      setSelectedDept((prev) => ({
        ...prev,
        ...res.data,
      }));
    } catch (err) {
      console.error("Error fetching department details:", err);
      toast.error('Failed to load department details.');
    } finally {
      setDetailLoading(false);
    }
  };

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
              <td 
                style={{ cursor: 'pointer', fontWeight: 600, color: 'var(--accent-light)' }}
                onClick={() => handleOpenDetails(dept)}
              >
                <span className="badge badge-accent" style={{ cursor: 'pointer' }}>{dept.code}</span>
              </td>
              <td 
                style={{ cursor: 'pointer', fontWeight: 500 }}
                onClick={() => handleOpenDetails(dept)}
              >
                {dept.name}
              </td>
              <td style={{ cursor: 'pointer' }} onClick={() => handleOpenDetails(dept)}>{dept.hod_name}</td>
              <td>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button 
                    className="btn btn-secondary btn-sm btn-icon" 
                    onClick={() => handleOpenDetails(dept)} 
                    title="View Details"
                  >
                    <Eye size={14} />
                  </button>
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
      {/* ─── SLIDE-OVER DETAIL DRAWER ─── */}
      <div 
        className={`drawer-overlay ${selectedDept ? 'active' : ''}`} 
        onClick={() => setSelectedDept(null)}
      >
        <div 
          className={`drawer-content ${selectedDept ? 'active' : ''}`} 
          onClick={(e) => e.stopPropagation()}
        >
          {selectedDept && (
            <>
              <div className="drawer-header">
                <h2 style={{ fontSize: '18px', fontWeight: 800, margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span className="badge badge-accent" style={{ fontSize: '13px', padding: '6px 10px' }}>
                    {selectedDept.code}
                  </span>
                </h2>
                <button className="drawer-close" onClick={() => setSelectedDept(null)}>
                  <X size={20} />
                </button>
              </div>

              <div className="drawer-body">
                {/* Department Header Card */}
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
                    borderRadius: '12px',
                    background: 'var(--accent)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    fontSize: '24px',
                    color: '#fff',
                    boxShadow: 'var(--shadow-accent)'
                  }}>
                    <Building2 size={32} />
                  </div>
                  <div>
                    <h3 style={{ fontSize: '18px', fontWeight: 700, margin: 0 }}>{selectedDept.name}</h3>
                    <span style={{ fontSize: '12px', color: 'var(--text-secondary)', display: 'block', marginTop: '4px' }}>
                      HOD: <strong>{selectedDept.hod_name}</strong>
                    </span>
                  </div>
                </div>

                {/* Statistics Grid */}
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
                  <div style={{ background: 'rgba(255,255,255,0.02)', padding: '16px', borderRadius: '10px', border: '1px solid var(--border)', textAlign: 'center' }}>
                    <span style={{ fontSize: '24px', fontWeight: 800, color: 'var(--accent-light)' }}>
                      {detailLoading ? (
                        <span className="loading" style={{ fontSize: '16px' }}>...</span>
                      ) : (
                        selectedDept.teachers?.length || 0
                      )}
                    </span>
                    <span style={{ display: 'block', fontSize: '10px', textTransform: 'uppercase', color: 'var(--text-secondary)', marginTop: '4px' }}>Faculty Members</span>
                  </div>
                  <div style={{ background: 'rgba(255,255,255,0.02)', padding: '16px', borderRadius: '10px', border: '1px solid var(--border)', textAlign: 'center' }}>
                    <span style={{ fontSize: '24px', fontWeight: 800, color: 'var(--success)' }}>
                      {detailLoading ? (
                        <span className="loading" style={{ fontSize: '16px' }}>...</span>
                      ) : (
                        selectedDept.student_count || 0
                      )}
                    </span>
                    <span style={{ display: 'block', fontSize: '10px', textTransform: 'uppercase', color: 'var(--text-secondary)', marginTop: '4px' }}>Enrolled Students</span>
                  </div>
                </div>

                {/* Teachers List */}
                <div>
                  <h4 className="drawer-section-title">Department Faculty</h4>
                  {detailLoading ? (
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '12px' }}>
                      <div className="loading" style={{ color: 'var(--accent-light)', fontSize: '12px' }}>Loading faculty...</div>
                    </div>
                  ) : !selectedDept.teachers || selectedDept.teachers.length === 0 ? (
                    <div style={{ fontSize: '12px', color: 'var(--text-secondary)', fontStyle: 'italic' }}>No faculty registered.</div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '180px', overflowY: 'auto', paddingRight: '4px' }}>
                      {selectedDept.teachers.map(t => (
                        <div key={t.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(255,255,255,0.01)', border: '1px solid var(--border)', padding: '10px 14px', borderRadius: '6px' }}>
                          <div>
                            <div style={{ fontSize: '13px', fontWeight: 600 }}>{t.full_name}</div>
                            <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>{t.email}</div>
                          </div>
                          <span className="badge badge-accent" style={{ fontSize: '10px' }}>{t.employee_id}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Courses List */}
                <div>
                  <h4 className="drawer-section-title">Course Catalog</h4>
                  {detailLoading ? (
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '12px' }}>
                      <div className="loading" style={{ color: 'var(--accent-light)', fontSize: '12px' }}>Loading courses...</div>
                    </div>
                  ) : !selectedDept.courses || selectedDept.courses.length === 0 ? (
                    <div style={{ fontSize: '12px', color: 'var(--text-secondary)', fontStyle: 'italic' }}>No courses cataloged.</div>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '180px', overflowY: 'auto', paddingRight: '4px' }}>
                      {selectedDept.courses.map(c => (
                        <div key={c.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(255,255,255,0.01)', border: '1px solid var(--border)', padding: '10px 14px', borderRadius: '6px' }}>
                          <div>
                            <div style={{ fontSize: '13px', fontWeight: 600 }}>{c.name}</div>
                            <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>{c.code}</div>
                          </div>
                          <span className="badge badge-secondary" style={{ fontSize: '10px' }}>{c.credit_hours} Cr</span>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Academic Sections List */}
                <div>
                  <h4 className="drawer-section-title">Academic Class Sections</h4>
                  {detailLoading ? (
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '12px' }}>
                      <div className="loading" style={{ color: 'var(--accent-light)', fontSize: '12px' }}>Loading class sections...</div>
                    </div>
                  ) : !selectedDept.academic_sections || selectedDept.academic_sections.length === 0 ? (
                    <div style={{ fontSize: '12px', color: 'var(--text-secondary)', fontStyle: 'italic' }}>No class sections.</div>
                  ) : (
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                      {selectedDept.academic_sections.map(sec => (
                        <span key={sec.id} className="badge badge-info" style={{ padding: '6px 12px', fontSize: '11px' }}>
                          {sec.full_label}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>

              <div className="drawer-footer">
                <button 
                  className="btn btn-danger" 
                  onClick={() => {
                    handleDelete(selectedDept.id);
                    setSelectedDept(null);
                  }}
                  style={{ marginRight: 'auto', display: 'flex', alignItems: 'center', gap: '6px' }}
                >
                  <Trash2 size={14} />
                  <span>Delete Dept</span>
                </button>
                <button className="btn btn-secondary" onClick={() => setSelectedDept(null)}>Close</button>
                <button 
                  className="btn btn-primary" 
                  onClick={() => {
                    openEditModal(selectedDept);
                    setSelectedDept(null);
                  }}
                  style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
                >
                  <Edit2 size={14} />
                  <span>Edit Dept</span>
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
