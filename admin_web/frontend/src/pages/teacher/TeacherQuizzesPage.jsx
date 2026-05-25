import { useState, useEffect } from 'react';
import { teacherPortalApi } from '../../services/api';
import { ClipboardList, Users, BarChart3, Edit, Eye, Save, Settings, Calendar, HelpCircle, Check, AlertCircle } from 'lucide-react';
import toast from 'react-hot-toast';

export default function TeacherQuizzesPage() {
  const [quizzes, setQuizzes] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // Tab control: 'quizzes' | 'submissions' | 'analytics'
  const [activeTab, setActiveTab] = useState('quizzes');
  const [selectedQuizId, setSelectedQuizId] = useState(null);
  
  // Details data states
  const [quizDetails, setQuizDetails] = useState(null);
  const [submissions, setSubmissions] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [loadingDetails, setLoadingDetails] = useState(false);

  // Edit states
  const [isEditing, setIsEditing] = useState(false);
  const [editTitle, setEditTitle] = useState('');
  const [editTimeLimit, setEditTimeLimit] = useState(10);
  const [editShowHints, setEditShowHints] = useState(false);
  const [editIsPublished, setEditIsPublished] = useState(false);
  const [editQuestions, setEditQuestions] = useState([]);

  const fetchQuizzesList = async () => {
    try {
      const res = await teacherPortalApi.listQuizzes();
      setQuizzes(res.data);
      if (res.data.length > 0 && !selectedQuizId) {
        setSelectedQuizId(res.data[0].id);
      }
    } catch (err) {
      toast.error('Failed to load quizzes.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQuizzesList();
  }, []);

  const loadTabDetails = async (quizId, tab) => {
    if (!quizId) return;
    setLoadingDetails(true);
    setIsEditing(false);
    try {
      if (tab === 'quizzes') {
        const res = await teacherPortalApi.getQuiz(quizId);
        setQuizDetails(res.data);
        setEditTitle(res.data.title);
        setEditTimeLimit(res.data.time_limit_mins || 10);
        setEditShowHints(res.data.show_hints);
        setEditIsPublished(res.data.is_published);
        setEditQuestions(res.data.questions || []);
      } else if (tab === 'submissions') {
        const res = await teacherPortalApi.getQuizSubmissions(quizId);
        setSubmissions(res.data);
      } else if (tab === 'analytics') {
        const res = await teacherPortalApi.getQuizAnalytics(quizId);
        setAnalytics(res.data);
      }
    } catch (err) {
      toast.error('Failed to fetch details.');
    } finally {
      setLoadingDetails(false);
    }
  };

  useEffect(() => {
    if (selectedQuizId) {
      loadTabDetails(selectedQuizId, activeTab);
    }
  }, [selectedQuizId, activeTab]);

  const handleEditQuestion = (index, field, value) => {
    setEditQuestions(prev => {
      const copy = [...prev];
      copy[index] = { ...copy[index], [field]: value };
      return copy;
    });
  };

  const handleAddQuestion = () => {
    setEditQuestions(prev => [
      ...prev,
      {
        question_text: '',
        option_a: '',
        option_b: '',
        option_c: '',
        option_d: '',
        correct_answer: 'A',
        difficulty: 'medium'
      }
    ]);
  };

  const handleRemoveQuestion = (index) => {
    setEditQuestions(prev => prev.filter((_, i) => i !== index));
  };

  const handleSaveQuizSettings = async (e) => {
    e.preventDefault();
    if (!editTitle.trim()) {
      toast.error('Quiz title is required.');
      return;
    }

    try {
      const data = {
        title: editTitle,
        is_published: editIsPublished,
        time_limit_mins: editTimeLimit,
        show_hints: editShowHints,
        questions: editQuestions.map(q => ({
          question_text: q.question_text,
          option_a: q.option_a,
          option_b: q.option_b,
          option_c: q.option_c,
          option_d: q.option_d,
          correct_answer: q.correct_answer,
          difficulty: q.difficulty
        }))
      };

      await teacherPortalApi.updateQuiz(selectedQuizId, data);
      toast.success('Quiz configurations and questions successfully saved!');
      setIsEditing(false);
      fetchQuizzesList();
      loadTabDetails(selectedQuizId, 'quizzes');
    } catch (err) {
      toast.error('Failed to update quiz settings.');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center" style={{ minHeight: '60vh' }}>
        <div className="loading" style={{ fontSize: '18px' }}>Loading Quiz Panel...</div>
      </div>
    );
  }

  const selectedQuizInfo = quizzes.find(q => q.id === selectedQuizId);

  return (
    <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 3fr', gap: '28px' }}>
      
      {/* Left Column: Quiz Selector List */}
      <div className="card" style={{ height: 'fit-content' }}>
        <div className="card-header">
          <h3 className="card-title flex items-center gap-2">
            <ClipboardList size={18} className="text-accent" />
            Class Quizzes
          </h3>
        </div>
        <div className="card-body" style={{ display: 'flex', flexDirection: 'column', gap: '10px', padding: '16px' }}>
          {quizzes.length === 0 ? (
            <div className="empty-state" style={{ padding: '24px 8px' }}>
              <p>No quizzes available yet.</p>
            </div>
          ) : (
            quizzes.map((q) => (
              <div 
                key={q.id}
                onClick={() => setSelectedQuizId(q.id)}
                className={`card ${selectedQuizId === q.id ? 'active' : ''}`}
                style={{ 
                  padding: '12px 16px', 
                  cursor: 'pointer',
                  borderColor: selectedQuizId === q.id ? 'var(--accent)' : 'var(--border)',
                  background: selectedQuizId === q.id ? 'var(--accent-glow)' : 'rgba(255,255,255,0.01)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '4px'
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '14px', fontWeight: '700', color: selectedQuizId === q.id ? 'var(--accent-light)' : 'var(--text-primary)' }}>
                    {q.title || `${q.quiz_type.toUpperCase()} - ${q.lecture_title}`}
                  </span>
                  {q.is_published ? (
                    <span className="badge badge-success" style={{ fontSize: '8px' }}>Live</span>
                  ) : (
                    <span className="badge badge-warning" style={{ fontSize: '8px' }}>Draft</span>
                  )}
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
                  {q.course_name} (Sec {q.section_label})
                </div>
                <div style={{ fontSize: '11px', color: 'var(--text-muted)', display: 'flex', justifyContent: 'space-between', marginTop: '4px' }}>
                  <span>Q's: {q.questions_count}</span>
                  <span>Attempts: {q.attempts_count}</span>
                </div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Right Column: Tab Panels */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        
        {/* Navigation Tabs */}
        <div 
          className="card" 
          style={{ 
            padding: '8px 16px', 
            display: 'flex', 
            gap: '12px',
            background: 'var(--bg-secondary)',
            borderColor: 'var(--border)'
          }}
        >
          <button 
            className={`btn ${activeTab === 'quizzes' ? 'btn-primary' : 'btn-secondary'} btn-sm`}
            onClick={() => setActiveTab('quizzes')}
            disabled={!selectedQuizId}
          >
            <Settings size={14} />
            Quiz settings & questions
          </button>
          
          <button 
            className={`btn ${activeTab === 'submissions' ? 'btn-primary' : 'btn-secondary'} btn-sm`}
            onClick={() => setActiveTab('submissions')}
            disabled={!selectedQuizId}
          >
            <Users size={14} />
            Attempts Tracker
          </button>
          
          <button 
            className={`btn ${activeTab === 'analytics' ? 'btn-primary' : 'btn-secondary'} btn-sm`}
            onClick={() => setActiveTab('analytics')}
            disabled={!selectedQuizId}
          >
            <BarChart3 size={14} />
            Item Analysis
          </button>
        </div>

        {/* Tab Detail Pane */}
        {loadingDetails ? (
          <div className="card flex items-center justify-center" style={{ minHeight: '40vh', padding: '32px' }}>
            <div className="loading" style={{ color: 'var(--text-secondary)' }}>Fetching data...</div>
          </div>
        ) : (
          selectedQuizId && (
            <div className="card" style={{ padding: '24px' }}>
              
              {/* TAB 1: Quiz Settings & Questions */}
              {activeTab === 'quizzes' && quizDetails && (
                <form onSubmit={handleSaveQuizSettings} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                  
                  {/* Header Title */}
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border)', paddingBottom: '16px' }}>
                    <h3 style={{ fontSize: '18px', fontWeight: '600' }}>Quiz Settings</h3>
                    {!isEditing ? (
                      <button type="button" className="btn btn-secondary btn-sm" onClick={() => setIsEditing(true)}>
                        <Edit size={14} /> Edit Configuration
                      </button>
                    ) : (
                      <div className="flex gap-2">
                        <button type="button" className="btn btn-secondary btn-sm" onClick={() => { setIsEditing(false); loadTabDetails(selectedQuizId, 'quizzes'); }}>
                          Cancel
                        </button>
                        <button type="submit" className="btn btn-primary btn-sm">
                          <Save size={14} /> Save Settings
                        </button>
                      </div>
                    )}
                  </div>

                  {/* Settings Input Grid */}
                  <div className="form-grid-3">
                    <div className="form-group">
                      <label className="form-label">Quiz Title</label>
                      <input
                        type="text"
                        className="form-control"
                        required
                        disabled={!isEditing}
                        value={editTitle}
                        onChange={(e) => setEditTitle(e.target.value)}
                      />
                    </div>
                    <div className="form-group">
                      <label className="form-label">Time Limit (mins)</label>
                      <input
                        type="number"
                        min={1}
                        className="form-control"
                        required
                        disabled={!isEditing}
                        value={editTimeLimit}
                        onChange={(e) => setEditTimeLimit(parseInt(e.target.value))}
                      />
                    </div>
                    <div className="form-group">
                      <label className="form-label">Status</label>
                      <select 
                        className="form-control" 
                        disabled={!isEditing}
                        value={editIsPublished ? 'true' : 'false'}
                        onChange={(e) => setEditIsPublished(e.target.value === 'true')}
                      >
                        <option value="true">Live (Students can attempt)</option>
                        <option value="false">Draft / Saved</option>
                      </select>
                    </div>
                  </div>

                  <div className="form-group" style={{ flexDirection: 'row', gap: '8px', alignItems: 'center' }}>
                    <input 
                      type="checkbox"
                      id="show-hints-check"
                      disabled={!isEditing}
                      checked={editShowHints}
                      onChange={(e) => setEditShowHints(e.target.checked)}
                      style={{ width: '16px', height: '16px', cursor: isEditing ? 'pointer' : 'not-allowed' }}
                    />
                    <label htmlFor="show-hints-check" className="form-label" style={{ margin: 0 }}>
                      Enable Hints (shows student helpful text during quiz)
                    </label>
                  </div>

                  {/* Questions Section */}
                  <div style={{ borderTop: '1px solid var(--border)', paddingTop: '20px', marginTop: '10px' }}>
                    <h4 style={{ fontSize: '15px', fontWeight: '600', marginBottom: '16px' }}>Quiz Questions ({editQuestions.length})</h4>
                    
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                      {editQuestions.map((q, qIndex) => (
                        <div 
                          key={q.id || qIndex} 
                          className="card" 
                          style={{ 
                            padding: '16px', 
                            background: 'rgba(255,255,255,0.01)', 
                            borderLeft: '3px solid var(--accent)',
                            display: 'flex',
                            flexDirection: 'column',
                            gap: '12px'
                          }}
                        >
                          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <span style={{ fontSize: '13px', fontWeight: '700', color: 'var(--text-secondary)' }}>Question #{qIndex + 1}</span>
                            <div className="flex items-center gap-2">
                              {isEditing && (
                                <button
                                  type="button"
                                  className="btn btn-secondary btn-sm"
                                  style={{ padding: '2px 8px', fontSize: '11px', color: 'var(--danger)', borderColor: 'var(--danger)', background: 'transparent' }}
                                  onClick={() => handleRemoveQuestion(qIndex)}
                                >
                                  Delete
                                </button>
                              )}
                              <span className={`badge ${
                                q.difficulty === 'easy' ? 'badge-success' : (q.difficulty === 'medium' ? 'badge-warning' : 'badge-danger')
                              }`}>
                                {q.difficulty}
                              </span>
                            </div>
                          </div>

                          <div className="form-group">
                            <label className="form-label">Question Text</label>
                            <input 
                              type="text" 
                              className="form-control"
                              disabled={!isEditing}
                              value={q.question_text}
                              onChange={(e) => handleEditQuestion(qIndex, 'question_text', e.target.value)}
                            />
                          </div>

                          <div className="form-grid">
                            <div className="form-group">
                              <label className="form-label">Option A</label>
                              <input 
                                type="text" 
                                className="form-control"
                                disabled={!isEditing}
                                value={q.option_a}
                                onChange={(e) => handleEditQuestion(qIndex, 'option_a', e.target.value)}
                              />
                            </div>
                            <div className="form-group">
                              <label className="form-label">Option B</label>
                              <input 
                                type="text" 
                                className="form-control"
                                disabled={!isEditing}
                                value={q.option_b}
                                onChange={(e) => handleEditQuestion(qIndex, 'option_b', e.target.value)}
                              />
                            </div>
                          </div>

                          <div className="form-grid">
                            <div className="form-group">
                              <label className="form-label">Option C</label>
                              <input 
                                type="text" 
                                className="form-control"
                                disabled={!isEditing}
                                value={q.option_c}
                                onChange={(e) => handleEditQuestion(qIndex, 'option_c', e.target.value)}
                              />
                            </div>
                            <div className="form-group">
                              <label className="form-label">Option D</label>
                              <input 
                                type="text" 
                                className="form-control"
                                disabled={!isEditing}
                                value={q.option_d}
                                onChange={(e) => handleEditQuestion(qIndex, 'option_d', e.target.value)}
                              />
                            </div>
                          </div>

                          <div className="form-grid">
                            <div className="form-group">
                              <label className="form-label">Correct Answer</label>
                              <select 
                                className="form-control"
                                disabled={!isEditing}
                                value={q.correct_answer}
                                onChange={(e) => handleEditQuestion(qIndex, 'correct_answer', e.target.value)}
                              >
                                <option value="A">Option A</option>
                                <option value="B">Option B</option>
                                <option value="C">Option C</option>
                                <option value="D">Option D</option>
                              </select>
                            </div>
                            <div className="form-group">
                              <label className="form-label">Difficulty Scale</label>
                              <select 
                                className="form-control"
                                disabled={!isEditing}
                                value={q.difficulty}
                                onChange={(e) => handleEditQuestion(qIndex, 'difficulty', e.target.value)}
                              >
                                <option value="easy">Easy</option>
                                <option value="medium">Medium</option>
                                <option value="hard">Hard</option>
                              </select>
                            </div>
                          </div>

                        </div>
                      ))}
                      {isEditing && (
                        <button
                          type="button"
                          className="btn btn-secondary"
                          onClick={handleAddQuestion}
                          style={{ alignSelf: 'flex-start', marginTop: '10px' }}
                        >
                          + Add Question
                        </button>
                      )}
                    </div>
                  </div>

                </form>
              )}

              {/* TAB 2: Submissions Tracker */}
              {activeTab === 'submissions' && (
                <div>
                  <h3 style={{ fontSize: '16px', fontWeight: '600', marginBottom: '16px', borderBottom: '1px solid var(--border)', paddingBottom: '12px' }}>
                    Student Attempts Tracker - {selectedQuizInfo?.title}
                  </h3>
                  
                  {submissions.length === 0 ? (
                    <div className="empty-state">
                      <Users size={32} className="text-muted" style={{ margin: '0 auto 12px' }} />
                      <h3>No submissions yet</h3>
                      <p>Once students start attempting this post quiz on their devices, they will appear here in real-time.</p>
                    </div>
                  ) : (
                    <div className="table-wrapper">
                      <table className="data-table">
                        <thead>
                          <tr>
                            <th>Student Name</th>
                            <th>Registration ID</th>
                            <th>Correct Qs</th>
                            <th>Mastery Grade</th>
                            <th>Attempt Timestamp</th>
                          </tr>
                        </thead>
                        <tbody>
                          {submissions.map((sub, sIdx) => (
                            <tr key={sIdx}>
                              <td>{sub.student_name}</td>
                              <td>{sub.reg_number}</td>
                              <td>{sub.correct_count} / {sub.total_questions}</td>
                              <td>
                                <span className={`badge ${sub.score_percentage >= 50 ? 'badge-success' : 'badge-danger'}`}>
                                  {sub.score_percentage}%
                                </span>
                              </td>
                              <td>{new Date(sub.submitted_at).toLocaleString()}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  )}
                </div>
              )}

              {/* TAB 3: Item Analysis */}
              {activeTab === 'analytics' && analytics && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border)', paddingBottom: '12px' }}>
                    <h3 style={{ fontSize: '16px', fontWeight: '600' }}>Class Analytics Summary</h3>
                    <div style={{ display: 'flex', gap: '20px' }}>
                      <div style={{ textAlign: 'right' }}>
                        <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Total Attempts</span>
                        <h4 style={{ fontSize: '18px', fontWeight: '700' }}>{analytics.attempts_count}</h4>
                      </div>
                      <div style={{ textAlign: 'right' }}>
                        <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Class Average</span>
                        <h4 style={{ fontSize: '18px', fontWeight: '700', color: 'var(--success)' }}>{analytics.avg_score}%</h4>
                      </div>
                    </div>
                  </div>

                  <div>
                    <h4 style={{ fontSize: '14px', fontWeight: '600', marginBottom: '12px', color: 'var(--text-secondary)' }}>
                      Question Difficulty Distribution (Ordered by success rate)
                    </h4>
                    
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                      {analytics.question_performance.map((qPerf, qIdx) => (
                        <div 
                          key={qPerf.question_id}
                          style={{
                            background: 'rgba(255,255,255,0.01)',
                            border: '1px solid var(--border)',
                            borderRadius: 'var(--radius-sm)',
                            padding: '12px 16px',
                            display: 'flex',
                            justifyContent: 'space-between',
                            alignItems: 'center'
                          }}
                        >
                          <div style={{ flex: 1, marginRight: '24px' }}>
                            <p style={{ fontSize: '13px', fontWeight: '500', color: 'var(--text-primary)' }}>
                              Q{qIdx + 1}: {qPerf.question_text}
                            </p>
                            <div style={{ width: '100%', display: 'flex', alignItems: 'center', gap: '10px', marginTop: '6px' }}>
                              <div style={{ flex: 1, height: '4px', background: 'var(--border)', borderRadius: '2px', overflow: 'hidden' }}>
                                <div 
                                  style={{ 
                                    width: `${qPerf.success_rate}%`, 
                                    height: '100%', 
                                    background: qPerf.success_rate < 50 ? 'var(--danger)' : (qPerf.success_rate < 75 ? 'var(--warning)' : 'var(--success)') 
                                  }} 
                                />
                              </div>
                              <span style={{ fontSize: '11px', fontWeight: 'bold', color: 'var(--text-secondary)', width: '32px' }}>
                                {qPerf.success_rate}%
                              </span>
                            </div>
                          </div>
                          <span className={`badge ${
                            qPerf.difficulty_rating === 'Easy' ? 'badge-success' : (qPerf.difficulty_rating === 'Medium' ? 'badge-warning' : 'badge-danger')
                          }`}>
                            {qPerf.difficulty_rating}
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>

                </div>
              )}

            </div>
          )
        )}
      </div>

    </div>
  );
}
