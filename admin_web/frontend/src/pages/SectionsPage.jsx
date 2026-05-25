import { useState, useEffect } from 'react';
import { sectionApi, courseApi, teacherApi, semesterApi } from '../services/api';
import DataTable from '../components/DataTable';
import Modal from '../components/Modal';
import { Plus, Edit2, Trash2, AlertCircle, Calendar, MapPin, Clock } from 'lucide-react';
import { toast } from 'react-hot-toast';

export default function SectionsPage() {
  const [sections, setSections] = useState([]);
  const [courses, setCourses] = useState([]);
  const [teachers, setTeachers] = useState([]);
  const [semesters, setSemesters] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [modalOpen, setModalOpen] = useState(false);
  const [editingSection, setEditingSection] = useState(null);

  // Form states
  const [courseId, setCourseId] = useState('');
  const [sectionLabel, setSectionLabel] = useState('A');
  const [teacherId, setTeacherId] = useState('');
  const [semesterId, setSemesterId] = useState('');
  const [schedule, setSchedule] = useState('');
  const [room, setRoom] = useState('');

  const fetchData = async () => {
    setLoading(true);
    try {
      const [sRes, cRes, tRes, semRes] = await Promise.all([
        sectionApi.list(),
        courseApi.list(),
        teacherApi.list(),
        semesterApi.list()
      ]);
      setSections(sRes.data);
      // Filter out archived courses when creating a section
      setCourses(cRes.data.filter(c => !c.is_archived));
      setTeachers(tRes.data.filter(t => t.is_active));
      setSemesters(semRes.data);
    } catch (err) {
      setError('Failed to fetch sections or dependency lists.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const openCreateModal = () => {
    setEditingSection(null);
    setCourseId('');
    setSectionLabel('A');
    setTeacherId('');
    setSemesterId('');
    setSchedule('');
    setRoom('');
    setModalOpen(true);
  };

  const openEditModal = (sec) => {
    setEditingSection(sec);
    // Find course, teacher, semester mappings
    const c = courses.find((x) => x.code === sec.course_code);
    const t = teachers.find((x) => x.full_name === sec.teacher_name);
    const s = semesters.find((x) => x.name === sec.semester_name);

    setCourseId(c ? String(c.id) : '');
    setSectionLabel(sec.section_label);
    setTeacherId(t ? String(t.id) : '');
    setSemesterId(s ? String(s.id) : '');
    setSchedule(sec.schedule || '');
    setRoom(sec.room || '');
    setModalOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!courseId) {
      toast.error('Course selection is required.');
      return;
    }
    try {
      const payload = {
        course_id: parseInt(courseId),
        section_label: sectionLabel,
        teacher_id: teacherId ? parseInt(teacherId) : null,
        semester_id: semesterId ? parseInt(semesterId) : null,
        schedule: schedule || null,
        room: room || null,
      };

      if (editingSection) {
        await sectionApi.update(editingSection.id, payload);
        toast.success('Section updated successfully');
      } else {
        await sectionApi.create(payload);
        toast.success('Section created successfully');
      }
      setModalOpen(false);
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Operation failed.');
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Are you sure you want to delete this section? This will delete all active enrollments for this class!')) return;
    try {
      await sectionApi.delete(id);
      toast.success('Section deleted');
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to delete section.');
    }
  };

  const headers = [
    { key: 'course_code', label: 'Course Code' },
    { key: 'course_name', label: 'Course Title' },
    { key: 'section_label', label: 'Sec' },
    { key: 'teacher_name', label: 'Assigned Teacher' },
    { key: 'semester_name', label: 'Semester' },
    { key: 'schedule', label: 'Schedule & Location' },
    { key: 'enrolled_count', label: 'Enrolled' },
    { key: 'actions', label: 'Actions', sortable: false },
  ];

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Class Sections</h1>
          <p className="page-subtitle">Instantiate course sections, schedule classes, assign instructors, and set rooms.</p>
        </div>
        <button className="btn btn-primary" onClick={openCreateModal}>
          <Plus size={16} />
          <span>Create Section</span>
        </button>
      </div>

      {error && (
        <div className="result-box error mb-4" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <AlertCircle size={18} />
          <span>{error}</span>
        </div>
      )}

      {loading ? (
        <div className="loading" style={{ textAlign: 'center', padding: '24px' }}>Loading sections scheduler...</div>
      ) : (
        <DataTable
          headers={headers}
          data={sections}
          searchKeys={['course_name', 'course_code', 'section_label', 'teacher_name', 'semester_name']}
          searchPlaceholder="Search sections..."
          renderRow={(sec) => (
            <>
              <td><span className="badge badge-accent">{sec.course_code}</span></td>
              <td>{sec.course_name}</td>
              <td><span className="badge badge-info">{sec.section_label}</span></td>
              <td>{sec.teacher_name || <span className="text-muted">Unassigned</span>}</td>
              <td>{sec.semester_name || <span className="text-muted">N/A</span>}</td>
              <td>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', fontSize: '12px' }}>
                  {sec.schedule && (
                    <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <Clock size={12} className="text-muted" /> {sec.schedule}
                    </span>
                  )}
                  {sec.room && (
                    <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <MapPin size={12} className="text-muted" /> {sec.room}
                    </span>
                  )}
                  {!sec.schedule && !sec.room && <span className="text-muted">TBD</span>}
                </div>
              </td>
              <td>
                <span className="badge badge-success">{sec.enrolled_count} Students</span>
              </td>
              <td>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <button className="btn btn-secondary btn-sm btn-icon" onClick={() => openEditModal(sec)} title="Edit">
                    <Edit2 size={14} />
                  </button>
                  <button className="btn btn-danger btn-sm btn-icon" onClick={() => handleDelete(sec.id)} title="Delete">
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
        title={editingSection ? 'Modify Class Section' : 'Create Section'}
        footer={
          <>
            <button className="btn btn-secondary" onClick={() => setModalOpen(false)}>Cancel</button>
            <button className="btn btn-primary" onClick={handleSubmit}>
              {editingSection ? 'Save Changes' : 'Create Section'}
            </button>
          </>
        }
      >
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div className="form-group">
            <label className="form-label">Course Subject</label>
            <select
              className="form-control"
              value={courseId}
              onChange={(e) => setCourseId(e.target.value)}
              disabled={!!editingSection}
            >
              <option value="">-- Select Course --</option>
              {courses.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.code} - {c.name}
                </option>
              ))}
            </select>
          </div>
          <div className="form-grid">
            <div className="form-group">
              <label className="form-label">Section Code / Label</label>
              <input
                type="text"
                className="form-control"
                placeholder="e.g. A, B, FA25-A"
                required
                value={sectionLabel}
                onChange={(e) => setSectionLabel(e.target.value)}
              />
            </div>
            <div className="form-group">
              <label className="form-label">Semester Session</label>
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
          </div>
          <div className="form-group">
            <label className="form-label">Assigned Teacher</label>
            <select
              className="form-control"
              value={teacherId}
              onChange={(e) => setTeacherId(e.target.value)}
            >
              <option value="">-- Select Instructor --</option>
              {teachers.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.full_name} ({t.employee_id})
                </option>
              ))}
            </select>
          </div>
          <div className="form-grid">
            <div className="form-group">
              <label className="form-label">Schedule Slot</label>
              <input
                type="text"
                className="form-control"
                placeholder="e.g. Mon/Wed 9:00-10:30 AM"
                value={schedule}
                onChange={(e) => setSchedule(e.target.value)}
              />
            </div>
            <div className="form-group">
              <label className="form-label">Room / Hall Location</label>
              <input
                type="text"
                className="form-control"
                placeholder="e.g. Room-101"
                value={room}
                onChange={(e) => setRoom(e.target.value)}
              />
            </div>
          </div>
        </form>
      </Modal>
    </div>
  );
}
