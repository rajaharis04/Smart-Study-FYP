import { useState, useEffect, useRef, useCallback } from 'react';
import { teacherPortalApi } from '../../services/api';
import { FileText, Plus, Edit, Trash2, Eye, Save, X, ChevronRight, Loader2, Sparkles, Brain, BookOpen, Check, AlertCircle, Calendar, Wand2, CheckCircle2, Clock, ClipboardList, Users, BarChart3, AlertTriangle, RotateCcw, HelpCircle, Video, ExternalLink } from 'lucide-react';
import toast from 'react-hot-toast';

export default function TeacherAssignmentsPage() {
  const [sections, setSections] = useState([]);
  const [selectedSectionId, setSelectedSectionId] = useState(null);
  const [assignments, setAssignments] = useState([]);
  const [loading, setLoading] = useState(true);

  // Tab control: 'questions' | 'submissions' | 'analytics'
  const [activeTab, setActiveTab] = useState('questions');
  const [assignmentFilterTab, setAssignmentFilterTab] = useState('active'); // 'active' | 'completed'
  const [submissions, setSubmissions] = useState([]);
  const [analytics, setAnalytics] = useState(null);

  // Detail view
  const [selectedAssignmentId, setSelectedAssignmentId] = useState(null);
  const [assignmentDetails, setAssignmentDetails] = useState(null);
  const [loadingDetails, setLoadingDetails] = useState(false);
  const [isEditing, setIsEditing] = useState(false);

  // Edit states
  const [editTitle, setEditTitle] = useState('');
  const [editDescription, setEditDescription] = useState('');
  const [editDueDate, setEditDueDate] = useState('');
  const [editTotalMarks, setEditTotalMarks] = useState(100);
  const [editIsPublished, setEditIsPublished] = useState(false);
  const [editQuestions, setEditQuestions] = useState([]);

  // Student Submission Evaluation Modal states
  const [selectedSubmissionId, setSelectedSubmissionId] = useState(null);
  const [submissionDetails, setSubmissionDetails] = useState(null);
  const [loadingSubmission, setLoadingSubmission] = useState(false);
  const [evaluatingAI, setEvaluatingAI] = useState(false);
  const [aiEvaluationResult, setAiEvaluationResult] = useState(null);
  const [marksAwardedMap, setMarksAwardedMap] = useState({});
  const [savingGrade, setSavingGrade] = useState(false);

  // Regrade Requests states
  const [regradeRequests, setRegradeRequests] = useState([]);
  const [showRegradeModal, setShowRegradeModal] = useState(false);
  const [loadingRegrades, setLoadingRegrades] = useState(false);

  const fetchRegradeRequests = async () => {
    setLoadingRegrades(true);
    try {
      const res = await teacherPortalApi.getRegradeRequests();
      setRegradeRequests(res.data.requests || []);
      setShowRegradeModal(true);
    } catch (err) {
      toast.error('Failed to load regrade requests.');
    } finally {
      setLoadingRegrades(false);
    }
  };

  const handleRespondRegrade = async (reqId, status, adjustedMarks, feedback) => {
    try {
      await teacherPortalApi.respondRegradeRequest(reqId, {
        status,
        adjusted_marks: adjustedMarks,
        teacher_feedback: feedback
      });
      toast.success(`Regrade request ${status}!`);
      fetchRegradeRequests();
    } catch (err) {
      toast.error('Failed to respond to regrade request.');
    }
  };

  // Create wizard
  const [showCreateWizard, setShowCreateWizard] = useState(false);
  const [createMode, setCreateMode] = useState('manual');
  const [wizardStep, setWizardStep] = useState(1);

  // Manual create
  const [newTitle, setNewTitle] = useState('');
  const [newDescription, setNewDescription] = useState('');
  const [newDueDate, setNewDueDate] = useState('');
  const [newTotalMarks, setNewTotalMarks] = useState(100);
  const [newIsPublished, setNewIsPublished] = useState(false);
  const [newQuestions, setNewQuestions] = useState([{
    question_text: '', question_type: 'short_answer', marks: 5, difficulty: 'medium'
  }]);

  // AI states
  const [availableMaterials, setAvailableMaterials] = useState([]);
  const [selectedMaterialIds, setSelectedMaterialIds] = useState([]);
  const [aiNumQuestions, setAiNumQuestions] = useState(10);
  const [aiDifficulty, setAiDifficulty] = useState('medium');
  const [aiQuestionTypes, setAiQuestionTypes] = useState(['short_answer', 'long_answer']);
  const [aiGeneratedQuestions, setAiGeneratedQuestions] = useState([]);
  const [aiGenerating, setAiGenerating] = useState(false);
  const [aiSaveTitle, setAiSaveTitle] = useState('');
  const [aiSaveDescription, setAiSaveDescription] = useState('');
  const [aiSaveDueDate, setAiSaveDueDate] = useState('');
  const [aiSaveTotalMarks, setAiSaveTotalMarks] = useState(100);
  const [aiSaveIsPublished, setAiSaveIsPublished] = useState(false);
  const [savingAI, setSavingAI] = useState(false);

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
    } catch (err) { toast.error('Failed to load sections.'); }
    finally { setLoading(false); }
  };

  useEffect(() => {
    if (selectedSectionId) {
      fetchAssignments(selectedSectionId);
    }
  }, [selectedSectionId]);

  useEffect(() => {
    if (selectedAssignmentId) {
      fetchAssignmentDetails(selectedAssignmentId);
    } else {
      setAssignmentDetails(null);
    }
  }, [selectedAssignmentId]);

  const fetchAssignments = async (sectionId) => {
    setLoading(true);
    try {
      const res = await teacherPortalApi.listAssignments(sectionId);
      const list = res.data || [];
      setAssignments(list);

      const activeList = list.filter(a => a.is_published && !a.is_deleted && (!a.due_date || new Date(a.due_date) >= new Date()));
      if (activeList.length > 0 && !selectedAssignmentId) {
        setSelectedAssignmentId(activeList[0].id);
      } else if (activeList.length === 0) {
        setSelectedAssignmentId(null);
      }
    } catch (err) {
      toast.error('Failed to load assignments.');
      setAssignments([]);
      setSelectedAssignmentId(null);
      setAssignmentDetails(null);
    } finally {
      setLoading(false);
    }
  };

  const fetchAssignmentDetails = async (id) => {
    setLoadingDetails(true);
    try {
      const res = await teacherPortalApi.getAssignment(id);
      setAssignmentDetails(res.data);
      setEditTitle(res.data.title);
      setEditDescription(res.data.description || '');
      setEditDueDate(res.data.due_date ? new Date(res.data.due_date).toISOString().slice(0, 16) : '');
      setEditTotalMarks(res.data.total_marks);
      setEditIsPublished(res.data.is_published);
      setEditQuestions(res.data.questions || []);
      
      // Load active tab data
      loadTabDetails(id, activeTab, res.data);
    } catch (err) { toast.error('Failed to load assignment details.'); }
    finally { setLoadingDetails(false); }
  };

  const loadTabDetails = async (assignmentId, tab, currentDetails = assignmentDetails) => {
    setActiveTab(tab);
    if (!assignmentId) return;

    if (tab === 'submissions') {
      try {
        if (typeof teacherPortalApi.getAssignmentSubmissions === 'function') {
          const res = await teacherPortalApi.getAssignmentSubmissions(assignmentId);
          setSubmissions(res.data || []);
        } else {
          setSubmissions([]);
        }
      } catch (err) {
        setSubmissions([]);
      }
    } else if (tab === 'analytics') {
      try {
        if (typeof teacherPortalApi.getAssignmentAnalytics === 'function') {
          const res = await teacherPortalApi.getAssignmentAnalytics(assignmentId);
          setAnalytics(res.data);
        } else {
          const qList = currentDetails?.questions || [];
          setAnalytics({
            attempts_count: 0,
            avg_score: 0,
            total_questions: qList.length || 0,
            question_performance: [],
          });
        }
      } catch (err) {
        const qList = currentDetails?.questions || [];
        setAnalytics({
          attempts_count: 0,
          avg_score: 0,
          total_questions: qList.length || 0,
          question_performance: [],
        });
      }
    }
  };

  const openEvaluationModal = async (subId) => {
    setSelectedSubmissionId(subId);
    setLoadingSubmission(true);
    setAiEvaluationResult(null);
    try {
      const res = await teacherPortalApi.getAssignmentSubmissionDetails(subId);
      setSubmissionDetails(res.data);
      const initialMap = {};
      (res.data.questions || []).forEach(q => {
        initialMap[q.question_id] = q.marks_awarded || 0;
      });
      setMarksAwardedMap(initialMap);
    } catch (err) {
      toast.error('Failed to load submission details.');
    } finally {
      setLoadingSubmission(false);
    }
  };

  const handleAIEvaluateSubmission = async () => {
    if (!selectedSubmissionId) return;
    setEvaluatingAI(true);
    try {
      const res = await teacherPortalApi.evaluateAssignmentWithAI(selectedSubmissionId);
      setAiEvaluationResult(res.data);
      const updatedMap = { ...marksAwardedMap };
      (res.data.question_evaluations || []).forEach(qEval => {
        updatedMap[qEval.question_id] = qEval.suggested_marks;
      });
      setMarksAwardedMap(updatedMap);
      toast.success('✨ Groq AI evaluated submission successfully!');
    } catch (err) {
      toast.error('AI evaluation failed. Please try again.');
    } finally {
      setEvaluatingAI(false);
    }
  };

  const handleSaveSubmissionGrade = async () => {
    if (!selectedSubmissionId) return;
    setSavingGrade(true);
    try {
      const questionGrades = Object.entries(marksAwardedMap).map(([qId, marks]) => ({
        question_id: parseInt(qId),
        marks_awarded: parseFloat(marks)
      }));
      await teacherPortalApi.gradeAssignmentSubmission(selectedSubmissionId, { question_grades: questionGrades });
      toast.success('Submission graded and saved!');
      setSelectedSubmissionId(null);
      setSubmissionDetails(null);
      fetchAssignments(selectedSectionId);
      loadTabDetails(selectedAssignmentId, 'submissions');
    } catch (err) {
      toast.error('Failed to save grade.');
    } finally {
      setSavingGrade(false);
    }
  };

  // ═══════════════════════════════════════════════════════════
  //  HANDLERS
  // ═══════════════════════════════════════════════════════════
  const handleSaveEdit = async () => {
    try {
      const computedTotal = editQuestions.reduce((sum, q) => sum + (parseInt(q.marks) || 0), 0);
      await teacherPortalApi.updateAssignment(selectedAssignmentId, {
        title: editTitle,
        description: editDescription,
        due_date: editDueDate || null,
        total_marks: computedTotal,
        is_published: editIsPublished,
        questions: editQuestions.map(q => ({
          question_text: q.question_text,
          question_type: q.question_type,
          option_a: q.option_a || null,
          option_b: q.option_b || null,
          option_c: q.option_c || null,
          option_d: q.option_d || null,
          correct_answer: q.correct_answer || '',
          marks: q.marks || 5,
          difficulty: q.difficulty || 'medium'
        }))
      });
      toast.success('Assignment updated!');
      setIsEditing(false);
      if (editIsPublished) {
        if (editDueDate && new Date(editDueDate) < new Date()) {
          setAssignmentFilterTab('completed');
        } else {
          setAssignmentFilterTab('active');
        }
      } else {
        setAssignmentFilterTab('draft');
      }
      fetchAssignments(selectedSectionId);
      fetchAssignmentDetails(selectedAssignmentId);
    } catch (err) { toast.error('Failed to update assignment.'); }
  };

  const handleDelete = async (id) => {
    if (!confirm('Delete this assignment?')) return;
    try {
      await teacherPortalApi.deleteAssignment(id);
      toast.success('Assignment deleted.');
      setSelectedAssignmentId(null);
      setAssignmentDetails(null);
      fetchAssignments(selectedSectionId);
    } catch (err) { toast.error('Failed to delete.'); }
  };

  const openCreateWizard = () => {
    setShowCreateWizard(true);
    setCreateMode('manual');
    setWizardStep(1);
    setNewTitle(''); setNewDescription(''); setNewDueDate('');
    setNewTotalMarks(100); setNewIsPublished(false);
    setNewQuestions([{
      question_text: '', question_type: 'short_answer', marks: 5, difficulty: 'medium'
    }]);
    setSelectedMaterialIds([]);
    setAiGeneratedQuestions([]);
    setAiSaveTitle(''); setAiSaveDescription('');
  };

  const handleSaveManual = async () => {
    if (!newTitle.trim()) { toast.error('Please enter a title.'); return; }
    try {
      const computedTotal = newQuestions.reduce((sum, q) => sum + (parseInt(q.marks) || 0), 0);
      await teacherPortalApi.createAssignment(selectedSectionId, {
        title: newTitle,
        description: newDescription,
        due_date: newDueDate || null,
        total_marks: computedTotal,
        is_published: newIsPublished,
        questions: newQuestions
      });
      toast.success('Assignment created!');
      setShowCreateWizard(false);
      if (newIsPublished) {
        if (newDueDate && new Date(newDueDate) < new Date()) {
          setAssignmentFilterTab('completed');
        } else {
          setAssignmentFilterTab('active');
        }
      } else {
        setAssignmentFilterTab('draft');
      }
      fetchAssignments(selectedSectionId);
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed to create.'); }
  };

  const fetchAvailableMaterials = async () => {
    try {
      const res = await teacherPortalApi.getAvailableMaterials();
      setAvailableMaterials(res.data);
    } catch (err) { toast.error('Failed to load materials.'); }
  };

  const handleAIGenerate = async () => {
    if (selectedMaterialIds.length === 0) { toast.error('Select at least one material.'); return; }
    setAiGenerating(true);
    try {
      const res = await teacherPortalApi.generateAIAssignment({
        material_ids: selectedMaterialIds,
        num_questions: aiNumQuestions,
        difficulty: aiDifficulty,
        question_types: aiQuestionTypes
      });
      setAiGeneratedQuestions(res.data.questions || []);
      setWizardStep(3);
      toast.success(`Generated ${res.data.questions?.length || 0} questions!`);
    } catch (err) { toast.error(err.response?.data?.detail || 'AI generation failed.'); }
    finally { setAiGenerating(false); }
  };

  const handleSaveAIAssignment = async () => {
    if (!aiSaveTitle.trim()) { toast.error('Enter a title.'); return; }
    setSavingAI(true);
    try {
      const computedTotal = aiGeneratedQuestions.reduce((sum, q) => sum + (parseInt(q.marks) || 0), 0);
      await teacherPortalApi.saveAIAssignment({
        section_id: selectedSectionId,
        title: aiSaveTitle,
        description: aiSaveDescription,
        due_date: aiSaveDueDate || null,
        total_marks: computedTotal,
        is_published: aiSaveIsPublished,
        source_material_ids: selectedMaterialIds,
        questions: aiGeneratedQuestions.map((q, i) => ({
          question_text: q.question_text,
          question_type: q.question_type || 'short_answer',
          option_a: q.option_a || null,
          option_b: q.option_b || null,
          option_c: q.option_c || null,
          option_d: q.option_d || null,
          correct_answer: q.correct_answer || '',
          marks: q.marks || 5,
          difficulty: q.difficulty || 'medium'
        }))
      });
      toast.success('AI assignment saved!');
      setShowCreateWizard(false);
      if (aiSaveIsPublished) {
        if (aiSaveDueDate && new Date(aiSaveDueDate) < new Date()) {
          setAssignmentFilterTab('completed');
        } else {
          setAssignmentFilterTab('active');
        }
      } else {
        setAssignmentFilterTab('draft');
      }
      fetchAssignments(selectedSectionId);
    } catch (err) { toast.error(err.response?.data?.detail || 'Save failed.'); }
    finally { setSavingAI(false); }
  };

  // ═══════════════════════════════════════════════════════════
  //  RENDER: Question Form (shared between edit & create)
  // ═══════════════════════════════════════════════════════════
  const renderQuestionForm = (questions, setQuestions, editable = true) => (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
      {questions.map((q, idx) => (
        <div key={idx} className="question-card" style={{ padding: '0.75rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.35rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <span className="question-number" style={{ fontSize: '0.7rem' }}>Q{idx + 1}</span>
              {editable && (
                <select className="input" value={q.question_type || 'short_answer'} onChange={e => {
                  const copy = [...questions]; copy[idx] = { ...copy[idx], question_type: e.target.value }; setQuestions(copy);
                }} style={{ width: '130px', fontSize: '0.7rem', padding: '0.2rem' }}>
                  <option value="short_answer">Short Answer</option>
                  <option value="long_answer">Long Answer</option>
                </select>
              )}
              {!editable && <span className="badge badge-info" style={{ fontSize: '0.65rem' }}>{q.question_type === 'long_answer' ? 'Long Answer' : 'Short Answer'}</span>}
            </div>
            {editable && (
              <button className="btn btn-ghost" onClick={() => setQuestions(prev => prev.filter((_, i) => i !== idx))} style={{ padding: '0.15rem', color: 'var(--danger)' }}><Trash2 size={12} /></button>
            )}
          </div>

          {/* Question Text */}
          <textarea
            className="input"
            value={q.question_text}
            onChange={e => {
              const copy = [...questions]; copy[idx] = { ...copy[idx], question_text: e.target.value }; setQuestions(copy);
            }}
            disabled={!editable}
            rows={q.question_type === 'long_answer' ? 3 : 2}
            placeholder={q.question_type === 'long_answer'
              ? "Enter long question prompt / problem description... (e.g., Write a program to invert a Binary Tree and explain its complexity)."
              : "Enter short question prompt... (e.g., Explain the difference between BST and AVL trees)."}
            style={{ width: '100%', marginBottom: '0.5rem', fontSize: '0.85rem' }}
          />

          {/* Solution / Marking Rubric */}
          {editable && (
            <textarea
              className="input"
              value={q.correct_answer || ''}
              onChange={e => {
                const copy = [...questions]; copy[idx] = { ...copy[idx], correct_answer: e.target.value }; setQuestions(copy);
              }}
              rows={2}
              placeholder={q.question_type === 'long_answer'
                ? "Enter expected solution outline, code, or marking rubric..."
                : "Enter expected answer keywords or short evaluation criteria..."}
              style={{ fontSize: '0.8rem', marginBottom: '0.5rem', width: '100%' }}
            />
          )}
          {!editable && q.correct_answer && (
            <div style={{ padding: '0.4rem 0.6rem', background: 'rgba(16,185,129,0.08)', borderRadius: '0.4rem', fontSize: '0.8rem', border: '1px solid rgba(16,185,129,0.2)' }}>
              <span style={{ fontWeight: 600, color: '#10b981' }}>Model Solution / Rubric:</span> {q.correct_answer}
            </div>
          )}

          {editable && (
            <div style={{ display: 'flex', gap: '0.75rem', marginTop: '0.4rem', alignItems: 'center', background: 'var(--bg-input)', padding: '0.35rem 0.6rem', borderRadius: '0.5rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)' }}>Difficulty:</span>
                <select className="input" value={q.difficulty || 'medium'} onChange={e => {
                  const copy = [...questions]; copy[idx] = { ...copy[idx], difficulty: e.target.value }; setQuestions(copy);
                }} style={{ width: '100px', padding: '0.2rem 0.4rem', fontSize: '0.75rem' }}>
                  <option value="easy">Easy</option>
                  <option value="medium">Medium</option>
                  <option value="hard">Hard</option>
                </select>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', marginLeft: 'auto' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)' }}>Marks:</span>
                <input type="number" className="input" value={q.marks || (q.question_type === 'long_answer' ? 15 : 5)} onChange={e => {
                  const copy = [...questions]; copy[idx] = { ...copy[idx], marks: parseInt(e.target.value) || 0 }; setQuestions(copy);
                }} style={{ width: '70px', padding: '0.2rem 0.4rem', fontSize: '0.75rem' }} placeholder="e.g. 5" min={1} />
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );

  // ── Overlay Dismiss Protection: shake + toast instead of close ──
  const [modalShaking, setModalShaking] = useState(false);
  const handleModalOverlayClick = useCallback((e) => {
    if (e.target !== e.currentTarget) return;
    setModalShaking(true);
    setTimeout(() => setModalShaking(false), 500);
    toast('Please close this dialog first using the ✕ button', { icon: '⚠️', duration: 2500 });
  }, []);

  const renderCreateWizard = () => {
    if (!showCreateWizard) return null;
    return (
      <div className="modal-overlay" onClick={handleModalOverlayClick}>
        <div className={`modal-content${modalShaking ? ' modal-content-shake' : ''}`} onClick={e => e.stopPropagation()}>
          <div className="wizard-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <FileText size={20} style={{ color: 'var(--accent)' }} />
              <h2 style={{ margin: 0, fontSize: '1.1rem' }}>Create Assignment</h2>
            </div>
            <button className="btn btn-ghost" onClick={() => setShowCreateWizard(false)} style={{ padding: '0.25rem' }}><X size={18} /></button>
          </div>

          <div className="wizard-mode-toggle">
            <button className={`mode-btn ${createMode === 'manual' ? 'active' : ''}`} onClick={() => { setCreateMode('manual'); setWizardStep(1); }}>
              <BookOpen size={16} /> Manual
            </button>
            <button className={`mode-btn ${createMode === 'ai' ? 'active' : ''}`} onClick={() => { setCreateMode('ai'); setWizardStep(1); fetchAvailableMaterials(); }}>
              <Brain size={16} /> AI Generate
            </button>
          </div>

          <div className="wizard-body">
            {createMode === 'manual' ? (
              <div>
                <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '0.85rem', marginBottom: '1rem' }}>
                  <div>
                    <label className="form-label">Assignment Title</label>
                    <input className="input" value={newTitle} onChange={e => setNewTitle(e.target.value)} placeholder="e.g., Assignment 1: Web Development & React State Management" />
                  </div>
                  <div>
                    <label className="form-label">Total Marks (Auto-Calculated)</label>
                    <div className="input" style={{ background: 'var(--bg-tertiary)', fontWeight: 600, color: 'var(--accent)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <span>{newQuestions.reduce((sum, q) => sum + (parseInt(q.marks) || 0), 0)} Marks</span>
                      <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 400 }}>Auto-sum of questions</span>
                    </div>
                  </div>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.85rem', marginBottom: '1rem' }}>
                  <div>
                    <label className="form-label">Description & Instructions (Optional)</label>
                    <textarea className="input" value={newDescription} onChange={e => setNewDescription(e.target.value)} rows={2} placeholder="Enter detailed assignment instructions, submission rules, or grading rubrics..." style={{ width: '100%' }} />
                  </div>
                  <div>
                    <label className="form-label">Due Date & Time (Optional)</label>
                    <input type="datetime-local" className="input" value={newDueDate} onChange={e => setNewDueDate(e.target.value)} placeholder="Select due date and time" />
                  </div>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                  <h4 style={{ fontSize: '0.9rem', margin: 0, color: 'var(--text-primary)', fontWeight: 600 }}>Questions ({newQuestions.length})</h4>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Configure question types & marks</span>
                </div>

                <div className="modal-scroll-area" style={{ maxHeight: '280px', overflowY: 'auto', paddingRight: '0.35rem' }}>
                  {renderQuestionForm(newQuestions, setNewQuestions, true)}
                </div>
                <button className="btn btn-ghost" onClick={() => setNewQuestions(prev => [...prev, {
                  question_text: '', question_type: 'short_answer', marks: 5, difficulty: 'medium'
                }])} style={{ marginTop: '0.75rem', width: '100%', border: '1.5px dashed var(--border)', fontSize: '0.825rem', padding: '0.5rem', borderRadius: '0.6rem' }}>
                  <Plus size={14} /> Add Question
                </button>

                <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1.25rem', paddingTop: '0.85rem', borderTop: '1px solid var(--border)', alignItems: 'center' }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.825rem', marginRight: 'auto', cursor: 'pointer', color: 'var(--text-secondary)' }}>
                    <input type="checkbox" checked={newIsPublished} onChange={e => setNewIsPublished(e.target.checked)} style={{ accentColor: 'var(--accent)', width: '16px', height: '16px' }} /> Publish immediately to students
                  </label>
                  <button className="btn btn-ghost" onClick={() => setShowCreateWizard(false)}>Cancel</button>
                  <button className="btn btn-primary" onClick={handleSaveManual} disabled={!newTitle.trim()}>
                    <Save size={14} /> Save Assignment
                  </button>
                </div>
              </div>
            ) : (
              <div>
                <div className="wizard-steps">
                  <div className={`wizard-step ${wizardStep === 1 ? 'active' : wizardStep > 1 ? 'completed' : ''}`}>
                    <span className="step-number">1</span> Select Materials
                  </div>
                  <div className={`wizard-step ${wizardStep === 2 ? 'active' : wizardStep > 2 ? 'completed' : ''}`}>
                    <span className="step-number">2</span> Configure AI
                  </div>
                  <div className={`wizard-step ${wizardStep === 3 ? 'active' : ''}`}>
                    <span className="step-number">3</span> Preview & Save
                  </div>
                </div>

                {wizardStep === 1 && (
                  <div>
                    <h4 style={{ fontSize: '0.85rem', marginBottom: '0.75rem', color: 'var(--text-secondary)' }}>Select Lecture Topics, Videos, or Assignments to Generate Questions From:</h4>
                    {availableMaterials.length === 0 ? (
                      <div style={{ textAlign: 'center', padding: '1.5rem', color: 'var(--text-muted)', fontSize: '0.85rem' }}>No materials or topics uploaded yet for this section.</div>
                    ) : (
                      <div className="modal-scroll-area" style={{ maxHeight: '250px', overflowY: 'auto', paddingRight: '0.25rem' }}>
                        {availableMaterials.map(course => (
                          <div key={course.course_id} style={{ marginBottom: '1rem' }}>
                            <h5 style={{ fontSize: '0.85rem', color: 'var(--accent)', margin: '0 0 0.4rem 0', fontWeight: 700 }}>
                              {course.course_code} — {course.course_name}
                            </h5>
                            {course.topics.map(topic => (
                              <div key={topic.topic_id} style={{ marginLeft: '0.5rem', marginBottom: '0.65rem' }}>
                                <span style={{ fontSize: '0.775rem', fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: '0.25rem' }}>{topic.topic_title}</span>
                                {topic.materials.map(m => (
                                  <label key={m.id} className={`material-checkbox ${selectedMaterialIds.includes(m.id) ? 'selected' : ''}`} style={{ marginBottom: '0.35rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                                    <input type="checkbox" checked={selectedMaterialIds.includes(m.id)} onChange={() => setSelectedMaterialIds(prev => prev.includes(m.id) ? prev.filter(x => x !== m.id) : [...prev, m.id])} />
                                    {m.file_type === 'video' || m.file_name?.startsWith('🎥') ? <Video size={14} style={{ color: 'var(--accent)', flexShrink: 0 }} /> :
                                     m.file_type === 'assignment' || m.file_name?.startsWith('📝') ? <FileText size={14} style={{ color: '#f59e0b', flexShrink: 0 }} /> :
                                     <BookOpen size={14} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />}
                                    <span style={{ fontSize: '0.825rem', fontWeight: 500 }}>{m.file_name || m.title || 'Untitled Material'}</span>
                                  </label>
                                ))}
                              </div>
                            ))}
                          </div>
                        ))}
                      </div>
                    )}
                    <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '1rem', paddingTop: '0.75rem', borderTop: '1px solid var(--border)' }}>
                      <button className="btn btn-primary" onClick={() => setWizardStep(2)} disabled={selectedMaterialIds.length === 0}>
                        Next: Configure <ChevronRight size={14} />
                      </button>
                    </div>
                  </div>
                )}

                {wizardStep === 2 && (
                  <div>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.85rem', marginBottom: '1rem' }}>
                      <div>
                        <label className="form-label">Number of Questions</label>
                        <input type="number" className="input" value={aiNumQuestions} onChange={e => setAiNumQuestions(parseInt(e.target.value))} min={1} max={20} />
                      </div>
                      <div>
                        <label className="form-label">Target Difficulty</label>
                        <select className="input" value={aiDifficulty} onChange={e => setAiDifficulty(e.target.value)}>
                          <option value="easy">Easy</option>
                          <option value="medium">Medium</option>
                          <option value="hard">Hard</option>
                        </select>
                      </div>
                    </div>
                    <div style={{ marginBottom: '1.25rem' }}>
                      <label className="form-label" style={{ fontWeight: 600, marginBottom: '0.5rem', display: 'block' }}>Question Types to Include</label>
                      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0.75rem', marginTop: '0.4rem' }}>
                        {[
                          { key: 'short_answer', label: 'Short Answer', desc: 'Conceptual 2-4 sentence questions' },
                          { key: 'long_answer', label: 'Long Answer', desc: 'Detailed analytical & problem solving' }
                        ].map(t => {
                          const isChecked = aiQuestionTypes.includes(t.key);
                          return (
                            <div
                              key={t.key}
                              onClick={() => {
                                setAiQuestionTypes(prev => prev.includes(t.key) ? (prev.length > 1 ? prev.filter(x => x !== t.key) : prev) : [...prev, t.key]);
                              }}
                              style={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: '0.75rem',
                                padding: '0.85rem 1rem',
                                borderRadius: '0.75rem',
                                border: isChecked ? '2px solid var(--accent, #6366f1)' : '1.5px solid var(--border)',
                                background: isChecked ? 'rgba(99, 102, 241, 0.08)' : 'var(--bg-input, rgba(255, 255, 255, 0.03))',
                                cursor: 'pointer',
                                transition: 'all 0.2s ease',
                                userSelect: 'none',
                                boxShadow: isChecked ? '0 2px 8px rgba(99, 102, 241, 0.15)' : 'none'
                              }}
                            >
                              {/* Custom Styled Checkbox Square */}
                              <div style={{
                                width: '20px',
                                height: '20px',
                                borderRadius: '6px',
                                border: isChecked ? 'none' : '2px solid var(--text-muted, #94a3b8)',
                                background: isChecked ? 'var(--accent, #6366f1)' : 'transparent',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                flexShrink: 0,
                                transition: 'all 0.2s ease'
                              }}>
                                {isChecked && <Check size={14} style={{ color: '#fff', strokeWidth: 3 }} />}
                              </div>

                              {/* Label and Description */}
                              <div>
                                <div style={{ fontSize: '0.875rem', fontWeight: 600, color: isChecked ? 'var(--accent, #6366f1)' : 'var(--text-primary)' }}>
                                  {t.label}
                                </div>
                                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                                  {t.desc}
                                </div>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', paddingTop: '0.85rem', borderTop: '1px solid var(--border)' }}>
                      <button className="btn btn-ghost" onClick={() => setWizardStep(1)}>Back</button>
                      <button className="btn btn-primary" onClick={handleAIGenerate} disabled={aiGenerating || aiQuestionTypes.length === 0}>
                        {aiGenerating ? <><Loader2 size={14} className="spin" /> Generating Questions...</> : <><Sparkles size={14} /> Generate Assignment</>}
                      </button>
                    </div>
                  </div>
                )}

                {wizardStep === 3 && (
                  <div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                      <h4 style={{ margin: 0, fontSize: '0.9rem', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                        <Sparkles size={16} style={{ color: 'var(--accent)' }} /> {aiGeneratedQuestions.length} Questions Generated
                      </h4>
                      <button className="btn btn-ghost" onClick={() => setWizardStep(2)} style={{ fontSize: '0.775rem', padding: '0.3rem 0.6rem' }}>↻ Regenerate</button>
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem', marginBottom: '1rem', padding: '0.85rem', background: 'var(--bg-input)', borderRadius: '0.75rem', border: '1px solid var(--border)' }}>
                      <div>
                        <label className="form-label">Assignment Title</label>
                        <input className="input" value={aiSaveTitle} onChange={e => setAiSaveTitle(e.target.value)} placeholder="e.g., AI Assignment: Database Design Practices" />
                      </div>
                      <div>
                        <label className="form-label">Due Date & Time</label>
                        <input type="datetime-local" className="input" value={aiSaveDueDate} onChange={e => setAiSaveDueDate(e.target.value)} placeholder="Select due date" />
                      </div>
                      <div>
                        <label className="form-label">Total Marks (Auto-Calculated)</label>
                        <div className="input" style={{ background: 'var(--bg-tertiary)', fontWeight: 600, color: 'var(--accent)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                          <span>{aiGeneratedQuestions.reduce((sum, q) => sum + (parseInt(q.marks) || 0), 0)} Marks</span>
                          <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 400 }}>Auto-sum of questions</span>
                        </div>
                      </div>
                      <div>
                        <label className="form-label">Description (Optional)</label>
                        <input className="input" value={aiSaveDescription} onChange={e => setAiSaveDescription(e.target.value)} placeholder="Enter brief instructions or guidelines..." />
                      </div>
                    </div>

                    <div className="modal-scroll-area" style={{ maxHeight: '250px', overflowY: 'auto', paddingRight: '0.25rem' }}>
                      {renderQuestionForm(aiGeneratedQuestions, setAiGeneratedQuestions, true)}
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '1.25rem', paddingTop: '0.85rem', borderTop: '1px solid var(--border)', alignItems: 'center' }}>
                      <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.825rem', cursor: 'pointer', color: 'var(--text-secondary)' }}>
                        <input type="checkbox" checked={aiSaveIsPublished} onChange={e => setAiSaveIsPublished(e.target.checked)} style={{ accentColor: 'var(--accent)', width: '16px', height: '16px' }} /> Publish immediately
                      </label>
                      <button className="btn btn-primary" onClick={handleSaveAIAssignment} disabled={savingAI || !aiSaveTitle.trim()}>
                        {savingAI ? <><Loader2 size={14} className="spin" /> Saving...</> : <><Save size={14} /> Save Assignment</>}
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    );
  };

  const handleDeleteAssignment = async (assignmentId, e) => {
    e.stopPropagation();
    if (window.confirm('Are you sure you want to end and delete this active assignment? It will move to Completed tab.')) {
      try {
        await teacherPortalApi.deleteAssignment(assignmentId);
        toast.success('Active assignment ended & moved to Completed!');
        setAssignmentFilterTab('completed');
        setSelectedAssignmentId(assignmentId);
        setActiveTab('submissions');
        fetchAssignments(selectedSectionId);
      } catch (err) {
        toast.error('Failed to delete assignment.');
      }
    }
  };

  const isExpired = (dueDate) => {
    if (!dueDate) return false;
    return new Date(dueDate) < new Date();
  };

  const activeAssignments = assignments.filter(a => a.is_published && !a.is_deleted && !isExpired(a.due_date));
  const completedAssignments = assignments.filter(a => a.is_published && (a.is_deleted || isExpired(a.due_date)));
  const draftAssignments = assignments.filter(a => !a.is_published && !a.is_deleted);
  const displayedAssignments = assignmentFilterTab === 'active' ? activeAssignments : assignmentFilterTab === 'draft' ? draftAssignments : completedAssignments;

  const renderAssignmentList = () => (
    <div className="assignment-sidebar">
      <div style={{ marginBottom: '0.75rem' }}>
        <label className="form-label" style={{ fontSize: '0.75rem' }}>Section</label>
        <select className="input" value={selectedSectionId || ''} onChange={e => setSelectedSectionId(parseInt(e.target.value))} style={{ fontSize: '0.8rem', padding: '0.35rem' }}>
          {sections.map(s => <option key={s.id} value={s.id}>{s.course_code} - {s.section_label}</option>)}
        </select>
      </div>

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
        <h3 style={{ margin: 0, fontSize: '0.95rem', color: 'var(--text-secondary)' }}>Assignments</h3>
        <div style={{ display: 'flex', gap: '0.4rem' }}>
          <button className="btn btn-ghost" onClick={fetchRegradeRequests} title="View Student Regrade Appeals" style={{ fontSize: '0.7rem', padding: '0.35rem 0.6rem', color: 'var(--accent)' }}>
            📩 Appeals
          </button>
          <button className="btn btn-primary" onClick={openCreateWizard} style={{ display: 'flex', alignItems: 'center', gap: '0.3rem', fontSize: '0.75rem', padding: '0.35rem 0.7rem' }}>
            <Plus size={13} /> Create
          </button>
        </div>
      </div>

      {/* Active vs Completed vs Draft Tabs */}
      <div style={{ display: 'flex', gap: '0.35rem', marginBottom: '0.85rem', background: 'var(--bg-tertiary)', padding: '4px', borderRadius: '8px' }}>
        <button
          onClick={() => {
            setAssignmentFilterTab('active');
            if (activeAssignments.length === 0) {
              setSelectedAssignmentId(null);
            } else if (!activeAssignments.some(a => a.id === selectedAssignmentId)) {
              setSelectedAssignmentId(activeAssignments[0].id);
            }
          }}
          style={{
            flex: 1,
            padding: '0.35rem 0.35rem',
            border: 'none',
            borderRadius: '6px',
            fontSize: '0.7rem',
            fontWeight: 600,
            cursor: 'pointer',
            background: assignmentFilterTab === 'active' ? 'var(--bg-card)' : 'transparent',
            color: assignmentFilterTab === 'active' ? 'var(--accent)' : 'var(--text-muted)',
            boxShadow: assignmentFilterTab === 'active' ? '0 1px 3px rgba(0,0,0,0.1)' : 'none'
          }}
        >
          Active ({activeAssignments.length})
        </button>
        <button
          onClick={() => {
            setAssignmentFilterTab('completed');
            if (completedAssignments.length === 0) {
              setSelectedAssignmentId(null);
            } else if (!completedAssignments.some(a => a.id === selectedAssignmentId)) {
              setSelectedAssignmentId(completedAssignments[0].id);
              setActiveTab('submissions');
            }
          }}
          style={{
            flex: 1,
            padding: '0.35rem 0.35rem',
            border: 'none',
            borderRadius: '6px',
            fontSize: '0.7rem',
            fontWeight: 600,
            cursor: 'pointer',
            background: assignmentFilterTab === 'completed' ? 'var(--bg-card)' : 'transparent',
            color: assignmentFilterTab === 'completed' ? 'var(--accent)' : 'var(--text-muted)',
            boxShadow: assignmentFilterTab === 'completed' ? '0 1px 3px rgba(0,0,0,0.1)' : 'none'
          }}
        >
          Completed ({completedAssignments.length})
        </button>
        <button
          onClick={() => {
            setAssignmentFilterTab('draft');
            if (draftAssignments.length === 0) {
              setSelectedAssignmentId(null);
            } else if (!draftAssignments.some(a => a.id === selectedAssignmentId)) {
              setSelectedAssignmentId(draftAssignments[0].id);
            }
          }}
          style={{
            flex: 1,
            padding: '0.35rem 0.35rem',
            border: 'none',
            borderRadius: '6px',
            fontSize: '0.7rem',
            fontWeight: 600,
            cursor: 'pointer',
            background: assignmentFilterTab === 'draft' ? 'var(--bg-card)' : 'transparent',
            color: assignmentFilterTab === 'draft' ? 'var(--accent)' : 'var(--text-muted)',
            boxShadow: assignmentFilterTab === 'draft' ? '0 1px 3px rgba(0,0,0,0.1)' : 'none'
          }}
        >
          Drafts ({draftAssignments.length})
        </button>
      </div>

      {loading ? (
        <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}><Loader2 size={20} className="spin" /></div>
      ) : displayedAssignments.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>
          <FileText size={36} style={{ opacity: 0.3, marginBottom: '0.5rem' }} />
          <p style={{ fontSize: '0.85rem' }}>{assignmentFilterTab === 'completed' ? 'No completed assignments' : assignmentFilterTab === 'draft' ? 'No draft assignments' : 'No active assignments'}</p>
        </div>
      ) : (
        displayedAssignments.map((a, idx) => (
          <div
            key={a.id}
            className={`assignment-card ${selectedAssignmentId === a.id ? 'selected' : ''}`}
            onClick={() => {
              setSelectedAssignmentId(a.id);
              if (assignmentFilterTab === 'completed' || a.is_deleted || isExpired(a.due_date)) {
                setActiveTab('submissions');
              }
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <h4 style={{ margin: '0 0 0.2rem', fontSize: '0.85rem' }}>
                {a.title || `Assignment ${idx + 1}`}
              </h4>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                {assignmentFilterTab === 'completed' || a.is_deleted || isExpired(a.due_date) ? (
                  <span className={`badge ${a.is_deleted ? 'badge-danger' : 'badge-warning'}`} style={{ fontSize: '0.6rem' }}>
                    {a.is_deleted ? 'END' : 'EXPIRED'}
                  </span>
                ) : assignmentFilterTab === 'draft' || !a.is_published ? (
                  <span className="badge badge-warning" style={{ fontSize: '0.6rem' }}>DRAFT</span>
                ) : (
                  <span className={`badge ${a.assignment_type === 'ai_generated' ? 'badge-ai' : 'badge-muted'}`} style={{ fontSize: '0.6rem' }}>
                    {a.assignment_type === 'ai_generated' ? '✨ AI' : 'Manual'}
                  </span>
                )}
                {assignmentFilterTab === 'active' && !a.is_deleted && !isExpired(a.due_date) && (
                  <button
                    onClick={(e) => handleDeleteAssignment(a.id, e)}
                    title="Delete & End Assignment"
                    style={{
                      background: 'none',
                      border: 'none',
                      color: '#ef4444',
                      cursor: 'pointer',
                      padding: '2px',
                      borderRadius: '4px',
                      display: 'flex',
                      alignItems: 'center'
                    }}
                  >
                    <Trash2 size={13} />
                  </button>
                )}
              </div>
            </div>
            <div style={{ display: 'flex', gap: '0.5rem', fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: '0.25rem', flexWrap: 'wrap' }}>
              <span>{a.questions_count} Q</span>
              <span>{a.total_marks} marks</span>
              {a.due_date && <span><Clock size={10} /> {new Date(a.due_date).toLocaleDateString()}</span>}
              <span className={`badge ${a.is_published ? 'badge-success' : 'badge-muted'}`} style={{ fontSize: '0.6rem' }}>
                {a.is_published ? 'Published' : 'Draft'}
              </span>
            </div>
          </div>
        ))
      )}
    </div>
  );

  const renderSubmissionsTab = () => (
    <div>
      {submissions.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>No submissions yet.</div>
      ) : (
        <table className="data-table" style={{ width: '100%' }}>
          <thead>
            <tr><th>Student</th><th>Reg #</th><th>Score</th><th>Status</th><th>Submitted At</th><th>Action</th></tr>
          </thead>
          <tbody>
            {submissions.map((s, i) => (
              <tr key={i}>
                <td>{s.student_name}</td>
                <td>{s.reg_number}</td>
                <td>
                  <span className={`badge ${s.score_percentage >= 70 ? 'badge-success' : s.score_percentage >= 50 ? 'badge-warning' : 'badge-danger'}`}>
                    {s.total_score}/{s.total_marks} ({s.score_percentage}%)
                  </span>
                </td>
                <td>
                  <span className={`badge ${s.status === 'Graded' ? 'badge-success' : 'badge-info'}`}>
                    {s.status}
                  </span>
                </td>
                <td style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{new Date(s.submitted_at).toLocaleString()}</td>
                <td>
                  <button className="btn btn-primary" onClick={() => openEvaluationModal(s.id)} style={{ fontSize: '0.75rem', padding: '0.25rem 0.6rem', display: 'inline-flex', alignItems: 'center', gap: '0.3rem' }}>
                    <Eye size={12} /> View & Grade
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );

  const renderAnalyticsTab = () => {
    if (!analytics) return null;
    return (
      <div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '1rem', marginBottom: '1.5rem' }}>
          <div className="stat-card"><div className="stat-value">{analytics.attempts_count}</div><div className="stat-label">Total Submissions</div></div>
          <div className="stat-card"><div className="stat-value">{analytics.avg_score}%</div><div className="stat-label">Avg Marks</div></div>
          <div className="stat-card"><div className="stat-value">{analytics.total_questions}</div><div className="stat-label">Questions</div></div>
        </div>
        <h4 style={{ fontSize: '0.9rem', marginBottom: '0.75rem' }}>Question Performance & Evaluation</h4>
        {(analytics.question_performance || []).map((qp, i) => (
          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem', padding: '0.65rem', background: 'var(--bg-tertiary)', borderRadius: '0.4rem' }}>
            <span style={{ fontSize: '0.8rem', flex: 1, fontWeight: 500 }}>{qp.question_text}</span>
            <span className={`badge ${qp.difficulty_rating === 'Easy' ? 'badge-success' : qp.difficulty_rating === 'Hard' ? 'badge-danger' : 'badge-warning'}`} style={{ fontSize: '0.7rem' }}>
              {qp.success_rate}% ({qp.difficulty_rating})
            </span>
          </div>
        ))}
      </div>
    );
  };

  const renderAssignmentDetails = () => {
    const isSelectedInDisplayed = displayedAssignments.some(a => a.id === selectedAssignmentId);
    return (
      <div className="assignment-details">
        {!selectedAssignmentId || !isSelectedInDisplayed ? (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-muted)', flexDirection: 'column', gap: '0.5rem' }}>
            <FileText size={40} style={{ opacity: 0.3 }} />
            <span>Select an assignment from the list to view details</span>
          </div>
        ) : loadingDetails ? (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '3rem', color: 'var(--text-muted)' }}><Loader2 size={24} className="spin" /></div>
      ) : assignmentDetails ? (
        <div>
          <div className="quiz-detail-tabs" style={{ display: 'flex', gap: '0.25rem', marginBottom: '1.25rem', padding: '0.25rem', background: 'var(--bg-input)', borderRadius: '0.5rem' }}>
            <button className={`tab-btn ${activeTab === 'questions' ? 'active' : ''}`} onClick={() => loadTabDetails(selectedAssignmentId, 'questions')}>
              <ClipboardList size={14} /> Questions
            </button>
            <button className={`tab-btn ${activeTab === 'submissions' ? 'active' : ''}`} onClick={() => loadTabDetails(selectedAssignmentId, 'submissions')}>
              <Users size={14} /> Submissions
            </button>
            <button className={`tab-btn ${activeTab === 'analytics' ? 'active' : ''}`} onClick={() => loadTabDetails(selectedAssignmentId, 'analytics')}>
              <BarChart3 size={14} /> Analytics
            </button>
          </div>

          {activeTab === 'submissions' && renderSubmissionsTab()}
          {activeTab === 'analytics' && renderAnalyticsTab()}

          {activeTab === 'questions' && (
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', padding: '0.75rem 1rem', background: 'var(--bg-tertiary)', borderRadius: '0.5rem' }}>
                {isEditing ? (
                  <input className="input" value={editTitle} onChange={e => setEditTitle(e.target.value)} style={{ fontSize: '1rem', fontWeight: 600, flex: 1, marginRight: '0.5rem' }} />
                ) : (
                  <div>
                    <h3 style={{ margin: 0, fontSize: '1rem' }}>{assignmentDetails.title}</h3>
                    <div style={{ display: 'flex', gap: '0.5rem', marginTop: '0.25rem' }}>
                      <span className={`badge ${assignmentDetails.assignment_type === 'ai_generated' ? 'badge-ai' : 'badge-muted'}`}>
                        {assignmentDetails.assignment_type === 'ai_generated' ? '✨ AI Generated' : 'Manual'}
                      </span>
                      <span className={`badge ${assignmentDetails.is_published ? 'badge-success' : 'badge-warning'}`}>
                        {assignmentDetails.is_published ? 'Published' : 'Draft'}
                      </span>
                    </div>
                  </div>
                )}
                <div style={{ display: 'flex', gap: '0.5rem' }}>
                  {isEditing ? (
                    <>
                      <button className="btn btn-success" onClick={handleSaveEdit} style={{ fontSize: '0.8rem', padding: '0.4rem 0.75rem' }}><Save size={14} /> Save</button>
                      <button className="btn btn-ghost" onClick={() => setIsEditing(false)} style={{ fontSize: '0.8rem' }}><X size={14} /></button>
                    </>
                  ) : (
                    <>
                      <button className="btn btn-primary" onClick={() => setIsEditing(true)} style={{ fontSize: '0.8rem', padding: '0.4rem 0.75rem' }}><Edit size={14} /> Edit</button>
                      <button className="btn btn-ghost" onClick={() => handleDelete(selectedAssignmentId)} style={{ fontSize: '0.8rem', color: 'var(--danger)' }}><Trash2 size={14} /></button>
                    </>
                  )}
                </div>
              </div>

              {isEditing && (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.75rem', marginBottom: '1rem' }}>
                  <div>
                    <label className="form-label">Due Date</label>
                    <input type="datetime-local" className="input" value={editDueDate} onChange={e => setEditDueDate(e.target.value)} />
                  </div>
                  <div>
                    <label className="form-label">Total Marks (Auto-Calculated)</label>
                    <div className="input" style={{ background: 'var(--bg-tertiary)', fontWeight: 600, color: 'var(--accent)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                      <span>{editQuestions.reduce((sum, q) => sum + (parseInt(q.marks) || 0), 0)} Marks</span>
                      <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)', fontWeight: 400 }}>Auto-sum of questions</span>
                    </div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'flex-end' }}>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.8rem', cursor: 'pointer' }}>
                      <input type="checkbox" checked={editIsPublished} onChange={e => setEditIsPublished(e.target.checked)} /> Published
                    </label>
                  </div>
                </div>
              )}

              {assignmentDetails.description && !isEditing && (
                <p style={{ margin: '0 0 1rem', fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>{assignmentDetails.description}</p>
              )}

              <h4 style={{ fontSize: '0.9rem', marginBottom: '0.5rem' }}>Questions ({(isEditing ? editQuestions : (assignmentDetails?.questions || [])).length})</h4>
              <div>
                {renderQuestionForm(isEditing ? editQuestions : (assignmentDetails?.questions || []), setEditQuestions, isEditing)}
              </div>
              {isEditing && (
                <button className="btn btn-ghost" onClick={() => setEditQuestions(prev => [...prev, {
                  question_text: '', question_type: 'short_answer', marks: 5, difficulty: 'medium'
                }])} style={{ marginTop: '0.5rem', width: '100%', border: '1px dashed var(--border)', fontSize: '0.8rem' }}>
                  <Plus size={14} /> Add Question
                </button>
              )}
            </div>
          )}
        </div>
      ) : (
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-muted)', flexDirection: 'column', gap: '0.5rem', textAlign: 'center', padding: '2rem' }}>
          <AlertTriangle size={36} style={{ color: 'var(--danger)', opacity: 0.6 }} />
          <span>Unable to load details for this assignment.</span>
          <button className="btn btn-ghost" onClick={() => fetchAssignmentDetails(selectedAssignmentId)} style={{ marginTop: '0.5rem', fontSize: '0.8rem' }}>
            <RotateCcw size={14} /> Retry Loading
          </button>
        </div>
      )}
    </div>
  );
};

  const renderEvaluationModal = () => {
    if (!selectedSubmissionId) return null;
    return (
      <div className="modal-overlay" onClick={handleModalOverlayClick}>
        <div className={`modal-content${modalShaking ? ' modal-content-shake' : ''}`} onClick={e => e.stopPropagation()} style={{ width: '840px' }}>
          <div className="wizard-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Sparkles size={20} style={{ color: 'var(--accent)' }} />
              <h2 style={{ margin: 0, fontSize: '1.1rem' }}>Evaluate Student Submission</h2>
            </div>
            <button className="btn btn-ghost" onClick={() => setSelectedSubmissionId(null)} style={{ padding: '0.25rem' }}><X size={18} /></button>
          </div>

          <div style={{ padding: '1.25rem' }}>
            {loadingSubmission ? (
              <div style={{ textAlign: 'center', padding: '3rem', color: 'var(--text-muted)' }}><Loader2 size={24} className="spin" /> Loading submission...</div>
            ) : submissionDetails ? (
              <div>
                {/* Header Summary */}
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem', padding: '0.85rem 1rem', background: 'var(--bg-input)', borderRadius: '0.75rem', border: '1px solid var(--border)' }}>
                  <div>
                    <h3 style={{ margin: 0, fontSize: '1rem', color: 'var(--text-primary)' }}>{submissionDetails.student_name} ({submissionDetails.reg_number})</h3>
                    <span style={{ fontSize: '0.775rem', color: 'var(--text-muted)' }}>{submissionDetails.assignment_title} • Submitted {new Date(submissionDetails.submitted_at).toLocaleString()}</span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <span className={`badge ${submissionDetails.status === 'Graded' ? 'badge-success' : 'badge-warning'}`} style={{ fontSize: '0.8rem', padding: '0.3rem 0.6rem' }}>
                      {submissionDetails.status}
                    </span>
                    <button className="btn btn-primary" onClick={handleAIEvaluateSubmission} disabled={evaluatingAI} style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.825rem', background: 'linear-gradient(135deg, #8b5cf6, #ec4899)', border: 'none' }}>
                      {evaluatingAI ? <><Loader2 size={14} className="spin" /> AI Checking...</> : <><Sparkles size={14} /> ✨ Evaluate with AI</>}
                    </button>
                  </div>
                </div>

                {/* Attached Document (PDF / DOCX) */}
                {submissionDetails.attached_file_url && (
                  <div style={{ marginBottom: '1.25rem', padding: '0.75rem 1rem', background: 'var(--bg-tertiary)', borderRadius: '0.6rem', border: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <FileText size={18} style={{ color: 'var(--accent)' }} />
                      <div>
                        <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                          Attached Document: {submissionDetails.attached_file_name || 'Student Document'}
                        </div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                          PDF / DOCX file submitted by student
                        </div>
                      </div>
                    </div>
                    <a
                      href={submissionDetails.attached_file_url.startsWith('http') 
                        ? submissionDetails.attached_file_url 
                        : `${window.location.protocol}//${window.location.hostname}:8001${submissionDetails.attached_file_url}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="btn btn-secondary"
                      style={{ fontSize: '0.8rem', padding: '0.35rem 0.75rem', display: 'flex', alignItems: 'center', gap: '0.35rem', textDecoration: 'none' }}
                    >
                      <FileText size={14} /> View File <ExternalLink size={13} />
                    </a>
                  </div>
                )}

                {/* AI Summary Banner if generated */}
                {aiEvaluationResult && (
                  <div style={{ marginBottom: '1.25rem', padding: '1rem', background: 'rgba(139, 92, 246, 0.08)', borderRadius: '0.75rem', border: '1.5px solid rgba(139, 92, 246, 0.3)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
                      <span style={{ fontSize: '0.85rem', fontWeight: 700, color: '#8b5cf6', display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                        <Sparkles size={16} /> AI Suggested Grade: {aiEvaluationResult.suggested_total_score} / {aiEvaluationResult.total_max_marks} ({aiEvaluationResult.suggested_percentage}%)
                      </span>
                      <span className="badge badge-success">Partial Credit Applied</span>
                    </div>
                    <p style={{ margin: 0, fontSize: '0.825rem', color: 'var(--text-secondary)' }}>AI auto-assessed student response logic against the model rubrics. You can adjust the awarded marks per question below before saving.</p>
                  </div>
                )}

                {/* Questions & Student Answers */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', maxHeight: '420px', overflowY: 'auto', paddingRight: '0.25rem' }}>
                  {(submissionDetails.questions || []).map((q, idx) => {
                    const qEval = aiEvaluationResult?.question_evaluations?.find(e => e.question_id === q.question_id);
                    return (
                      <div key={q.question_id} className="question-card">
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
                          <span className="question-number">Q{idx + 1}</span>
                          <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-muted)' }}>Max: {q.marks} marks</span>
                        </div>

                        <p style={{ margin: '0.4rem 0', fontWeight: 600, fontSize: '0.875rem' }}>{q.question_text}</p>

                        {q.correct_answer && (
                          <div style={{ padding: '0.4rem 0.6rem', background: 'rgba(16,185,129,0.08)', borderRadius: '0.4rem', fontSize: '0.775rem', marginBottom: '0.5rem', border: '1px solid rgba(16,185,129,0.2)' }}>
                            <strong style={{ color: '#10b981' }}>Model Rubric:</strong> {q.correct_answer}
                          </div>
                        )}

                        <div style={{ padding: '0.65rem 0.85rem', background: 'var(--bg-input)', borderRadius: '0.5rem', border: '1px solid var(--border)', marginBottom: '0.75rem' }}>
                          <span style={{ fontSize: '0.725rem', fontWeight: 700, color: 'var(--text-muted)', display: 'block', marginBottom: '0.25rem', textTransform: 'uppercase' }}>Student Response:</span>
                          <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--text-primary)', whiteSpace: 'pre-wrap' }}>{q.student_answer || <em>No response submitted for this question.</em>}</p>
                        </div>

                        {/* AI Breakdown for this question if evaluated */}
                        {qEval && (
                          <div style={{ padding: '0.65rem 0.85rem', background: 'rgba(139, 92, 246, 0.06)', borderRadius: '0.5rem', border: '1px dashed rgba(139, 92, 246, 0.3)', marginBottom: '0.75rem' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.35rem' }}>
                              <span style={{ fontSize: '0.775rem', fontWeight: 700, color: '#8b5cf6' }}>AI Suggested: {qEval.suggested_marks} / {qEval.max_marks} marks</span>
                              <span style={{ fontSize: '0.725rem', color: 'var(--text-muted)' }}>Relevance: {qEval.relevance_score}</span>
                            </div>
                            <p style={{ margin: '0 0 0.35rem', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{qEval.feedback_summary}</p>
                            {qEval.criteria_breakdown && (
                              <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap' }}>
                                {Object.entries(qEval.criteria_breakdown).map(([k, v]) => (
                                  <span key={k} className="badge badge-info" style={{ fontSize: '0.675rem' }}>{k}: {v}</span>
                                ))}
                              </div>
                            )}
                          </div>
                        )}

                        {/* Marks Input */}
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '0.5rem', paddingTop: '0.4rem', borderTop: '1px solid var(--border)' }}>
                          <label style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)' }}>Awarded Marks:</label>
                          <input
                            type="number"
                            className="input"
                            value={marksAwardedMap[q.question_id] ?? 0}
                            onChange={e => {
                              const val = parseFloat(e.target.value) || 0;
                              setMarksAwardedMap(prev => ({ ...prev, [q.question_id]: Math.min(q.marks, Math.max(0, val)) }));
                            }}
                            style={{ width: '80px', padding: '0.25rem 0.5rem', fontSize: '0.85rem' }}
                            min={0}
                            max={q.marks}
                            step={0.5}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>

                {/* Footer Actions */}
                <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '1.25rem', paddingTop: '0.85rem', borderTop: '1px solid var(--border)', alignItems: 'center' }}>
                  <button className="btn btn-ghost" onClick={() => setSelectedSubmissionId(null)}>Cancel</button>
                  <button className="btn btn-primary" onClick={handleSaveSubmissionGrade} disabled={savingGrade}>
                    {savingGrade ? <><Loader2 size={14} className="spin" /> Saving Grade...</> : <><Save size={14} /> Save Final Grade</>}
                  </button>
                </div>
              </div>
            ) : null}
          </div>
        </div>
      </div>
    );
  };

  const renderRegradeModal = () => {
    if (!showRegradeModal) return null;

    const list = Array.isArray(regradeRequests) ? regradeRequests : [];

    return (
      <div className="modal-overlay" onClick={handleModalOverlayClick}>
        <div className={`modal-content${modalShaking ? ' modal-content-shake' : ''}`} onClick={e => e.stopPropagation()} style={{ width: '750px' }}>
          <div className="wizard-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <HelpCircle size={20} style={{ color: 'var(--accent)' }} />
              <div>
                <h3 style={{ margin: 0, fontSize: '1rem' }}>Student Assignment Regrade Appeals</h3>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Review student regrade reasons, adjust scores, and respond</span>
              </div>
            </div>
            <button className="btn btn-ghost" onClick={() => setShowRegradeModal(false)} style={{ padding: '0.25rem' }}><X size={18} /></button>
          </div>

          <div style={{ padding: '1.25rem' }}>
            {loadingRegrades ? (
              <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}><Loader2 size={24} className="spin" /> Loading regrade appeals...</div>
            ) : list.length === 0 ? (
              <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>No student regrade requests pending.</div>
            ) : (
              <table className="data-table" style={{ width: '100%' }}>
                <thead>
                  <tr>
                    <th>Student Name</th>
                    <th>Assignment</th>
                    <th>Reason / Appeal</th>
                    <th>Current Score</th>
                    <th>Status</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {list.map(r => {
                    const st = r?.status || 'pending';
                    return (
                      <tr key={r.id}>
                        <td>
                          <div style={{ fontWeight: 600 }}>{r.student_name || 'Student'}</div>
                          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{r.reg_number || ''}</div>
                        </td>
                        <td>{r.assignment_title || 'N/A'}</td>
                        <td style={{ fontSize: '0.8rem', maxWidth: '220px' }}>"{r.reason || ''}"</td>
                        <td><strong>{r.current_score ?? 0} / {r.total_marks ?? 100}</strong></td>
                        <td>
                          <span className={`badge ${st === 'approved' ? 'badge-success' : st === 'rejected' ? 'badge-danger' : 'badge-warning'}`}>
                            {st.toUpperCase()}
                          </span>
                        </td>
                        <td>
                          {st === 'pending' ? (
                            <div style={{ display: 'flex', gap: '0.35rem' }}>
                              <button
                                className="btn btn-primary"
                                onClick={() => {
                                  const newMarks = prompt(`Enter updated total score (out of ${r.total_marks || 100}):`, r.current_score || 0);
                                  if (newMarks !== null) {
                                    const feedback = prompt('Enter teacher feedback for student:');
                                    handleRespondRegrade(r.id, 'approved', parseInt(newMarks) || (r.current_score || 0), feedback);
                                  }
                                }}
                                style={{ fontSize: '0.7rem', padding: '0.25rem 0.5rem' }}
                              >
                                Approve
                              </button>
                              <button
                                className="btn btn-danger"
                                onClick={() => {
                                  const feedback = prompt('Enter rejection reason:');
                                  handleRespondRegrade(r.id, 'rejected', null, feedback);
                                }}
                                style={{ fontSize: '0.7rem', padding: '0.25rem 0.5rem' }}
                              >
                                Reject
                              </button>
                            </div>
                          ) : (
                            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Responded</span>
                          )}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="assignments-page">
      <style>{`
        .assignments-page { display: grid; grid-template-columns: 300px 1fr; gap: 1.25rem; height: calc(100vh - 140px); }
        .assignment-sidebar { background: var(--bg-secondary); border: 1px solid var(--border); border-radius: 0.75rem; padding: 1rem; overflow-y: auto; }
        .assignment-details { background: var(--bg-secondary); border: 1px solid var(--border); border-radius: 0.75rem; padding: 1.25rem; overflow-y: auto; }
        .assignment-card { padding: 0.75rem; border: 1px solid var(--border); border-radius: 0.5rem; cursor: pointer; transition: all 0.2s; margin-bottom: 0.5rem; }
        .assignment-card:hover { border-color: var(--accent); background: var(--accent-glow); }
        .assignment-card.selected { border-color: var(--accent); background: var(--accent-glow); }
        .quiz-detail-tabs { display: flex; gap: 0.25rem; margin-bottom: 1.25rem; padding: 0.25rem; background: var(--bg-input); border-radius: 0.5rem; }
        .tab-btn { display: flex; align-items: center; gap: 0.35rem; padding: 0.5rem 1rem; border: none; background: none; color: var(--text-muted); cursor: pointer; border-radius: 0.35rem; font-size: 0.8rem; transition: all 0.2s; }
        .tab-btn.active { background: var(--accent); color: white; }
        .tab-btn:hover:not(.active) { background: var(--bg-secondary); }
        .question-card { background: var(--bg-card); border: 1.5px solid var(--border); border-radius: 0.75rem; padding: 0.85rem; transition: all 0.2s ease; margin-bottom: 0.75rem; }
        .question-card:focus-within, .question-card:hover { border-color: var(--accent); }
        .question-number { display: inline-flex; align-items: center; justify-content: center; width: 28px; height: 28px; border-radius: 50%; background: var(--accent); color: white; font-size: 0.75rem; font-weight: 700; }
        .stat-card { background: var(--bg-input); border-radius: 0.5rem; padding: 1rem; text-align: center; }
        .stat-value { font-size: 1.5rem; font-weight: 700; color: var(--accent); }
        .stat-label { font-size: 0.75rem; color: var(--text-muted); margin-top: 0.25rem; }
        .badge { padding: 0.15rem 0.4rem; border-radius: 0.25rem; font-size: 0.7rem; font-weight: 600; }
        .badge-success { background: rgba(16,185,129,0.15); color: #10b981; }
        .badge-danger { background: rgba(239,68,68,0.15); color: #ef4444; }
        .badge-warning { background: rgba(245,158,11,0.15); color: #f59e0b; }
        .badge-info { background: var(--accent-glow); color: var(--accent); }
        .badge-muted { background: rgba(107,114,128,0.15); color: #6b7280; }
        .badge-ai { background: var(--accent-glow); color: var(--accent); border: 1px solid var(--accent); }

        .input { width: 100%; padding: 0.55rem 0.85rem; font-size: 0.85rem; font-family: inherit; color: var(--text-primary); background: var(--bg-input); border: 1.5px solid var(--border); border-radius: 0.6rem; outline: none; transition: all 0.2s ease-in-out; box-sizing: border-box; }
        .input:hover { border-color: var(--accent); }
        .input:focus { border-color: var(--border-focus, var(--accent)); background: var(--bg-card, #ffffff); box-shadow: 0 0 0 3.5px var(--accent-glow); }
        .input::placeholder { color: var(--text-muted); font-size: 0.82rem; opacity: 0.85; }
        select.input option { background: var(--bg-secondary); color: var(--text-primary); }
        textarea.input { resize: vertical; min-height: 65px; line-height: 1.45; }
        .form-label { display: flex; align-items: center; gap: 0.35rem; font-size: 0.725rem; font-weight: 700; color: var(--text-secondary); margin-bottom: 0.35rem; text-transform: uppercase; letter-spacing: 0.04em; }

        .modal-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(15, 23, 42, 0.65); display: flex; align-items: center; justify-content: center; z-index: 1000; backdrop-filter: blur(8px); animation: fadeIn 0.2s ease-out; }
        .modal-content { background: var(--bg-secondary); border: 1px solid var(--border); border-radius: 1.25rem; width: 760px; max-width: 92vw; max-height: 88vh; overflow-y: auto; box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25); animation: modalSlideUp 0.25s cubic-bezier(0.16, 1, 0.3, 1); }
        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
        @keyframes modalSlideUp { from { transform: translateY(16px) scale(0.98); opacity: 0; } to { transform: translateY(0) scale(1); opacity: 1; } }
        .modal-scroll-area::-webkit-scrollbar, .modal-content::-webkit-scrollbar { width: 6px; }
        .modal-scroll-area::-webkit-scrollbar-track, .modal-content::-webkit-scrollbar-track { background: transparent; }
        .modal-scroll-area::-webkit-scrollbar-thumb, .modal-content::-webkit-scrollbar-thumb { background: var(--border); border-radius: 10px; }
        .modal-scroll-area::-webkit-scrollbar-thumb:hover, .modal-content::-webkit-scrollbar-thumb:hover { background: var(--text-muted); }
        .wizard-header { display: flex; justify-content: space-between; align-items: center; padding: 1.1rem 1.5rem; border-bottom: 1px solid var(--border); background: var(--bg-card); border-top-left-radius: 1.25rem; border-top-right-radius: 1.25rem; }
        .wizard-mode-toggle { display: flex; padding: 0.6rem 1.5rem; gap: 0.5rem; border-bottom: 1px solid var(--border); background: var(--bg-input); }
        .mode-btn { display: flex; align-items: center; gap: 0.4rem; padding: 0.55rem 1.25rem; border: 1.5px solid var(--border); background: var(--bg-secondary); color: var(--text-secondary); border-radius: 0.6rem; cursor: pointer; font-size: 0.85rem; font-weight: 600; transition: all 0.2s ease; }
        .mode-btn.active { background: var(--accent); color: white; border-color: var(--accent); box-shadow: 0 4px 12px var(--accent-glow); }
        .mode-btn:hover:not(.active) { background: var(--bg-card); border-color: var(--accent); color: var(--accent); }
        .wizard-body { padding: 1.5rem; }
        .wizard-steps { display: flex; gap: 0.5rem; margin-bottom: 1.5rem; padding: 0.75rem; background: var(--bg-input); border-radius: 0.75rem; border: 1px solid var(--border); }
        .wizard-step { display: flex; align-items: center; gap: 0.4rem; font-size: 0.8rem; font-weight: 500; color: var(--text-muted); flex: 1; }
        .wizard-step.active { color: var(--accent); font-weight: 700; }
        .wizard-step.completed { color: #10b981; }
        .step-number { width: 26px; height: 26px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 0.75rem; font-weight: 700; border: 2px solid var(--border); background: var(--bg-secondary); }
        .wizard-step.active .step-number { border-color: var(--accent); background: var(--accent); color: white; box-shadow: 0 0 0 3px var(--accent-glow); }
        .wizard-step.completed .step-number { border-color: #10b981; background: #10b981; color: white; }
        .material-checkbox { display: flex; align-items: center; gap: 0.6rem; padding: 0.65rem 0.85rem; margin: 0.35rem 0; border: 1.5px solid var(--border); border-radius: 0.6rem; cursor: pointer; transition: all 0.2s ease; background: var(--bg-secondary); }
        .material-checkbox:hover { border-color: var(--accent); background: var(--bg-input); }
        .material-checkbox.selected { border-color: var(--accent); background: var(--accent-glow); }
        .material-checkbox input { accent-color: var(--accent); width: 16px; height: 16px; }
        .type-chip { display: flex; align-items: center; gap: 0.35rem; padding: 0.4rem 0.85rem; border: 1.5px solid var(--border); border-radius: 2rem; font-size: 0.775rem; font-weight: 600; cursor: pointer; transition: all 0.2s ease; background: var(--bg-secondary); color: var(--text-secondary); }
        .type-chip.active { background: var(--accent-glow); border-color: var(--accent); color: var(--accent); }
        .spin { animation: spin 1s linear infinite; }
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }

        /* Shake animation for inline modal-content elements */
        @keyframes inlineModalShake {
          0%, 100% { transform: translateX(0); }
          10%, 50%, 90% { transform: translateX(-6px); }
          30%, 70% { transform: translateX(6px); }
        }
        .modal-content-shake {
          animation: inlineModalShake 0.45s cubic-bezier(0.36, 0.07, 0.19, 0.97) both !important;
          border-color: #f59e0b !important;
          box-shadow: 0 0 0 3px rgba(245, 158, 11, 0.25), 0 25px 50px -12px rgba(0, 0, 0, 0.25) !important;
        }
      `}</style>

      {renderAssignmentList()}
      {renderAssignmentDetails()}
      {renderCreateWizard()}
      {renderEvaluationModal()}
      {renderRegradeModal()}
    </div>
  );
}
