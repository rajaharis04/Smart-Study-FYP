import { useState, useEffect } from 'react';
import { teacherPortalApi } from '../../services/api';
import { FileSpreadsheet, Save, Loader2, Award } from 'lucide-react';
import toast from 'react-hot-toast';

export default function TeacherExamGradesPage() {
  const [sections, setSections] = useState([]);
  const [selectedSectionId, setSelectedSectionId] = useState(null);
  const [students, setStudents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadingGrades, setLoadingGrades] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    fetchSections();
  }, []);

  const fetchSections = async () => {
    try {
      const res = await teacherPortalApi.sections();
      setSections(res.data);
      if (res.data.length > 0) {
        setSelectedSectionId(res.data[0].id);
      }
    } catch (err) {
      toast.error('Failed to load class sections.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (selectedSectionId) {
      fetchExamGrades(selectedSectionId);
    }
  }, [selectedSectionId]);

  const fetchExamGrades = async (sectionId) => {
    setLoadingGrades(true);
    try {
      const res = await teacherPortalApi.getSectionExamGrades(sectionId);
      setStudents(res.data.students || []);
    } catch (err) {
      toast.error('Failed to load exam grades.');
      setStudents([]);
    } finally {
      setLoadingGrades(false);
    }
  };

  const handleScoreChange = (index, field, value) => {
    const parsed = parseFloat(value) || 0;
    setStudents(prev => {
      const copy = [...prev];
      copy[index] = { ...copy[index], [field]: parsed };
      return copy;
    });
  };

  const handleMaxMarksChange = (field, value) => {
    const parsed = parseFloat(value) || 0;
    setStudents(prev => prev.map(s => ({ ...s, [field]: parsed })));
  };

  const handleSaveAll = async () => {
    if (!selectedSectionId) return;
    setSaving(true);
    try {
      await teacherPortalApi.saveSectionExamGrades(selectedSectionId, { students });
      toast.success('Exam grades saved successfully!');
    } catch (err) {
      toast.error('Failed to save exam grades.');
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '60vh', color: 'var(--text-muted)' }}>
        <Loader2 size={24} className="spin" /> Loading Exam Grades...
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* Top Bar */}
      <div className="card" style={{ padding: '1rem 1.25rem', background: 'var(--bg-secondary)', border: '1px solid var(--border)', borderRadius: '0.75rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <Award size={22} style={{ color: 'var(--accent)' }} />
            <div>
              <h3 style={{ margin: 0, fontSize: '1.05rem' }}>Exams & Other Evaluation Marks</h3>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Set Max Marks and enter Midterm, Final Exam & Others scores</span>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <select
              className="input"
              style={{ width: '240px' }}
              value={selectedSectionId || ''}
              onChange={e => setSelectedSectionId(parseInt(e.target.value))}
            >
              {sections.map(s => (
                <option key={s.id} value={s.id}>{s.course_code} - {s.section_label}</option>
              ))}
            </select>

            <button className="btn btn-primary" onClick={handleSaveAll} disabled={saving || students.length === 0}>
              {saving ? <><Loader2 size={14} className="spin" /> Saving...</> : <><Save size={14} /> Save Grades</>}
            </button>
          </div>
        </div>
      </div>

      {/* Main Table */}
      <div className="card" style={{ padding: '1.25rem', background: 'var(--bg-secondary)', border: '1px solid var(--border)', borderRadius: '0.75rem' }}>
        {loadingGrades ? (
          <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
            <Loader2 size={24} className="spin" /> Loading class roster...
          </div>
        ) : students.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
            <FileSpreadsheet size={40} style={{ opacity: 0.3, marginBottom: '0.5rem' }} />
            <p>No enrolled students found in this section.</p>
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table className="data-table" style={{ width: '100%' }}>
              <thead>
                <tr>
                  <th>Student Name</th>
                  <th>Reg / Roll #</th>
                  <th>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                      <span>Midterm Exam</span>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.75rem', fontWeight: 'normal', color: 'var(--text-muted)' }}>
                        <span>Max:</span>
                        <input
                          type="number"
                          className="input"
                          style={{ width: '65px', padding: '0.15rem 0.35rem', fontSize: '0.75rem' }}
                          value={students[0]?.midterm_max ?? 30}
                          onChange={e => handleMaxMarksChange('midterm_max', e.target.value)}
                        />
                      </div>
                    </div>
                  </th>
                  <th>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                      <span>Final Exam</span>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.75rem', fontWeight: 'normal', color: 'var(--text-muted)' }}>
                        <span>Max:</span>
                        <input
                          type="number"
                          className="input"
                          style={{ width: '65px', padding: '0.15rem 0.35rem', fontSize: '0.75rem' }}
                          value={students[0]?.final_max ?? 50}
                          onChange={e => handleMaxMarksChange('final_max', e.target.value)}
                        />
                      </div>
                    </div>
                  </th>
                  <th>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                      <span>Others / Presentation</span>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.75rem', fontWeight: 'normal', color: 'var(--text-muted)' }}>
                        <span>Max:</span>
                        <input
                          type="number"
                          className="input"
                          style={{ width: '65px', padding: '0.15rem 0.35rem', fontSize: '0.75rem' }}
                          value={students[0]?.others_max ?? 20}
                          onChange={e => handleMaxMarksChange('others_max', e.target.value)}
                        />
                      </div>
                    </div>
                  </th>
                </tr>
              </thead>
              <tbody>
                {students.map((st, idx) => (
                  <tr key={st.student_id}>
                    <td>
                      <div style={{ fontWeight: 600 }}>{st.student_name}</div>
                      <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{st.student_email}</div>
                    </td>
                    <td style={{ fontSize: '0.85rem' }}>{st.reg_number}</td>
                    <td>
                      <input
                        type="number"
                        className="input"
                        style={{ width: '90px' }}
                        min={0}
                        max={st.midterm_max || 30}
                        value={st.midterm_score}
                        onChange={e => handleScoreChange(idx, 'midterm_score', e.target.value)}
                      />
                    </td>
                    <td>
                      <input
                        type="number"
                        className="input"
                        style={{ width: '90px' }}
                        min={0}
                        max={st.final_max || 50}
                        value={st.final_score}
                        onChange={e => handleScoreChange(idx, 'final_score', e.target.value)}
                      />
                    </td>
                    <td>
                      <input
                        type="number"
                        className="input"
                        style={{ width: '90px' }}
                        min={0}
                        max={st.others_max || 20}
                        value={st.others_score}
                        onChange={e => handleScoreChange(idx, 'others_score', e.target.value)}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
