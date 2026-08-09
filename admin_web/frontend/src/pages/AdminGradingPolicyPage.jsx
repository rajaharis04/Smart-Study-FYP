import { useState, useEffect } from 'react';
import { academicSectionApi } from '../services/api';
import { Sliders, Save, Award, CheckCircle, AlertCircle, Loader2, Send } from 'lucide-react';
import toast from 'react-hot-toast';

export default function AdminGradingPolicyPage() {
  const [weights, setWeights] = useState({
    quizzes_weight: 15.0,
    assignments_weight: 15.0,
    midterm_weight: 25.0,
    final_weight: 40.0,
    others_weight: 5.0,
  });
  const [sectionsResults, setSectionsResults] = useState([]);
  const [loading, setLoading] = useState(true);
  const [savingPolicy, setSavingPolicy] = useState(false);
  const [announcingId, setAnnouncingId] = useState(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    setLoading(true);
    try {
      const policyRes = await academicSectionApi.getGradingPolicy();
      setWeights(policyRes.data);

      const resultsRes = await academicSectionApi.getSemesterResults();
      setSectionsResults(resultsRes.data.sections || []);
    } catch (err) {
      toast.error('Failed to load grading policy and semester results.');
    } finally {
      setLoading(false);
    }
  };

  const totalSum = Object.values(weights).reduce((a, b) => (parseFloat(a) || 0) + (parseFloat(b) || 0), 0);

  const handleWeightChange = (field, val) => {
    const num = parseFloat(val) || 0;
    setWeights(prev => ({ ...prev, [field]: num }));
  };

  const handleSavePolicy = async () => {
    if (Math.round(totalSum) !== 100) {
      toast.error(`Total weightage must equal exactly 100%. Current sum: ${totalSum}%`);
      return;
    }

    setSavingPolicy(true);
    try {
      await academicSectionApi.updateGradingPolicy(weights);
      toast.success('Grading policy weightages updated successfully!');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to update policy.');
    } finally {
      setSavingPolicy(false);
    }
  };

  const handleAnnounceResults = async (sectionId) => {
    if (!confirm('Are you sure you want to officially announce and publish final semester results to students? Push notifications will be sent.')) return;
    setAnnouncingId(sectionId);
    try {
      await academicSectionApi.announceSemesterResults(sectionId);
      toast.success('Semester results officially announced!');
      fetchData();
    } catch (err) {
      toast.error('Failed to announce results.');
    } finally {
      setAnnouncingId(null);
    }
  };

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '60vh', color: 'var(--text-muted)' }}>
        <Loader2 size={24} className="spin" /> Loading Grading Policy & Approvals...
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
      {/* Weightage Config Section */}
      <div className="card" style={{ padding: '1.25rem', background: 'var(--bg-secondary)', border: '1px solid var(--border)', borderRadius: '0.75rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <Sliders size={22} style={{ color: 'var(--accent)' }} />
            <div>
              <h3 style={{ margin: 0, fontSize: '1.05rem' }}>Global 100-Mark Grading Formula</h3>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Set percentage weights for automatic semester grade calculation</span>
            </div>
          </div>
          <button className="btn btn-primary" onClick={handleSavePolicy} disabled={savingPolicy || Math.round(totalSum) !== 100}>
            {savingPolicy ? <><Loader2 size={14} className="spin" /> Saving...</> : <><Save size={14} /> Save Weightages</>}
          </button>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '1rem', marginBottom: '1rem' }}>
          <div style={{ background: 'var(--bg-input)', padding: '0.75rem', borderRadius: '0.5rem', border: '1px solid var(--border)' }}>
            <label className="form-label" style={{ fontSize: '0.75rem' }}>Quizzes Weight (%)</label>
            <input type="number" className="input" value={weights.quizzes_weight} onChange={e => handleWeightChange('quizzes_weight', e.target.value)} />
          </div>
          <div style={{ background: 'var(--bg-input)', padding: '0.75rem', borderRadius: '0.5rem', border: '1px solid var(--border)' }}>
            <label className="form-label" style={{ fontSize: '0.75rem' }}>Assignments Weight (%)</label>
            <input type="number" className="input" value={weights.assignments_weight} onChange={e => handleWeightChange('assignments_weight', e.target.value)} />
          </div>
          <div style={{ background: 'var(--bg-input)', padding: '0.75rem', borderRadius: '0.5rem', border: '1px solid var(--border)' }}>
            <label className="form-label" style={{ fontSize: '0.75rem' }}>Midterm Weight (%)</label>
            <input type="number" className="input" value={weights.midterm_weight} onChange={e => handleWeightChange('midterm_weight', e.target.value)} />
          </div>
          <div style={{ background: 'var(--bg-input)', padding: '0.75rem', borderRadius: '0.5rem', border: '1px solid var(--border)' }}>
            <label className="form-label" style={{ fontSize: '0.75rem' }}>Final Exam Weight (%)</label>
            <input type="number" className="input" value={weights.final_weight} onChange={e => handleWeightChange('final_weight', e.target.value)} />
          </div>
          <div style={{ background: 'var(--bg-input)', padding: '0.75rem', borderRadius: '0.5rem', border: '1px solid var(--border)' }}>
            <label className="form-label" style={{ fontSize: '0.75rem' }}>Others / Project (%)</label>
            <input type="number" className="input" value={weights.others_weight} onChange={e => handleWeightChange('others_weight', e.target.value)} />
          </div>
        </div>

        <div style={{ marginBottom: '1rem', padding: '0.75rem 1rem', background: 'var(--bg-input)', borderRadius: '0.5rem', border: '1px solid var(--border)' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.85rem', cursor: 'pointer', fontWeight: 600 }}>
            <input
              type="checkbox"
              checked={weights.drop_lowest_quiz || false}
              onChange={e => setWeights(prev => ({ ...prev, drop_lowest_quiz: e.target.checked }))}
              style={{ accentColor: 'var(--accent)', width: '16px', height: '16px' }}
            />
            Drop lowest quiz score automatically for each student when compiling 100-mark results
          </label>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0.6rem 1rem', background: Math.round(totalSum) === 100 ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.1)', borderRadius: '0.5rem' }}>
          <span style={{ fontSize: '0.85rem', fontWeight: 600, color: Math.round(totalSum) === 100 ? '#10b981' : '#ef4444' }}>
            Total Weightage Sum: {totalSum}%
          </span>
          {Math.round(totalSum) === 100 ? (
            <span style={{ fontSize: '0.75rem', color: '#10b981', display: 'flex', alignItems: 'center', gap: '4px' }}><CheckCircle size={14} /> Formula Valid (100%)</span>
          ) : (
            <span style={{ fontSize: '0.75rem', color: '#ef4444', display: 'flex', alignItems: 'center', gap: '4px' }}><AlertCircle size={14} /> Total must equal 100%</span>
          )}
        </div>
      </div>

      {/* Semester Results Approvals */}
      <div className="card" style={{ padding: '1.25rem', background: 'var(--bg-secondary)', border: '1px solid var(--border)', borderRadius: '0.75rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
          <Award size={22} style={{ color: 'var(--accent)' }} />
          <div>
            <h3 style={{ margin: 0, fontSize: '1.05rem' }}>Semester Results Announcement & Approvals</h3>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Review teacher submissions and publish official results to students</span>
          </div>
        </div>

        {sectionsResults.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>No class sections found.</div>
        ) : (
          <table className="data-table" style={{ width: '100%' }}>
            <thead>
              <tr>
                <th>Course & Section</th>
                <th>Teacher</th>
                <th>Status</th>
                <th>Submitted / Students</th>
                <th>Class Avg</th>
                <th>Pass / Fail</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {sectionsResults.map(sec => (
                <tr key={sec.section_id}>
                  <td>
                    <div style={{ fontWeight: 600 }}>{sec.course_code} - {sec.course_name}</div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Sec {sec.section_label}</div>
                  </td>
                  <td>{sec.teacher_name}</td>
                  <td>
                    <span className={`badge ${sec.status === 'announced' ? 'badge-success' : sec.status === 'submitted' ? 'badge-warning' : 'badge-muted'}`}>
                      {sec.status === 'announced' ? '📢 Announced' : sec.status === 'submitted' ? '⏳ Pending Approval' : 'Draft'}
                    </span>
                  </td>
                  <td>{sec.submitted_count} students</td>
                  <td><strong>{sec.average_score} / 100</strong></td>
                  <td>
                    <span style={{ color: '#10b981', fontWeight: 600 }}>{sec.pass_count} Pass</span> / <span style={{ color: '#ef4444', fontWeight: 600 }}>{sec.fail_count} Fail</span>
                  </td>
                  <td>
                    {sec.status === 'submitted' ? (
                      <button className="btn btn-primary" onClick={() => handleAnnounceResults(sec.section_id)} disabled={announcingId === sec.section_id} style={{ fontSize: '0.75rem', padding: '0.3rem 0.75rem' }}>
                        {announcingId === sec.section_id ? <Loader2 size={12} className="spin" /> : <><Send size={12} /> Announce Results</>}
                      </button>
                    ) : sec.status === 'announced' ? (
                      <span style={{ fontSize: '0.75rem', color: '#10b981', fontWeight: 600 }}>Published</span>
                    ) : (
                      <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Awaiting Teacher Submission</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
