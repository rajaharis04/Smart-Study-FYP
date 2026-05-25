import { useState, useEffect } from 'react';
import { enrollmentApi, sectionApi, studentApi } from '../services/api';
import DataTable from '../components/DataTable';
import Modal from '../components/Modal';
import CSVUploader from '../components/CSVUploader';
import { Plus, Upload, Trash2, AlertCircle, CheckSquare, Square } from 'lucide-react';
import { toast } from 'react-hot-toast';

export default function EnrollmentsPage() {
  const [enrollments, setEnrollments] = useState([]);
  const [sections, setSections] = useState([]);
  const [students, setStudents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Modals
  const [enrollModalOpen, setEnrollModalOpen] = useState(false);
  const [uploadModalOpen, setUploadModalOpen] = useState(false);

  // Form states
  const [sectionId, setSectionId] = useState('');
  const [selectedStudentIds, setSelectedStudentIds] = useState([]);
  const [studentSearchQuery, setStudentSearchQuery] = useState('');

  const fetchData = async () => {
    setLoading(true);
    try {
      const [eRes, sRes, stdRes] = await Promise.all([
        enrollmentApi.list(),
        sectionApi.list(),
        studentApi.list()
      ]);
      setEnrollments(eRes.data.filter(e => e.is_active));
      setSections(sRes.data);
      setStudents(stdRes.data.filter(s => s.is_active));
    } catch (err) {
      setError('Failed to load enrollments schema datasets.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const openEnrollModal = () => {
    setSectionId('');
    setSelectedStudentIds([]);
    setStudentSearchQuery('');
    setEnrollModalOpen(true);
  };

  const openUploadModal = () => {
    setSectionId('');
    setUploadModalOpen(true);
  };

  const handleEnrollSubmit = async (e) => {
    e.preventDefault();
    if (!sectionId) {
      toast.error('Please select a class section.');
      return;
    }
    if (selectedStudentIds.length === 0) {
      toast.error('Please select at least one student to enroll.');
      return;
    }

    try {
      const payload = {
        section_id: parseInt(sectionId),
        student_ids: selectedStudentIds.map(id => parseInt(id)),
      };
      const res = await enrollmentApi.enroll(payload);
      toast.success(`Successfully enrolled ${res.data.enrolled} students!`);
      if (res.data.errors && res.data.errors.length > 0) {
        toast.error(`Skipped / Errors: ${res.data.errors.join(', ')}`);
      }
      setEnrollModalOpen(false);
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Enrollment transaction failed.');
    }
  };

  const handleDeactivate = async (id, name, courseCode, sectionLabel) => {
    if (!window.confirm(`Are you sure you want to drop student ${name} from course section ${courseCode} - ${sectionLabel}?`)) return;
    try {
      await enrollmentApi.deactivate(id);
      toast.success('Student dropped from course section successfully');
      fetchData();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to drop student from section.');
    }
  };

  const handleCSVUpload = async (file) => {
    if (!sectionId) {
      throw new Error('Please select a section before uploading the CSV.');
    }
    const formData = new FormData();
    formData.append('file', file);
    const res = await enrollmentApi.bulkUpload(parseInt(sectionId), formData);
    fetchData();
    return res.data;
  };

  const toggleStudentSelection = (id) => {
    if (selectedStudentIds.includes(id)) {
      setSelectedStudentIds(selectedStudentIds.filter(x => x !== id));
    } else {
      setSelectedStudentIds([...selectedStudentIds, id]);
    }
  };

  // Filter students displayed in the checklist search
  const filteredStudents = students.filter(student =>
    student.full_name.toLowerCase().includes(studentSearchQuery.toLowerCase()) ||
    student.reg_number.toLowerCase().includes(studentSearchQuery.toLowerCase())
  );

  const headers = [
    { key: 'student_reg', label: 'Registration No' },
    { key: 'student_name', label: 'Student Name' },
    { key: 'course_name', label: 'Enrolled Course' },
    { key: 'section_label', label: 'Section' },
    { key: 'enrolled_at', label: 'Date Joined', sortable: false },
    { key: 'actions', label: 'Actions', sortable: false },
  ];

  return (
    <div>
      <div className="page-header">
        <div>
          <h1 className="page-title">Class Enrollments</h1>
          <p className="page-subtitle">Assign students to class sections, upload rosters, and manage dropouts.</p>
        </div>
        <div style={{ display: 'flex', gap: '12px' }}>
          <button className="btn btn-secondary" onClick={openUploadModal}>
            <Upload size={16} />
            <span>CSV Bulk Enroll</span>
          </button>
          <button className="btn btn-primary" onClick={openEnrollModal}>
            <Plus size={16} />
            <span>Enroll Students</span>
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
        <div className="loading" style={{ textAlign: 'center', padding: '24px' }}>Loading enrollment rosters...</div>
      ) : (
        <DataTable
          headers={headers}
          data={enrollments}
          searchKeys={['student_name', 'student_reg', 'course_name', 'section_label']}
          searchPlaceholder="Search enrollments..."
          renderRow={(e) => (
            <>
              <td><span className="badge badge-accent">{e.student_reg}</span></td>
              <td>{e.student_name}</td>
              <td>{e.course_name}</td>
              <td><span className="badge badge-info">{e.section_label}</span></td>
              <td>{new Date(e.enrolled_at).toLocaleDateString()}</td>
              <td>
                <button
                  className="btn btn-danger btn-sm btn-icon"
                  onClick={() => handleDeactivate(e.id, e.student_name, e.course_name, e.section_label)}
                  title="Drop Student"
                >
                  <Trash2 size={14} />
                </button>
              </td>
            </>
          )}
        />
      )}

      {/* MANUAL ENROLLMENT MODAL */}
      <Modal
        isOpen={enrollModalOpen}
        onClose={() => setEnrollModalOpen(false)}
        title="Enroll Students to Section"
        footer={
          <>
            <button className="btn btn-secondary" onClick={() => setEnrollModalOpen(false)}>Cancel</button>
            <button className="btn btn-primary" onClick={handleEnrollSubmit}>Enroll Selected</button>
          </>
        }
      >
        <form onSubmit={handleEnrollSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div className="form-group">
            <label className="form-label">Target Class Section</label>
            <select
              className="form-control"
              required
              value={sectionId}
              onChange={(e) => setSectionId(e.target.value)}
            >
              <option value="">-- Select Section --</option>
              {sections.map((sec) => (
                <option key={sec.id} value={sec.id}>
                  {sec.course_code} - {sec.course_name} (Sec {sec.section_label})
                </option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label className="form-label">Search Students</label>
            <input
              type="text"
              className="form-control"
              placeholder="Type name or registration number..."
              value={studentSearchQuery}
              onChange={(e) => setStudentSearchQuery(e.target.value)}
            />
          </div>

          <div className="form-group">
            <label className="form-label">Select Students ({selectedStudentIds.length} chosen)</label>
            <div
              style={{
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-sm)',
                background: 'var(--bg-input)',
                maxHeight: '180px',
                overflowY: 'auto',
                padding: '6px',
                display: 'flex',
                flexDirection: 'column',
                gap: '2px',
              }}
            >
              {filteredStudents.length > 0 ? (
                filteredStudents.map((std) => {
                  const isSelected = selectedStudentIds.includes(std.id);
                  return (
                    <div
                      key={std.id}
                      onClick={() => toggleStudentSelection(std.id)}
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '10px',
                        padding: '8px',
                        borderRadius: 'var(--radius-sm)',
                        cursor: 'pointer',
                        background: isSelected ? 'var(--accent-glow)' : 'transparent',
                        transition: 'background 0.2s',
                      }}
                    >
                      {isSelected ? (
                        <CheckSquare size={16} className="text-success" />
                      ) : (
                        <Square size={16} style={{ color: 'var(--text-muted)' }} />
                      )}
                      <div style={{ display: 'flex', flexDirection: 'column' }}>
                        <span style={{ fontSize: '13px', fontWeight: 500, color: 'var(--text-primary)' }}>
                          {std.full_name}
                        </span>
                        <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
                          {std.reg_number} - {std.batch}
                        </span>
                      </div>
                    </div>
                  );
                })
              ) : (
                <div className="text-muted" style={{ padding: '12px', textAlign: 'center', fontSize: '13px' }}>
                  No students found.
                </div>
              )}
            </div>
          </div>
        </form>
      </Modal>

      {/* CSV UPLOAD ENROLLMENT MODAL */}
      <Modal
        isOpen={uploadModalOpen}
        onClose={() => setUploadModalOpen(false)}
        title="CSV Bulk Enrollment"
        footer={
          <button className="btn btn-secondary w-full" onClick={() => setUploadModalOpen(false)}>Close</button>
        }
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div className="form-group">
            <label className="form-label">Target Class Section</label>
            <select
              className="form-control"
              required
              value={sectionId}
              onChange={(e) => setSectionId(e.target.value)}
            >
              <option value="">-- Select Section --</option>
              {sections.map((sec) => (
                <option key={sec.id} value={sec.id}>
                  {sec.course_code} - {sec.course_name} (Sec {sec.section_label})
                </option>
              ))}
            </select>
          </div>

          <CSVUploader
            title="Upload Enrollment CSV"
            subtitle="Columns: RegNumber"
            onUpload={handleCSVUpload}
          />
          <div style={{ fontSize: '12px', color: 'var(--text-muted)', lineHeight: '1.4' }}>
            <strong>Note:</strong> Select the section first, then drag your CSV list. The spreadsheet should contain a single column named <code>RegNumber</code>. All matching registration numbers will be registered to this section.
          </div>
        </div>
      </Modal>
    </div>
  );
}
