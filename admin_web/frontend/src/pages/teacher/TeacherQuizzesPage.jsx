import { useState, useEffect, useRef, useCallback } from 'react';
import { teacherPortalApi } from '../../services/api';
import { ClipboardList, Users, BarChart3, Edit, Eye, Save, Settings, Calendar, HelpCircle, Check, AlertCircle, Plus, Sparkles, X, ChevronRight, Loader2, Trash2, BookOpen, Brain, Wand2, RefreshCw, Video, FileText } from 'lucide-react';
import toast from 'react-hot-toast';

export default function TeacherQuizzesPage() {
  const [quizzes, setQuizzes] = useState([]);
  const [loading, setLoading] = useState(true);
  
  // Tab control: 'quizzes' | 'submissions' | 'analytics'
  const [activeTab, setActiveTab] = useState('quizzes');
  const [quizFilterTab, setQuizFilterTab] = useState('active'); // 'active' | 'completed'
  const [selectedQuizId, setSelectedQuizId] = useState(null);
  
  // Student Marks Modal states
  const [showStudentMarksModal, setShowStudentMarksModal] = useState(false);
  const [studentMarksQuiz, setStudentMarksQuiz] = useState(null);
  const [studentMarksList, setStudentMarksList] = useState([]);
  const [loadingStudentMarks, setLoadingStudentMarks] = useState(false);
  
  // Details data states
  const [quizDetails, setQuizDetails] = useState(null);
  const [submissions, setSubmissions] = useState([]);
  const [analytics, setAnalytics] = useState(null);
  const [loadingDetails, setLoadingDetails] = useState(false);

  // Edit states
  const [isEditing, setIsEditing] = useState(false);
  const [editTitle, setEditTitle] = useState('');
  const [editTimeLimit, setEditTimeLimit] = useState(10);
  const [editPerQuestionTimer, setEditPerQuestionTimer] = useState(30);
  const [editMaxQuestionsPerStudent, setEditMaxQuestionsPerStudent] = useState('');
  const [editShowHints, setEditShowHints] = useState(false);
  const [editIsPublished, setEditIsPublished] = useState(false);
  const [editQuestions, setEditQuestions] = useState([]);

  // ═══════════════════════════════════════════════════════════
  //  CREATE QUIZ WIZARD STATES
  // ═══════════════════════════════════════════════════════════
  const [showCreateWizard, setShowCreateWizard] = useState(false);
  const [createMode, setCreateMode] = useState('manual'); // 'manual' | 'ai'
  const [wizardStep, setWizardStep] = useState(1); // 1=select materials, 2=configure, 3=preview

  // Manual create states
  const [manualTitle, setManualTitle] = useState('');
  const [manualQuizType, setManualQuizType] = useState('post');
  const [manualTimeLimit, setManualTimeLimit] = useState(10);
  const [manualPerQuestionTimer, setManualPerQuestionTimer] = useState(30);
  const [manualMaxQuestionsPerStudent, setManualMaxQuestionsPerStudent] = useState('');
  const [manualDueDate, setManualDueDate] = useState('');
  const [manualLectureId, setManualLectureId] = useState(null);
  const [manualIsPublished, setManualIsPublished] = useState(false);
  const [manualQuestions, setManualQuestions] = useState([{
    question_text: '', option_a: '', option_b: '', option_c: '', option_d: '',
    correct_answer: 'A', difficulty: 'medium'
  }]);

  // AI generate states
  const [availableMaterials, setAvailableMaterials] = useState([]);
  const [selectedMaterialIds, setSelectedMaterialIds] = useState([]);
  const [aiNumQuestions, setAiNumQuestions] = useState(10);
  const [aiDifficulty, setAiDifficulty] = useState('medium');
  const [aiQuizQuestionTypes, setAiQuizQuestionTypes] = useState(['mcq', 'true_false']);
  const [aiGeneratedQuestions, setAiGeneratedQuestions] = useState([]);
  const [aiGenerating, setAiGenerating] = useState(false);
  const [aiSaveTitle, setAiSaveTitle] = useState('');
  const [aiSaveQuizType, setAiSaveQuizType] = useState('post');
  const [aiSaveTimeLimit, setAiSaveTimeLimit] = useState(10);
  const [aiSavePerQuestionTimer, setAiSavePerQuestionTimer] = useState(30);
  const [aiSaveMaxQuestionsPerStudent, setAiSaveMaxQuestionsPerStudent] = useState('');
  const [aiSaveDueDate, setAiSaveDueDate] = useState('');
  const [aiSaveLectureId, setAiSaveLectureId] = useState(null);
  const [aiSaveIsPublished, setAiSaveIsPublished] = useState(false);
  const [savingAIQuiz, setSavingAIQuiz] = useState(false);

  // Teacher sections & lectures for selection
  const [sections, setSections] = useState([]);
  const [lectures, setLectures] = useState([]);
  const [loadingLectures, setLoadingLectures] = useState(false);

  const fetchQuizzesList = async () => {
    try {
      const res = await teacherPortalApi.listQuizzes();
      const list = res.data || [];
      setQuizzes(list);
      
      const activeList = list.filter(q => q.is_published && !q.is_deleted && q.attempts_count === 0);
      if (activeList.length > 0 && !selectedQuizId) {
        setSelectedQuizId(activeList[0].id);
      } else if (activeList.length === 0) {
        setSelectedQuizId(null);
      }
    } catch (err) {
      toast.error('Failed to load quizzes.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchQuizzesList();
    fetchSections();
  }, []);

  const fetchSections = async () => {
    try {
      const res = await teacherPortalApi.sections();
      setSections(res.data);
    } catch (err) { /* silently fail */ }
  };

  const fetchLecturesForSection = async (sectionId) => {
    setLoadingLectures(true);
    try {
      const res = await teacherPortalApi.listLectures(sectionId);
      setLectures(res.data);
    } catch (err) { setLectures([]); }
    finally { setLoadingLectures(false); }
  };

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
        setEditPerQuestionTimer(res.data.per_question_timer_seconds || 30);
        setEditMaxQuestionsPerStudent(res.data.max_questions_per_student ? String(res.data.max_questions_per_student) : '');
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

  // ═══════════════════════════════════════════════════════════
  //  QUIZ EDIT HANDLERS
  // ═══════════════════════════════════════════════════════════
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

  const handleDeleteQuestion = (index) => {
    setEditQuestions(prev => prev.filter((_, i) => i !== index));
  };

  const handleSaveQuiz = async () => {
    try {
      await teacherPortalApi.updateQuiz(selectedQuizId, {
        title: editTitle,
        is_published: editIsPublished,
        time_limit_mins: editTimeLimit,
        per_question_timer_seconds: editPerQuestionTimer,
        max_questions_per_student: editMaxQuestionsPerStudent ? parseInt(editMaxQuestionsPerStudent) : null,
        show_hints: editShowHints,
        questions: editQuestions
      });
      toast.success('Quiz updated successfully!');
      setIsEditing(false);
      if (editIsPublished) {
        setQuizFilterTab('active');
      } else {
        setQuizFilterTab('draft');
      }
      loadTabDetails(selectedQuizId, 'quizzes');
      fetchQuizzesList();
    } catch (err) {
      toast.error('Failed to save quiz.');
    }
  };

  // ═══════════════════════════════════════════════════════════
  //  CREATE WIZARD HANDLERS
  // ═══════════════════════════════════════════════════════════
  const openCreateWizard = () => {
    setShowCreateWizard(true);
    setCreateMode('manual');
    setWizardStep(1);
    setManualTitle('');
    setManualQuizType('post');
    setManualTimeLimit(10);
    setManualPerQuestionTimer(30);
    setManualMaxQuestionsPerStudent('');
    setManualLectureId(null);
    setManualIsPublished(false);
    setManualQuestions([{
      question_text: '', option_a: '', option_b: '', option_c: '', option_d: '',
      correct_answer: 'A', difficulty: 'medium'
    }]);
    setSelectedMaterialIds([]);
    setAiGeneratedQuestions([]);
    setAiSaveTitle('');
  };

  const fetchAvailableMaterials = async () => {
    try {
      const res = await teacherPortalApi.getAvailableMaterials();
      setAvailableMaterials(res.data);
    } catch (err) {
      toast.error('Failed to load available materials.');
    }
  };

  const toggleMaterial = (id) => {
    setSelectedMaterialIds(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id]
    );
  };

  const handleAIGenerate = async () => {
    if (selectedMaterialIds.length === 0) {
      toast.error('Please select at least one material.');
      return;
    }
    setAiGenerating(true);
    try {
      const res = await teacherPortalApi.generateAIQuiz({
        material_ids: selectedMaterialIds,
        num_questions: aiNumQuestions,
        difficulty: aiDifficulty,
        question_types: aiQuizQuestionTypes
      });
      setAiGeneratedQuestions(res.data.questions || []);
      setWizardStep(3);
      toast.success(`Generated ${res.data.questions?.length || 0} questions!`);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'AI generation failed.');
    } finally {
      setAiGenerating(false);
    }
  };

  const handleAIQuestionEdit = (index, field, value) => {
    setAiGeneratedQuestions(prev => {
      const copy = [...prev];
      copy[index] = { ...copy[index], [field]: value };
      return copy;
    });
  };

  const handleAIQuestionDelete = (index) => {
    setAiGeneratedQuestions(prev => prev.filter((_, i) => i !== index));
  };

  const handleSaveAIQuiz = async () => {
    if (!aiSaveLectureId) {
      toast.error('Please select a lecture to attach this quiz to.');
      return;
    }
    if (!aiSaveTitle.trim()) {
      toast.error('Please enter a quiz title.');
      return;
    }
    setSavingAIQuiz(true);
    try {
      const res = await teacherPortalApi.saveAIQuiz({
        lecture_id: aiSaveLectureId,
        title: aiSaveTitle,
        quiz_type: aiSaveQuizType,
        time_limit_mins: aiSaveTimeLimit,
        per_question_timer_seconds: aiSavePerQuestionTimer,
        max_questions_per_student: aiSaveMaxQuestionsPerStudent ? parseInt(aiSaveMaxQuestionsPerStudent) : null,
        due_date: aiSaveDueDate || null,
        is_published: aiSaveIsPublished,
        source_material_ids: selectedMaterialIds,
        questions: aiGeneratedQuestions.map(q => ({
          question_text: q.question_text || 'Untitled Question',
          option_a: q.option_a != null ? String(q.option_a) : '',
          option_b: q.option_b != null ? String(q.option_b) : '',
          option_c: q.option_c != null ? String(q.option_c) : '',
          option_d: q.option_d != null ? String(q.option_d) : '',
          correct_answer: q.correct_answer || 'A',
          difficulty: q.difficulty || 'medium',
          question_type: q.question_type || 'mcq'
        }))
      });
      const savedQuizId = res.data?.quiz_id;
      toast.success('AI quiz saved successfully!');
      setShowCreateWizard(false);
      
      const targetTab = aiSaveIsPublished ? 'active' : 'draft';
      setQuizFilterTab(targetTab);
      
      // Fetch latest quizzes list and select the newly created quiz
      const listRes = await teacherPortalApi.listQuizzes();
      const updatedList = listRes.data || [];
      setQuizzes(updatedList);

      if (savedQuizId) {
        setSelectedQuizId(savedQuizId);
      } else if (updatedList.length > 0) {
        setSelectedQuizId(updatedList[0].id);
      }
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to save quiz.');
    } finally {
      setSavingAIQuiz(false);
    }
  };

  const handleManualQuestionEdit = (index, field, value) => {
    setManualQuestions(prev => {
      const copy = [...prev];
      copy[index] = { ...copy[index], [field]: value };
      return copy;
    });
  };

  const handleSaveManualQuiz = async () => {
    if (!manualLectureId) {
      toast.error('Please select a lecture.');
      return;
    }
    if (!manualTitle.trim()) {
      toast.error('Please enter a quiz title.');
      return;
    }
    try {
      await teacherPortalApi.createManualQuiz(manualLectureId, {
        title: manualTitle,
        quiz_type: manualQuizType,
        time_limit_mins: manualTimeLimit,
        per_question_timer_seconds: manualPerQuestionTimer,
        max_questions_per_student: manualMaxQuestionsPerStudent ? parseInt(manualMaxQuestionsPerStudent) : null,
        due_date: manualDueDate || null,
        is_published: manualIsPublished,
        questions: manualQuestions
      });
      toast.success('Quiz created successfully!');
      setShowCreateWizard(false);
      if (manualIsPublished) {
        setQuizFilterTab('active');
      } else {
        setQuizFilterTab('draft');
      }
      fetchQuizzesList();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to create quiz.');
    }
  };

  const handleDeleteQuiz = async (quizId, e) => {
    e.stopPropagation();
    if (window.confirm('Are you sure you want to end and delete this active quiz? It will move to Completed tab.')) {
      try {
        await teacherPortalApi.deleteQuiz(quizId);
        toast.success('Active quiz ended & moved to Completed!');
        setQuizFilterTab('completed');
        setSelectedQuizId(quizId);
        setActiveTab('submissions');
        fetchQuizzesList();
      } catch (err) {
        toast.error('Failed to delete quiz.');
      }
    }
  };

  const handleBulkRegrade = async () => {
    if (!selectedQuizId) return;
    if (!window.confirm('Re-grade all student responses against current answer keys?')) return;
    try {
      const res = await teacherPortalApi.regradeQuiz(selectedQuizId);
      toast.success(res.data.message || 'Quiz re-graded successfully!');
      fetchQuizDetails(selectedQuizId);
    } catch (err) {
      toast.error('Failed to re-grade quiz.');
    }
  };

  const handleOpenStudentMarksModal = async (quiz, e) => {
    if (e) e.stopPropagation();
    setStudentMarksQuiz(quiz);
    setShowStudentMarksModal(true);
    setLoadingStudentMarks(true);
    try {
      const res = await teacherPortalApi.getQuizSubmissions(quiz.id);
      setStudentMarksList(res.data || []);
    } catch (err) {
      toast.error('Failed to load student marks.');
    } finally {
      setLoadingStudentMarks(false);
    }
  };

  // Filter quizzes into Active vs Completed/Ended vs Drafts
  const activeQuizzes = quizzes.filter(q => q.is_published && !q.is_deleted && q.attempts_count === 0);
  const completedQuizzes = quizzes.filter(q => q.is_published && (q.attempts_count > 0 || q.is_deleted));
  const draftQuizzes = quizzes.filter(q => !q.is_published && !q.is_deleted);
  const displayedQuizzes = quizFilterTab === 'active' ? activeQuizzes : quizFilterTab === 'draft' ? draftQuizzes : completedQuizzes;

  // ═══════════════════════════════════════════════════════════
  //  RENDER: Quiz List Sidebar
  // ═══════════════════════════════════════════════════════════
  const renderQuizList = () => (
    <div className="quiz-sidebar">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
        <h3 style={{ margin: 0, fontSize: '1rem', color: 'var(--text-secondary)' }}>Quizzes</h3>
        <button className="btn btn-primary" onClick={openCreateWizard} style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.8rem', padding: '0.4rem 0.8rem' }}>
          <Plus size={14} /> Create Quiz
        </button>
      </div>

      {/* Active vs Completed vs Draft Tabs */}
      <div style={{ display: 'flex', gap: '0.35rem', marginBottom: '1rem', background: 'var(--bg-tertiary)', padding: '4px', borderRadius: '8px' }}>
        <button
          onClick={() => {
            setQuizFilterTab('active');
            if (activeQuizzes.length === 0) {
              setSelectedQuizId(null);
            } else if (!activeQuizzes.some(q => q.id === selectedQuizId)) {
              setSelectedQuizId(activeQuizzes[0].id);
            }
          }}
          style={{
            flex: 1,
            padding: '0.4rem 0.4rem',
            border: 'none',
            borderRadius: '6px',
            fontSize: '0.725rem',
            fontWeight: 600,
            cursor: 'pointer',
            background: quizFilterTab === 'active' ? 'var(--bg-card)' : 'transparent',
            color: quizFilterTab === 'active' ? 'var(--accent)' : 'var(--text-muted)',
            boxShadow: quizFilterTab === 'active' ? '0 1px 3px rgba(0,0,0,0.1)' : 'none'
          }}
        >
          Active ({activeQuizzes.length})
        </button>
        <button
          onClick={() => {
            setQuizFilterTab('completed');
            if (completedQuizzes.length === 0) {
              setSelectedQuizId(null);
            } else if (!completedQuizzes.some(q => q.id === selectedQuizId)) {
              setSelectedQuizId(completedQuizzes[0].id);
              setActiveTab('submissions');
            }
          }}
          style={{
            flex: 1,
            padding: '0.4rem 0.4rem',
            border: 'none',
            borderRadius: '6px',
            fontSize: '0.725rem',
            fontWeight: 600,
            cursor: 'pointer',
            background: quizFilterTab === 'completed' ? 'var(--bg-card)' : 'transparent',
            color: quizFilterTab === 'completed' ? 'var(--accent)' : 'var(--text-muted)',
            boxShadow: quizFilterTab === 'completed' ? '0 1px 3px rgba(0,0,0,0.1)' : 'none'
          }}
        >
          Completed ({completedQuizzes.length})
        </button>
        <button
          onClick={() => {
            setQuizFilterTab('draft');
            if (draftQuizzes.length === 0) {
              setSelectedQuizId(null);
            } else if (!draftQuizzes.some(q => q.id === selectedQuizId)) {
              setSelectedQuizId(draftQuizzes[0].id);
            }
          }}
          style={{
            flex: 1,
            padding: '0.4rem 0.4rem',
            border: 'none',
            borderRadius: '6px',
            fontSize: '0.725rem',
            fontWeight: 600,
            cursor: 'pointer',
            background: quizFilterTab === 'draft' ? 'var(--bg-card)' : 'transparent',
            color: quizFilterTab === 'draft' ? 'var(--accent)' : 'var(--text-muted)',
            boxShadow: quizFilterTab === 'draft' ? '0 1px 3px rgba(0,0,0,0.1)' : 'none'
          }}
        >
          Drafts ({draftQuizzes.length})
        </button>
      </div>

      {displayedQuizzes.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '2rem 1rem', color: 'var(--text-muted)' }}>
          <ClipboardList size={40} style={{ opacity: 0.3, marginBottom: '0.5rem' }} />
          <p>{quizFilterTab === 'completed' ? 'No completed quizzes yet' : quizFilterTab === 'draft' ? 'No draft quizzes' : 'No active quizzes'}</p>
        </div>
      ) : (
        displayedQuizzes.map((q, idx) => (
          <div
            key={q.id}
            className={`quiz-card ${selectedQuizId === q.id ? 'selected' : ''}`}
            onClick={() => {
              setSelectedQuizId(q.id);
              if (quizFilterTab === 'completed' || q.is_deleted) {
                setActiveTab('submissions');
                handleOpenStudentMarksModal(q);
              }
            }}
          >
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
              <div>
                <h4 style={{ margin: '0 0 0.25rem', fontSize: '0.9rem' }}>
                  {q.title || `Quiz ${idx + 1}: ${q.lecture_title}`}
                </h4>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                  {q.course_name} • {q.section_label}
                </span>
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                {quizFilterTab === 'completed' || q.is_deleted ? (
                  <span className="badge badge-danger">END</span>
                ) : quizFilterTab === 'draft' || !q.is_published ? (
                  <span className="badge badge-warning">DRAFT</span>
                ) : (
                  <span className={`badge ${q.quiz_type === 'post' ? 'badge-info' : q.quiz_type === 'pre' ? 'badge-warning' : 'badge-primary'}`}>
                    {q.quiz_type.toUpperCase()}
                  </span>
                )}
                {quizFilterTab === 'active' && !q.is_deleted && (
                  <button
                    onClick={(e) => handleDeleteQuiz(q.id, e)}
                    title="Delete & End Quiz"
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
                    <Trash2 size={14} />
                  </button>
                )}
              </div>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginTop: '0.75rem' }}>
              <div style={{ display: 'flex', gap: '0.75rem', fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                <span><HelpCircle size={12} /> {q.questions_count} Q</span>
                <span><Users size={12} /> {q.attempts_count} Attempts</span>
              </div>
              <button
                className="btn btn-ghost"
                onClick={(e) => handleOpenStudentMarksModal(q, e)}
                style={{ fontSize: '0.75rem', padding: '0.2rem 0.5rem', color: 'var(--accent)', fontWeight: 600 }}
              >
                <Eye size={12} style={{ marginRight: '3px' }} /> View Marks
              </button>
            </div>
          </div>
        ))
      )}
    </div>
  );

  // ═══════════════════════════════════════════════════════════
  //  RENDER: Quiz Details Panel
  // ═══════════════════════════════════════════════════════════
  const renderQuizDetails = () => {
    const isSelectedInDisplayed = displayedQuizzes.some(q => q.id === selectedQuizId);
    if (!selectedQuizId || !isSelectedInDisplayed) return (
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100%', color: 'var(--text-muted)' }}>
        <ClipboardList size={48} style={{ opacity: 0.25, marginBottom: '0.75rem' }} />
        <p style={{ margin: 0, fontSize: '0.9rem', fontWeight: 500 }}>Select a quiz from the list to view details</p>
      </div>
    );

    const availableTabs = quizFilterTab === 'completed'
      ? [
          { key: 'submissions', label: 'Submissions', icon: <Users size={14} /> },
          { key: 'analytics', label: 'Analytics', icon: <BarChart3 size={14} /> },
        ]
      : [
          { key: 'quizzes', label: 'Questions', icon: <ClipboardList size={14} /> },
          { key: 'submissions', label: 'Submissions', icon: <Users size={14} /> },
          { key: 'analytics', label: 'Analytics', icon: <BarChart3 size={14} /> },
        ];

    const currentTab = (quizFilterTab === 'completed' && activeTab === 'quizzes') ? 'submissions' : activeTab;

    return (
      <div className="quiz-details-panel">
        {/* Tabs */}
        <div className="quiz-detail-tabs">
          {availableTabs.map(tab => (
            <button
              key={tab.key}
              className={`tab-btn ${currentTab === tab.key ? 'active' : ''}`}
              onClick={() => setActiveTab(tab.key)}
            >
              {tab.icon} {tab.label}
            </button>
          ))}
        </div>

        {loadingDetails ? (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '3rem', color: 'var(--text-muted)' }}>
            <Loader2 size={24} className="spin" /> Loading...
          </div>
        ) : (
          <>
            {currentTab === 'quizzes' && renderQuestionsTab()}
            {currentTab === 'submissions' && renderSubmissionsTab()}
            {currentTab === 'analytics' && renderAnalyticsTab()}
          </>
        )}
      </div>
    );
  };

  const renderQuestionsTab = () => {
    if (!quizDetails) return null;
    return (
      <div>
        {/* Quiz header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem', padding: '0.75rem 1rem', background: 'var(--bg-tertiary)', borderRadius: '0.5rem' }}>
          {isEditing ? (
            <input className="input" value={editTitle} onChange={e => setEditTitle(e.target.value)} style={{ fontSize: '1rem', fontWeight: 600 }} />
          ) : (
            <h3 style={{ margin: 0, fontSize: '1rem' }}>{quizDetails.title}</h3>
          )}
          <div style={{ display: 'flex', gap: '0.5rem' }}>
            {isEditing ? (
              <>
                <button className="btn btn-success" onClick={handleSaveQuiz} style={{ fontSize: '0.8rem', padding: '0.4rem 0.75rem' }}><Save size={14} /> Save</button>
                <button className="btn btn-ghost" onClick={() => setIsEditing(false)} style={{ fontSize: '0.8rem', padding: '0.4rem 0.75rem' }}><X size={14} /> Cancel</button>
              </>
            ) : (
              <>
                <button className="btn btn-ghost" onClick={handleBulkRegrade} title="Re-grade all student submissions" style={{ fontSize: '0.8rem', padding: '0.4rem 0.75rem', color: 'var(--accent)' }}>
                  <RefreshCw size={14} style={{ marginRight: '4px' }} /> Bulk Re-Grade
                </button>
                <button className="btn btn-primary" onClick={() => setIsEditing(true)} style={{ fontSize: '0.8rem', padding: '0.4rem 0.75rem' }}><Edit size={14} /> Edit</button>
              </>
            )}
          </div>
        </div>

        {/* Settings row */}
        {isEditing && (
          <div style={{ display: 'flex', gap: '1rem', marginBottom: '1rem', flexWrap: 'wrap' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.8rem' }}>
              <HelpCircle size={14} /> Per-Question Timer:
              <input type="number" className="input" value={editPerQuestionTimer} onChange={e => setEditPerQuestionTimer(parseInt(e.target.value) || 30)} style={{ width: '60px' }} min={5} /> sec
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.8rem', cursor: 'pointer' }}>
              <input type="checkbox" checked={editShowHints} onChange={e => setEditShowHints(e.target.checked)} /> Show Hints
            </label>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.35rem', fontSize: '0.8rem', cursor: 'pointer' }}>
              <input type="checkbox" checked={editIsPublished} onChange={e => setEditIsPublished(e.target.checked)} /> Published
            </label>
          </div>
        )}

        {/* Questions */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {(isEditing ? editQuestions : quizDetails.questions).map((q, idx) => (
            <div key={idx} className="question-card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                <span className="question-number">Q{idx + 1}</span>
                <span className={`badge ${q.difficulty === 'easy' ? 'badge-success' : q.difficulty === 'hard' ? 'badge-danger' : 'badge-warning'}`} style={{ fontSize: '0.65rem' }}>
                  {q.difficulty}
                </span>
              </div>
              {isEditing ? (
                <div style={{ marginTop: '0.5rem' }}>
                  <textarea className="input" value={q.question_text} onChange={e => handleEditQuestion(idx, 'question_text', e.target.value)} rows={2} style={{ width: '100%', marginBottom: '0.5rem' }} />
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.35rem' }}>
                    {['a', 'b', 'c', 'd'].map(opt => (
                      <div key={opt} style={{ display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                        <span style={{ fontWeight: 600, fontSize: '0.75rem', minWidth: '14px' }}>{opt.toUpperCase()}</span>
                        <input className="input" value={q[`option_${opt}`]} onChange={e => handleEditQuestion(idx, `option_${opt}`, e.target.value)} style={{ flex: 1, fontSize: '0.8rem' }} />
                      </div>
                    ))}
                  </div>
                  <div style={{ display: 'flex', gap: '0.75rem', marginTop: '0.5rem', alignItems: 'center' }}>
                    <label style={{ fontSize: '0.75rem' }}>Correct:
                      <select className="input" value={q.correct_answer} onChange={e => handleEditQuestion(idx, 'correct_answer', e.target.value)} style={{ marginLeft: '0.25rem', width: '50px' }}>
                        {['A','B','C','D'].map(o => <option key={o} value={o}>{o}</option>)}
                      </select>
                    </label>
                    <label style={{ fontSize: '0.75rem' }}>Difficulty:
                      <select className="input" value={q.difficulty} onChange={e => handleEditQuestion(idx, 'difficulty', e.target.value)} style={{ marginLeft: '0.25rem' }}>
                        {['easy','medium','hard'].map(d => <option key={d} value={d}>{d}</option>)}
                      </select>
                    </label>
                    <button className="btn btn-ghost" onClick={() => handleDeleteQuestion(idx)} style={{ marginLeft: 'auto', color: 'var(--danger)', fontSize: '0.75rem', padding: '0.25rem' }}>
                      <Trash2 size={14} />
                    </button>
                  </div>
                </div>
              ) : (
                <div style={{ marginTop: '0.5rem' }}>
                  <p style={{ margin: '0 0 0.5rem', fontSize: '0.85rem' }}>{q.question_text}</p>
                  <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.25rem' }}>
                    {['a', 'b', 'c', 'd'].filter(opt => q[`option_${opt}`] != null && q[`option_${opt}`].toString().trim() !== '').map(opt => (
                      <div key={opt} style={{
                        display: 'flex', alignItems: 'center', gap: '0.35rem', padding: '0.3rem 0.5rem',
                        borderRadius: '0.25rem', fontSize: '0.8rem',
                        background: q.correct_answer === opt.toUpperCase() ? 'rgba(16, 185, 129, 0.1)' : 'transparent',
                        border: q.correct_answer === opt.toUpperCase() ? '1px solid rgba(16, 185, 129, 0.3)' : '1px solid transparent'
                      }}>
                        {q.correct_answer === opt.toUpperCase() && <Check size={12} style={{ color: '#10b981' }} />}
                        <span style={{ fontWeight: 600, color: 'var(--text-muted)', minWidth: '14px' }}>{opt.toUpperCase()}.</span>
                        {q[`option_${opt}`]}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
        {isEditing && (
          <button className="btn btn-ghost" onClick={handleAddQuestion} style={{ marginTop: '0.75rem', width: '100%', border: '1px dashed var(--border)' }}>
            <Plus size={14} /> Add Question
          </button>
        )}
      </div>
    );
  };

  const renderSubmissionsTab = () => (
    <div>
      {submissions.length === 0 ? (
        <div style={{ textAlign: 'center', padding: '2rem', color: 'var(--text-muted)' }}>No submissions yet.</div>
      ) : (
        <table className="data-table" style={{ width: '100%' }}>
          <thead>
            <tr><th>Student</th><th>Reg #</th><th>Score</th><th>Submitted At</th></tr>
          </thead>
          <tbody>
            {submissions.map((s, i) => (
              <tr key={i}>
                <td>{s.student_name}</td>
                <td>{s.reg_number}</td>
                <td>
                  <span className={`badge ${s.score_percentage >= 70 ? 'badge-success' : s.score_percentage >= 50 ? 'badge-warning' : 'badge-danger'}`}>
                    {s.correct_count}/{s.total_questions} ({s.score_percentage}%)
                  </span>
                </td>
                <td style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>{new Date(s.submitted_at).toLocaleString()}</td>
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
          <div className="stat-card"><div className="stat-value">{analytics.attempts_count}</div><div className="stat-label">Total Attempts</div></div>
          <div className="stat-card"><div className="stat-value">{analytics.avg_score}%</div><div className="stat-label">Avg Score</div></div>
          <div className="stat-card"><div className="stat-value">{analytics.total_questions}</div><div className="stat-label">Questions</div></div>
        </div>
        <h4 style={{ fontSize: '0.9rem', marginBottom: '0.75rem' }}>Question Performance</h4>
        {(analytics.question_performance || []).map((qp, i) => (
          <div key={i} style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem', padding: '0.5rem', background: 'var(--bg-tertiary)', borderRadius: '0.35rem' }}>
            <span style={{ fontSize: '0.8rem', flex: 1 }}>{qp.question_text}</span>
            <span className={`badge ${qp.difficulty_rating === 'Easy' ? 'badge-success' : qp.difficulty_rating === 'Hard' ? 'badge-danger' : 'badge-warning'}`} style={{ fontSize: '0.7rem' }}>
              {qp.success_rate}% ({qp.difficulty_rating})
            </span>
          </div>
        ))}
      </div>
    );
  };

  // ═══════════════════════════════════════════════════════════
  //  RENDER: Create Quiz Wizard (Modal)
  // ═══════════════════════════════════════════════════════════
  // ── Overlay Dismiss Protection: shake + toast instead of close ──
  const [wizardShaking, setWizardShaking] = useState(false);
  const handleWizardOverlayClick = useCallback((e) => {
    if (e.target !== e.currentTarget) return;
    setWizardShaking(true);
    setTimeout(() => setWizardShaking(false), 500);
    toast('Please close this dialog first using the ✕ button', { icon: '⚠️', duration: 2500 });
  }, []);

  const renderCreateWizard = () => {
    if (!showCreateWizard) return null;

    return (
      <div className="modal-overlay" onClick={handleWizardOverlayClick}>
        <div className={`modal-content wizard-modal${wizardShaking ? ' modal-content-shake' : ''}`} onClick={e => e.stopPropagation()}>
          {/* Header */}
          <div className="wizard-header">
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Wand2 size={20} style={{ color: 'var(--accent)' }} />
              <h2 style={{ margin: 0, fontSize: '1.1rem' }}>Create Quiz</h2>
            </div>
            <button className="btn btn-ghost" onClick={() => setShowCreateWizard(false)} style={{ padding: '0.25rem' }}><X size={18} /></button>
          </div>

          {/* Mode Toggle */}
          <div className="wizard-mode-toggle">
            <button className={`mode-btn ${createMode === 'manual' ? 'active' : ''}`} onClick={() => { setCreateMode('manual'); setWizardStep(1); }}>
              <BookOpen size={16} /> Manual
            </button>
            <button className={`mode-btn ${createMode === 'ai' ? 'active' : ''}`} onClick={() => { setCreateMode('ai'); setWizardStep(1); fetchAvailableMaterials(); }}>
              <Brain size={16} /> AI Generate
            </button>
          </div>

          {/* Body */}
          <div className="wizard-body">
            {createMode === 'manual' ? renderManualMode() : renderAIMode()}
          </div>
        </div>
      </div>
    );
  };

  const renderManualMode = () => (
    <div>
      {/* Section & Lecture selection */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.85rem', marginBottom: '1rem' }}>
        <div>
          <label className="form-label">Course Section</label>
          <select className="input" onChange={e => { const sid = parseInt(e.target.value); if (sid) fetchLecturesForSection(sid); }} defaultValue="">
            <option value="" disabled>Select course section...</option>
            {sections.map(s => <option key={s.id} value={s.id}>{s.course_name} - {s.section_label}</option>)}
          </select>
        </div>
        <div>
          <label className="form-label">Lecture Topic</label>
          <select className="input" value={manualLectureId || ''} onChange={e => setManualLectureId(parseInt(e.target.value))} disabled={loadingLectures}>
            <option value="" disabled>Select lecture topic...</option>
            {lectures.map(l => <option key={l.id} value={l.id}>{l.title}</option>)}
          </select>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '2.5fr 1.2fr 1.5fr', gap: '0.85rem', marginBottom: '1rem' }}>
        <div>
          <label className="form-label">Quiz Title</label>
          <input className="input" value={manualTitle} onChange={e => setManualTitle(e.target.value)} placeholder="e.g., Chapter 1: Introduction to Data Structures" />
        </div>
        <div>
          <label className="form-label">Timer/Q (sec)</label>
          <input type="number" className="input" value={manualPerQuestionTimer} onChange={e => setManualPerQuestionTimer(parseInt(e.target.value) || 30)} placeholder="e.g., 30" min={5} />
        </div>
        <div>
          <label className="form-label">Deadline Date</label>
          <input type="datetime-local" className="input" value={manualDueDate} onChange={e => setManualDueDate(e.target.value)} />
        </div>
      </div>

      {/* Questions */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
        <h4 style={{ fontSize: '0.9rem', margin: 0, color: 'var(--text-primary)', fontWeight: 600 }}>Questions ({manualQuestions.length})</h4>
        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Configure options & correct answers</span>
      </div>

      <div className="modal-scroll-area" style={{ maxHeight: '320px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '0.75rem', paddingRight: '0.35rem' }}>
        {manualQuestions.map((q, idx) => (
          <div key={idx} className="question-card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.5rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <span className="question-number">Q{idx + 1}</span>
                <select
                  className="input"
                  value={q.question_type || 'mcq'}
                  onChange={e => {
                    const type = e.target.value;
                    handleManualQuestionEdit(idx, 'question_type', type);
                    if (type === 'true_false') {
                      handleManualQuestionEdit(idx, 'option_a', 'True');
                      handleManualQuestionEdit(idx, 'option_b', 'False');
                      handleManualQuestionEdit(idx, 'option_c', '');
                      handleManualQuestionEdit(idx, 'option_d', '');
                      handleManualQuestionEdit(idx, 'correct_answer', 'A');
                    }
                  }}
                  style={{ width: '150px', fontSize: '0.75rem', padding: '0.2rem' }}
                >
                  <option value="mcq">Multiple Choice (MCQ)</option>
                  <option value="true_false">True / False</option>
                </select>
              </div>
              <button className="btn btn-ghost" onClick={() => setManualQuestions(prev => prev.filter((_, i) => i !== idx))} style={{ padding: '0.2rem 0.4rem', color: 'var(--danger)' }} title="Delete Question"><Trash2 size={14} /></button>
            </div>
            <textarea className="input" value={q.question_text} onChange={e => handleManualQuestionEdit(idx, 'question_text', e.target.value)} rows={2} placeholder={q.question_type === 'true_false' ? "Enter statement (e.g., QuickSort is an in-place sorting algorithm)..." : "Enter question prompt here... (e.g., What is the time complexity of QuickSort?)"} style={{ width: '100%', marginBottom: '0.5rem', fontSize: '0.85rem' }} />
            
            {q.question_type === 'true_false' ? (
              <div style={{ display: 'flex', gap: '0.6rem', marginBottom: '0.5rem' }}>
                <div className="type-chip active" style={{ flex: 1, justifyContent: 'center' }}>Option A: True</div>
                <div className="type-chip active" style={{ flex: 1, justifyContent: 'center' }}>Option B: False</div>
              </div>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.4rem', marginBottom: '0.5rem' }}>
                <input className="input" value={q.option_a} onChange={e => handleManualQuestionEdit(idx, 'option_a', e.target.value)} placeholder="Option A (e.g., O(n log n))" style={{ fontSize: '0.8rem' }} />
                <input className="input" value={q.option_b} onChange={e => handleManualQuestionEdit(idx, 'option_b', e.target.value)} placeholder="Option B (e.g., O(n^2))" style={{ fontSize: '0.8rem' }} />
                <input className="input" value={q.option_c} onChange={e => handleManualQuestionEdit(idx, 'option_c', e.target.value)} placeholder="Option C (e.g., O(n))" style={{ fontSize: '0.8rem' }} />
                <input className="input" value={q.option_d} onChange={e => handleManualQuestionEdit(idx, 'option_d', e.target.value)} placeholder="Option D (e.g., O(1))" style={{ fontSize: '0.8rem' }} />
              </div>
            )}
            
            <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', background: 'var(--bg-input)', padding: '0.4rem 0.6rem', borderRadius: '0.5rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)' }}>Correct:</span>
                <select className="input" value={q.correct_answer} onChange={e => handleManualQuestionEdit(idx, 'correct_answer', e.target.value)} style={{ width: '110px', padding: '0.25rem 0.4rem', fontSize: '0.75rem' }}>
                  {q.question_type === 'true_false' ? (
                    <>
                      <option value="A">A (True)</option>
                      <option value="B">B (False)</option>
                    </>
                  ) : (
                    ['A','B','C','D'].map(o => <option key={o} value={o}>Option {o}</option>)
                  )}
                </select>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)' }}>Difficulty:</span>
                <select className="input" value={q.difficulty} onChange={e => handleManualQuestionEdit(idx, 'difficulty', e.target.value)} style={{ width: '100px', padding: '0.25rem 0.4rem', fontSize: '0.75rem' }}>
                  <option value="easy">Easy</option>
                  <option value="medium">Medium</option>
                  <option value="hard">Hard</option>
                </select>
              </div>
            </div>
          </div>
        ))}
      </div>

      <button className="btn btn-ghost" onClick={() => setManualQuestions(prev => [...prev, { question_text: '', option_a: '', option_b: '', option_c: '', option_d: '', correct_answer: 'A', difficulty: 'medium' }])} style={{ marginTop: '0.75rem', width: '100%', border: '1.5px dashed var(--border)', fontSize: '0.825rem', padding: '0.5rem', borderRadius: '0.6rem' }}>
        <Plus size={14} /> Add Another Question
      </button>

      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', marginTop: '1.25rem', paddingTop: '0.85rem', borderTop: '1px solid var(--border)', alignItems: 'center' }}>
        <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.825rem', marginRight: 'auto', cursor: 'pointer', userSelect: 'none', color: 'var(--text-secondary)' }}>
          <input type="checkbox" checked={manualIsPublished} onChange={e => setManualIsPublished(e.target.checked)} style={{ accentColor: 'var(--accent)', width: '16px', height: '16px' }} /> Publish immediately to students
        </label>
        <button className="btn btn-ghost" onClick={() => setShowCreateWizard(false)}>Cancel</button>
        <button className="btn btn-primary" onClick={handleSaveManualQuiz} disabled={!manualLectureId || !manualTitle.trim()}>
          <Save size={14} /> Save Quiz
        </button>
      </div>
    </div>
  );

  const renderAIMode = () => (
    <div>
      {/* Step Indicator */}
      <div className="wizard-steps">
        {['Select Materials', 'Configure', 'Preview & Save'].map((label, i) => (
          <div key={i} className={`wizard-step ${wizardStep > i + 1 ? 'completed' : ''} ${wizardStep === i + 1 ? 'active' : ''}`}>
            <div className="step-number">{wizardStep > i + 1 ? <Check size={12} /> : i + 1}</div>
            <span>{label}</span>
          </div>
        ))}
      </div>

      {/* Step 1: Select Materials */}
      {wizardStep === 1 && (
        <div>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
            Select the uploaded lecture materials to generate quiz questions automatically:
          </p>
          {availableMaterials.length === 0 ? (
            <div style={{ textAlign: 'center', padding: '2.5rem', color: 'var(--text-muted)', background: 'var(--bg-input)', borderRadius: '0.75rem', border: '1px dashed var(--border)' }}>
              <AlertCircle size={36} style={{ opacity: 0.5, marginBottom: '0.5rem', color: 'var(--accent)' }} />
              <p style={{ fontWeight: 500, color: 'var(--text-primary)' }}>No AI-ready materials found</p>
              <span style={{ fontSize: '0.8rem' }}>Upload PDFs or PPTs under course topics first.</span>
            </div>
          ) : (
            <div style={{ maxHeight: '300px', overflowY: 'auto', paddingRight: '0.25rem' }}>
              {availableMaterials.map(course => (
                <div key={course.course_id} style={{ marginBottom: '1.25rem' }}>
                  <h4 style={{ fontSize: '0.85rem', color: 'var(--accent)', marginBottom: '0.5rem', fontWeight: 700 }}>
                    {course.course_code} — {course.course_name}
                  </h4>
                  {course.topics.map(topic => (
                    <div key={topic.topic_id} style={{ marginLeft: '0.5rem', marginBottom: '0.75rem' }}>
                      <span style={{ fontSize: '0.8rem', fontWeight: 600, color: 'var(--text-secondary)', display: 'block', marginBottom: '0.25rem' }}>{topic.topic_title}</span>
                      {topic.materials.map(m => (
                        <label key={m.id} className={`material-checkbox ${selectedMaterialIds.includes(m.id) ? 'selected' : ''}`}>
                          <input type="checkbox" checked={selectedMaterialIds.includes(m.id)} onChange={() => toggleMaterial(m.id)} />
                          <span style={{ flex: 1 }}>
                            <span style={{ fontSize: '0.825rem', fontWeight: 500, display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                              {m.file_type === 'video' || m.file_name.startsWith('🎥') ? <Video size={14} style={{ color: 'var(--accent)', flexShrink: 0 }} /> :
                               m.file_type === 'assignment' || m.file_name.startsWith('📝') ? <FileText size={14} style={{ color: '#f59e0b', flexShrink: 0 }} /> :
                               <BookOpen size={14} style={{ color: 'var(--text-muted)', flexShrink: 0 }} />}
                              <span>{m.file_name}</span>
                            </span>
                            <span style={{ fontSize: '0.725rem', color: 'var(--text-muted)', display: 'block', marginTop: '2px', marginLeft: '1.25rem' }}>
                              {m.text_length > 0 ? `${Math.round(m.text_length / 100) / 10} KB processed text` : 'No text content'}
                            </span>
                          </span>
                        </label>
                      ))}
                    </div>
                  ))}
                </div>
              ))}
            </div>
          )}
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginTop: '1.25rem', paddingTop: '0.85rem', borderTop: '1px solid var(--border)' }}>
            <button className="btn btn-primary" onClick={() => setWizardStep(2)} disabled={selectedMaterialIds.length === 0}>
              Next Step <ChevronRight size={14} />
            </button>
          </div>
        </div>
      )}

      {/* Step 2: Configure */}
      {wizardStep === 2 && (
        <div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem', marginBottom: '1.25rem' }}>
            <div>
              <label className="form-label">Number of Questions</label>
              <input type="number" className="input" value={aiNumQuestions} onChange={e => setAiNumQuestions(parseInt(e.target.value) || 5)} min={1} max={30} placeholder="e.g. 5 (Range: 1 - 30)" />
            </div>
            <div>
              <label className="form-label">Difficulty Level</label>
              <select className="input" value={aiDifficulty} onChange={e => setAiDifficulty(e.target.value)}>
                <option value="easy">Easy — Basic Concepts & Definitions</option>
                <option value="medium">Medium — Application & Problem Solving</option>
                <option value="hard">Hard — Advanced Analysis & Synthesis</option>
              </select>
            </div>
          </div>

          <div style={{ marginBottom: '1.25rem' }}>
            <label className="form-label" style={{ fontWeight: 600, marginBottom: '0.5rem', display: 'block' }}>Question Types to Include</label>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '0.75rem', marginTop: '0.4rem' }}>
              {[
                { key: 'mcq', label: 'Multiple Choice (MCQ)', desc: 'Standard 4-option questions' },
                { key: 'true_false', label: 'True / False', desc: 'Binary format statement checks' }
              ].map(t => {
                const isChecked = aiQuizQuestionTypes.includes(t.key);
                return (
                  <div
                    key={t.key}
                    onClick={() => {
                      setAiQuizQuestionTypes(prev =>
                        prev.includes(t.key) ? (prev.length > 1 ? prev.filter(x => x !== t.key) : prev) : [...prev, t.key]
                      );
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

          <div style={{ padding: '1.25rem', background: 'var(--accent-subtle, rgba(13, 148, 136, 0.05))', borderRadius: '0.75rem', border: '1px solid var(--border)', marginBottom: '1.25rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.35rem' }}>
              <Sparkles size={18} style={{ color: 'var(--accent)' }} />
              <span style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-primary)' }}>AI Generation Overview</span>
            </div>
            <p style={{ margin: 0, fontSize: '0.825rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
              SmartStudy AI will analyze <strong>{selectedMaterialIds.length} material(s)</strong> and generate <strong>{aiNumQuestions} {aiDifficulty}-level</strong> multiple choice questions using deep course contextual intelligence.
            </p>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', paddingTop: '0.85rem', borderTop: '1px solid var(--border)' }}>
            <button className="btn btn-ghost" onClick={() => setWizardStep(1)}>Back</button>
            <button className="btn btn-primary" onClick={handleAIGenerate} disabled={aiGenerating}>
              {aiGenerating ? <><Loader2 size={14} className="spin" /> Generating Questions...</> : <><Sparkles size={14} /> Generate Questions</>}
            </button>
          </div>
        </div>
      )}

      {/* Step 3: Preview & Save */}
      {wizardStep === 3 && (
        <div>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h4 style={{ margin: 0, fontSize: '0.9rem', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <Sparkles size={16} style={{ color: 'var(--accent)' }} /> {aiGeneratedQuestions.length} AI Questions Generated
            </h4>
            <button className="btn btn-ghost" onClick={() => setWizardStep(2)} style={{ fontSize: '0.775rem', padding: '0.3rem 0.6rem' }}>
              ↻ Regenerate
            </button>
          </div>

          {/* Save config */}
          <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1.2fr 2fr 1fr 1fr 1.5fr', gap: '0.65rem', marginBottom: '1rem', padding: '0.85rem', background: 'var(--bg-input)', borderRadius: '0.75rem', border: '1px solid var(--border)' }}>
            <div>
              <label className="form-label">Section</label>
              <select className="input" onChange={e => { const sid = parseInt(e.target.value); if (sid) fetchLecturesForSection(sid); }} defaultValue="">
                <option value="" disabled>Select section...</option>
                {sections.map(s => <option key={s.id} value={s.id}>{s.course_name} - {s.section_label}</option>)}
              </select>
            </div>
            <div>
              <label className="form-label">Lecture Topic</label>
              <select className="input" value={aiSaveLectureId || ''} onChange={e => setAiSaveLectureId(parseInt(e.target.value))}>
                <option value="" disabled>Select lecture...</option>
                {lectures.map(l => <option key={l.id} value={l.id}>{l.title}</option>)}
              </select>
            </div>
            <div>
              <label className="form-label">Quiz Title</label>
              <input className="input" value={aiSaveTitle} onChange={e => setAiSaveTitle(e.target.value)} placeholder="e.g., AI Quiz: Machine Learning" />
            </div>
            <div>
              <label className="form-label">Timer/Q (s)</label>
              <input type="number" className="input" value={aiSavePerQuestionTimer} onChange={e => setAiSavePerQuestionTimer(parseInt(e.target.value) || 30)} placeholder="30" min={5} />
            </div>
            <div>
              <label className="form-label">Deadline</label>
              <input type="datetime-local" className="input" value={aiSaveDueDate} onChange={e => setAiSaveDueDate(e.target.value)} />
            </div>
          </div>

          {/* Editable questions list */}
          <div className="modal-scroll-area" style={{ maxHeight: '260px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '0.75rem', paddingRight: '0.25rem' }}>
            {aiGeneratedQuestions.map((q, idx) => (
              <div key={idx} className="question-card">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.35rem' }}>
                  <span className="question-number">Q{idx + 1}</span>
                  <button className="btn btn-ghost" onClick={() => handleAIQuestionDelete(idx)} style={{ padding: '0.2rem 0.4rem', color: 'var(--danger)' }} title="Delete Question"><Trash2 size={13} /></button>
                </div>
                <textarea className="input" value={q.question_text} onChange={e => handleAIQuestionEdit(idx, 'question_text', e.target.value)} rows={2} placeholder="Enter question prompt..." style={{ width: '100%', marginBottom: '0.5rem', fontSize: '0.85rem' }} />
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.4rem', marginBottom: '0.4rem' }}>
                  {(q.question_type === 'true_false' ? ['a', 'b'] : ['a', 'b', 'c', 'd']).map(opt => (
                    <input key={opt} className="input" value={q[`option_${opt}`] || ''} onChange={e => handleAIQuestionEdit(idx, `option_${opt}`, e.target.value)} placeholder={`Option ${opt.toUpperCase()} text...`} style={{ fontSize: '0.8rem' }} />
                  ))}
                </div>
                <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', background: 'var(--bg-input)', padding: '0.35rem 0.6rem', borderRadius: '0.5rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                    <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)' }}>Correct:</span>
                    <select className="input" value={q.correct_answer} onChange={e => handleAIQuestionEdit(idx, 'correct_answer', e.target.value)} style={{ width: '90px', padding: '0.2rem 0.4rem', fontSize: '0.75rem' }}>
                      {(q.question_type === 'true_false' ? ['A','B'] : ['A','B','C','D']).map(o => <option key={o} value={o}>Option {o}</option>)}
                    </select>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.35rem' }}>
                    <span style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--text-secondary)' }}>Difficulty:</span>
                    <select className="input" value={q.difficulty || 'medium'} onChange={e => handleAIQuestionEdit(idx, 'difficulty', e.target.value)} style={{ width: '100px', padding: '0.2rem 0.4rem', fontSize: '0.75rem' }}>
                      <option value="easy">Easy</option>
                      <option value="medium">Medium</option>
                      <option value="hard">Hard</option>
                    </select>
                  </div>
                </div>
              </div>
            ))}
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', marginTop: '1.25rem', paddingTop: '0.85rem', borderTop: '1px solid var(--border)', alignItems: 'center' }}>
            <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.825rem', cursor: 'pointer', color: 'var(--text-secondary)' }}>
              <input type="checkbox" checked={aiSaveIsPublished} onChange={e => setAiSaveIsPublished(e.target.checked)} style={{ accentColor: 'var(--accent)', width: '16px', height: '16px' }} /> Publish immediately
            </label>
            <button className="btn btn-primary" onClick={handleSaveAIQuiz} disabled={savingAIQuiz || !aiSaveLectureId || !aiSaveTitle.trim()}>
              {savingAIQuiz ? <><Loader2 size={14} className="spin" /> Saving...</> : <><Save size={14} /> Save Quiz</>}
            </button>
          </div>
        </div>
      )}
    </div>
  );

  // ═══════════════════════════════════════════════════════════
  //  RENDER: Main Layout
  // ═══════════════════════════════════════════════════════════
  if (loading) {
    return <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '3rem', color: 'var(--text-muted)' }}><Loader2 size={24} className="spin" /> Loading quizzes...</div>;
  }

  return (
    <div className="quizzes-page">
      <style>{`
        .quizzes-page { display: grid; grid-template-columns: 280px 1fr; gap: 1.25rem; height: calc(100vh - 140px); }
        .quiz-sidebar { background: var(--bg-secondary); border: 1px solid var(--border); border-radius: 0.75rem; padding: 1rem; overflow-y: auto; }
        .quiz-card { padding: 0.75rem; border: 1px solid var(--border); border-radius: 0.5rem; cursor: pointer; transition: all 0.2s; margin-bottom: 0.5rem; }
        .quiz-card:hover { border-color: var(--accent); background: var(--accent-glow); }
        .quiz-card.selected { border-color: var(--accent); background: var(--accent-glow); }
        .quiz-details-panel { background: var(--bg-secondary); border: 1px solid var(--border); border-radius: 0.75rem; padding: 1.25rem; overflow-y: auto; }
        .quiz-detail-tabs { display: flex; gap: 0.25rem; margin-bottom: 1.25rem; padding: 0.25rem; background: var(--bg-input); border-radius: 0.5rem; }
        .tab-btn { display: flex; align-items: center; gap: 0.35rem; padding: 0.5rem 1rem; border: none; background: none; color: var(--text-muted); cursor: pointer; border-radius: 0.35rem; font-size: 0.8rem; transition: all 0.2s; }
        .tab-btn.active { background: var(--accent); color: white; }
        .tab-btn:hover:not(.active) { background: var(--bg-secondary); }
        .question-card { background: var(--bg-card); border: 1.5px solid var(--border); border-radius: 0.75rem; padding: 0.85rem; transition: all 0.2s ease; }
        .question-card:focus-within, .question-card:hover { border-color: var(--accent); }
        .question-number { display: inline-flex; align-items: center; justify-content: center; width: 28px; height: 28px; border-radius: 50%; background: var(--accent); color: white; font-size: 0.75rem; font-weight: 700; }
        .stat-card { background: var(--bg-input); border-radius: 0.5rem; padding: 1rem; text-align: center; }
        .stat-value { font-size: 1.5rem; font-weight: 700; color: var(--accent); }
        .stat-label { font-size: 0.75rem; color: var(--text-muted); margin-top: 0.25rem; }
        .badge { padding: 0.15rem 0.4rem; border-radius: 0.25rem; font-size: 0.7rem; font-weight: 600; }
        .badge-success { background: rgba(16, 185, 129, 0.15); color: #10b981; }
        .badge-danger { background: rgba(239, 68, 68, 0.15); color: #ef4444; }
        .badge-warning { background: rgba(245, 158, 11, 0.15); color: #f59e0b; }
        .badge-info { background: var(--accent-glow); color: var(--accent); }
        .badge-primary { background: var(--accent-glow); color: var(--accent); }
        .badge-muted { background: rgba(107, 114, 128, 0.15); color: #6b7280; }

        /* Form Inputs & Controls */
        .input {
          width: 100%;
          padding: 0.55rem 0.85rem;
          font-size: 0.85rem;
          font-family: inherit;
          color: var(--text-primary);
          background: var(--bg-input);
          border: 1.5px solid var(--border);
          border-radius: 0.6rem;
          outline: none;
          transition: all 0.2s ease-in-out;
          box-sizing: border-box;
        }
        .input:hover {
          border-color: var(--accent);
        }
        .input:focus {
          border-color: var(--border-focus, var(--accent));
          background: var(--bg-card, #ffffff);
          box-shadow: 0 0 0 3.5px var(--accent-glow);
        }
        .input::placeholder {
          color: var(--text-muted);
          font-size: 0.82rem;
          opacity: 0.85;
        }
        select.input option {
          background: var(--bg-secondary);
          color: var(--text-primary);
        }
        textarea.input {
          resize: vertical;
          min-height: 65px;
          line-height: 1.45;
        }
        .form-label {
          display: flex;
          align-items: center;
          gap: 0.35rem;
          font-size: 0.725rem;
          font-weight: 700;
          color: var(--text-secondary);
          margin-bottom: 0.35rem;
          text-transform: uppercase;
          letter-spacing: 0.04em;
        }

        /* Modal / Wizard Dialog */
        .modal-overlay {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: rgba(15, 23, 42, 0.65);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 1000;
          backdrop-filter: blur(8px);
          animation: fadeIn 0.2s ease-out;
        }
        .modal-content {
          background: var(--bg-secondary);
          border: 1px solid var(--border);
          border-radius: 1.25rem;
          width: 760px;
          max-width: 92vw;
          max-height: 88vh;
          overflow-y: auto;
          box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.25);
          animation: modalSlideUp 0.25s cubic-bezier(0.16, 1, 0.3, 1);
        }
        @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
        @keyframes modalSlideUp { from { transform: translateY(16px) scale(0.98); opacity: 0; } to { transform: translateY(0) scale(1); opacity: 1; } }

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

        /* Custom Scrollbar inside modal */
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
        .wizard-step.active .step-number { border-color: var(--primary); background: var(--primary); color: white; }
        .wizard-step.completed .step-number { border-color: #10b981; background: #10b981; color: white; }

        .material-checkbox { display: flex; align-items: center; gap: 0.5rem; padding: 0.5rem 0.75rem; margin: 0.25rem 0 0.25rem 1rem; border: 1px solid var(--border); border-radius: 0.35rem; cursor: pointer; transition: all 0.2s; }
        .material-checkbox:hover { background: var(--bg-tertiary); }
        .material-checkbox.selected { border-color: var(--primary); background: rgba(99, 102, 241, 0.06); }
        .material-checkbox input { accent-color: var(--primary); }
        .form-label { display: block; font-size: 0.75rem; font-weight: 600; color: var(--text-muted); margin-bottom: 0.25rem; text-transform: uppercase; letter-spacing: 0.05em; }

        .spin { animation: spin 1s linear infinite; }
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }
      `}</style>

      {renderQuizList()}
      {renderQuizDetails()}
      {renderCreateWizard()}
    </div>
  );
}
