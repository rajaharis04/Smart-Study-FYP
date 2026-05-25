import { useState, useEffect } from 'react';
import { courseApi, deptApi, semesterApi } from '../services/api';
import DataTable from '../components/DataTable';
import Modal from '../components/Modal';
import { Plus, Edit2, Archive, RotateCcw, Trash2, AlertCircle } from 'lucide-react';
import { toast } from 'react-hot-toast';

export default function CoursesPage() {
  const [courses, setCourses] = useState([]);
  const [departments, setDepartments] = useState([]);
  const [semesters, setSemesters] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [editingCourse, setEditingCourse] = useState(null);

  // Form states
  const [name, setName] = useState('');
  const [code, setCode] = useState('');
  const [creditHours, setCreditHours] = useState('3');
  const [departmentId, setDepartmentId] = useState('');
  const [semesterId, setSemesterId] = useState('');

  const fetchData = async () => {
    setLoading(true);
    try {
      const [cRes, dRes, sRes] = await Promise.all([
        courseApi.list(),
        deptApi.list(),
        semesterApi.list()
      ]);
      setCourses(cRes.data);
      setDepartments(dRes.data);
      setSemesters(sRes.data);
    } catch (err) {
      setError('Failed to fetch academic details.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const openCreateModal = () => {
    setEditingCourse(null);
    setName('');
    setCode('');
    setCreditHours('3');
    setDepartmentId('');
    setSemesterId('');
    setModalOpen(true);
  };

  const openEditModal = (course) => {
    setEditingCourse(course);
    setName(course.name);
    setCode(course.code);
    setCreditHours(String(course.credit_hours));
    // Find matching department & semester to set in form
    const dept = departments.find((d) => d.name === course.department_name);
    const sem = semesters.find((s) => s.name === course.semester_name);
    setDepartmentId(dept ? String(dept.id) : '');
    setSemesterId(sem ? String(sem.id) : '');
    setModalOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      const payload = {
        name,
        code,
        credit_hours: parseInt(creditHours),
        department_id: departmentId ? parseInt(departmentId) : null,
        semester_id: semesterId ? parseInt(semesterId) : null,
      };

      if (editingCourse) {
        await courseApi.update(editingCourse.id, payload);
        toast.success('Course details updated successfully');
      } else {
        await courseApi.create(payload);
        toast.success('Course created successfully');
      }
      setModalOpen(false);
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Operation failed.');
    }
  };

  const handleToggleArchive = async (course) => {
    const action = course.is_archived ? 'restore' : 'archive';
    if (!window.confirm(`Are you sure you want to ${action} this course?`)) return;
    try {
      await courseApi.update(course.id, { is_archived: !course.is_archived });
      toast.success(`Course ${action}d successfully`);
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to toggle archive status.');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this course? This will remove all associated sections and enrollments!')) return;
    try {
      await courseApi.delete(id);
      toast.success('Course deleted');
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to delete course.');
    }
  };

  const headers = [
    { key: 'code', label: 'Course Code' },
    { key: 'name', label: 'Course Name' },
    { key: 'credit_hours', label: 'Credits' },
    { key: 'department_name', label: 'Department' },
    { key: 'semester_name', label: 'Semester' },
    { key: 'sections_count', label: 'Sections' },
    { key: 'is_archived', label: 'Status' },
    { key: 'actions', label: 'Actions', sortable: false },
  ];

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Courses</h1>
          <p className="page-subtitle">Configure university courses, credit weights, and syllabus mappings.</p>
        </div>
        <button className="btn btn-primary" onClick={openCreateModal}>
          <Plus size={16} />
          <span>Add Course</span>
        </button>
      </div>

      {error && (
        <div className="result-box error mb-4" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      {loading ? (
        <div className="loading" style={{ textAlign: 'center', padding: '24px' }}>Loading courses data...</div>
      ) : (
        <DataTable
          headers={headers}
          data={courses}
          searchKeys={['name', 'code', 'department_name', 'semester_name']}
          searchPlaceholder="Search courses..."
          renderRow={(c) => (
            <>
              <td><span className="badge badge-accent">{c.code}</span></td>
              <td>{c.name}</td>
              <td>{c.credit_hours} CH</td>
              <td>{c.department_name || <span className="text-muted">General</span>}</td>
              <td>{c.semester_name || <span className="text-muted">Flexible</span>}</td>
              <td><span className="badge badge-info">{c.sections_count}</span></td>
              <td>
                <span className={`badge ${!c.is_archived ? 'badge-success' : 'badge-danger'}`}>
                  {!c.is_archived ? 'Active' : 'Archived'}
                </span>
              </td>
              <td>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button className="btn btn-secondary btn-sm btn-icon" onClick={() => openEditModal(c)} title="Edit">
                    <Edit2 size={14} />
                  </button>
                  <button
                    className="btn btn-secondary btn-sm btn-icon"
                    onClick={() => handleToggleArchive(c)}
                    title={c.is_archived ? 'Restore' : 'Archive'}
                  >
                    {c.is_archived ? <RotateCcw size={14} /> : <Archive size={14} />}
                  </button>
                  <button className="btn btn-danger btn-sm btn-icon" onClick={() => handleDelete(c.id)} title="Delete">
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
        title={editingCourse ? 'Edit Course Details' : 'Create Course'}
        footer={
          <>
            <button className="btn btn-secondary" onClick={() => setModalOpen(false)}>Cancel</button>
            <button className="btn btn-primary" onClick={handleSubmit}>
              {editingCourse ? 'Save Changes' : 'Create Course'}
            </button>
          </>
        }
      >
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div className="form-group">
            <label className="form-label">Course Code</label>
            <input
              type="text"
              className="form-control"
              placeholder="e.g. CSC-301"
              required
              value={code}
              onChange={(e) => setCode(e.target.value)}
              disabled={!!editingCourse} // Course code cannot be updated to preserve historical grades/schedules
            />
          </div>
          <div className="form-group">
            <label className="form-label">Course Name</label>
            <input
              type="text"
              className="form-control"
              placeholder="e.g. Database Systems"
              required
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>
          <div className="form-grid">
            <div className="form-group">
              <label className="form-label">Credit Hours</label>
              <select
                className="form-control"
                value={creditHours}
                onChange={(e) => setCreditHours(e.target.value)}
              >
                <option value="1">1 CH</option>
                <option value="2">2 CH</option>
                <option value="3">3 CH</option>
                <option value="4">4 CH</option>
              </select>
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
          <div className="form-group">
            <label className="form-label">Semester Mapping</label>
            <select
              className="form-control"
              value={semesterId}
              onChange={(e) => setSemesterId(e.target.value)}
            >
              <option value="">-- Select Semester --</option>
              {semesters.map((sem) => (
                <option key={sem.id} value={sem.id}>
                  {sem.name}
                </option>
              ))}
            </select>
          </div>
        </form>
      </Modal>
    </div>
  );
}
