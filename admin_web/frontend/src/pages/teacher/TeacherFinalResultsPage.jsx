import { useState, useEffect } from 'react';
import { teacherPortalApi } from '../../services/api';
import { Award, Send, Loader2, CheckCircle, Sliders } from 'lucide-react';
import toast from 'react-hot-toast';

export default function TeacherFinalResultsPage() {
  const [sections, setSections] = useState([]);
  const [selectedSectionId, setSelectedSectionId] = useState(null);
  const [resultsData, setResultsData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [loadingResults, setLoadingResults] = useState(false);
  const [submitting, setSubmitting] = useState(false);

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
      fetchCompiledResults(selectedSectionId);
    }
  }, [selectedSectionId]);

  const fetchCompiledResults = async (sectionId) => {
    setLoadingResults(true);
    try {
      const res = await teacherPortalApi.getCompiledResults(sectionId);
      setResultsData(res.data);
    } catch (err) {
      toast.error('Failed to compile 100-mark results.');
      setResultsData(null);
    } finally {
      setLoadingResults(false);
    }
  };

  const handleSubmitToAdmin = async () => {
    if (!selectedSectionId) return;
    if (!confirm('Submit compiled 100-mark final results to Admin for review and official announcement?')) return;
    setSubmitting(true);
    try {
      await teacherPortalApi.submitFinalResults(selectedSectionId);
      toast.success('Final semester grades submitted to Admin successfully!');
      fetchCompiledResults(selectedSectionId);
    } catch (err) {
      toast.error('Failed to submit results.');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '60vh', color: 'var(--text-muted)' }}>
        <Loader2 size={24} className="spin" /> Compiling Semester Results...
      </div>
    );
  }

  const policy = resultsData?.policy || { quizzes_weight: 15, assignments_weight: 15, midterm_weight: 25, final_weight: 40, others_weight: 5 };
  const students = resultsData?.students || [];
  const status = resultsData?.submission_status || 'draft';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
      {/* Top Header Card */}
      <div className="card" style={{ padding: '1rem 1.25rem', background: 'var(--bg-secondary)', border: '1px solid var(--border)', borderRadius: '0.75rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <Award size={24} style={{ color: 'var(--accent)' }} />
            <div>
              <h3 style={{ margin: 0, fontSize: '1.1rem' }}>End-of-Semester 100-Mark Results Compiler</h3>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Auto-calculated weighted average based on Admin grading formula</span>
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

            {status === 'announced' ? (
              <span className="badge badge-success" style={{ fontSize: '0.85rem', padding: '0.4rem 0.75rem' }}>
                📢 Results Announced
              </span>
            ) : status === 'submitted' ? (
              <span className="badge badge-warning" style={{ fontSize: '0.85rem', padding: '0.4rem 0.75rem' }}>
                ⏳ Submitted to Admin
              </span>
            ) : (
              <button className="btn btn-primary" onClick={handleSubmitToAdmin} disabled={submitting || students.length === 0}>
                {submitting ? <><Loader2 size={14} className="spin" /> Submitting...</> : <><Send size={14} /> Submit Final Results to Admin</>}
              </button>
            )}
          </div>
        </div>

        {/* Formula Weightage Chips */}
        <div style={{ display: 'flex', gap: '0.75rem', marginTop: '0.85rem', paddingTop: '0.75rem', borderTop: '1px solid var(--border)', flexWrap: 'wrap' }}>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '4px' }}><Sliders size={12} /> Formula Weights:</span>
          <span className="badge badge-info">Quizzes: {policy.quizzes_weight}%</span>
          <span className="badge badge-info">Assignments: {policy.assignments_weight}%</span>
          <span className="badge badge-info">Midterm: {policy.midterm_weight}%</span>
          <span className="badge badge-info">Final Exam: {policy.final_weight}%</span>
          <span className="badge badge-info">Others: {policy.others_weight}%</span>
          <span className="badge badge-success" style={{ marginLeft: 'auto' }}>Total: 100%</span>
        </div>
      </div>

      {/* Main Results Breakdown Table */}
      <div className="card" style={{ padding: '1.25rem', background: 'var(--bg-secondary)', border: '1px solid var(--border)', borderRadius: '0.75rem' }}>
        {loadingResults ? (
          <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
            <Loader2 size={24} className="spin" /> Calculating 100-mark weighted scores...
          </div>
        ) : students.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}>No enrolled students in this section.</div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table className="data-table" style={{ width: '100%' }}>
              <thead>
                <tr>
                  <th>Student Name</th>
                  <th>Reg #</th>
                  <th>Quizzes ({policy.quizzes_weight}%)</th>
                  <th>Assignments ({policy.assignments_weight}%)</th>
                  <th>Midterm ({policy.midterm_weight}%)</th>
                  <th>Final ({policy.final_weight}%)</th>
                  <th>Others ({policy.others_weight}%)</th>
                  <th>Total Score (/100)</th>
                  <th>Grade</th>
                  <th>GPA</th>
                </tr>
              </thead>
              <tbody>
                {students.map((st, idx) => (
                  <tr key={st.student_id}>
                    <td><strong>{st.student_name}</strong></td>
                    <td style={{ fontSize: '0.85rem' }}>{st.reg_number}</td>
                    <td>{st.quizzes_comp}</td>
                    <td>{st.assignments_comp}</td>
                    <td>{st.midterm_comp}</td>
                    <td>{st.final_comp}</td>
                    <td>{st.others_comp}</td>
                    <td><strong>{st.total_weighted_score}</strong></td>
                    <td>
                      <span className={`badge ${st.letter_grade === 'A' ? 'badge-success' : st.letter_grade === 'F' ? 'badge-danger' : 'badge-warning'}`}>
                        Grade {st.letter_grade}
                      </span>
                    </td>
                    <td><strong>{st.gpa.toFixed(1)}</strong></td>
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
