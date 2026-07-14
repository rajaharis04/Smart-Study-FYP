import { useState, useEffect, useRef } from 'react';
import { teacherPortalApi } from '../../services/api';
import { Video, Plus, Trash2, Calendar, FileVideo, Edit, UploadCloud, Film, Sparkles, Cpu } from 'lucide-react';
import toast from 'react-hot-toast';

export default function TeacherLecturesPage() {
  const [sections, setSections] = useState([]);
  const [selectedSection, setSelectedSection] = useState(null);
  const [topics, setTopics] = useState([]);
  const [lectures, setLectures] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadingLectures, setLoadingLectures] = useState(false);

  // Video Upload Modal State
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [duration, setDuration] = useState(30);
  const [selectedTopicId, setSelectedTopicId] = useState('');
  const [videoFile, setVideoFile] = useState(null);
  const [isPublished, setIsPublished] = useState(true);
  const [uploading, setUploading] = useState(false);

  // Edit Mode State
  const [editingLecture, setEditingLecture] = useState(null);
  const [showEditModal, setShowEditModal] = useState(false);

  // AI Video Generator Modal State
  const [showAIModal, setShowAIModal] = useState(false);
  const [aiTitle, setAiTitle] = useState('');
  const [aiDescription, setAiDescription] = useState('');
  const [aiTopicId, setAiTopicId] = useState('');
  const [aiPdfFile, setAiPdfFile] = useState(null);
  const [aiTextInput, setAiTextInput] = useState('');
  const [aiAvatarFile, setAiAvatarFile] = useState(null);
  const [aiAvatarPreview, setAiAvatarPreview] = useState(null);
  const [isAiPublished, setIsAiPublished] = useState(true);

  // Phase management: 'input' | 'blueprint' | 'rendering'
  const [aiPhase, setAiPhase] = useState('input');
  const [generatingDraft, setGeneratingDraft] = useState(false);
  const [renderingVideo, setRenderingVideo] = useState(false);

  // Blueprint data
  const [blueprint, setBlueprint] = useState(null);
  const [activeSceneIndex, setActiveSceneIndex] = useState(0);

  // Rendering progress state
  const [renderJobId, setRenderJobId] = useState('');
  const [renderProgress, setRenderProgress] = useState(0);
  const [renderStep, setRenderStep] = useState('Queued...');

  const fetchSections = async () => {
    try {
      const res = await teacherPortalApi.sections();
      setSections(res.data);
      if (res.data.length > 0) {
        setSelectedSection(res.data[0]);
      }
    } catch (err) {
      toast.error('Failed to load classes.');
    } finally {
      setLoading(false);
    }
  };

  const fetchLecturesAndTopics = async (sect) => {
    setLoadingLectures(true);
    try {
      const lecturesRes = await teacherPortalApi.listLectures(sect.id);
      const topicsRes = await teacherPortalApi.listTopics(sect.course_id);
      
      setLectures(lecturesRes.data);
      setTopics(topicsRes.data);
    } catch (err) {
      toast.error('Failed to load lectures.');
    } finally {
      setLoadingLectures(false);
    }
  };

  useEffect(() => {
    fetchSections();
  }, []);

  useEffect(() => {
    if (selectedSection) {
      fetchLecturesAndTopics(selectedSection);
    }
  }, [selectedSection]);

  const handleVideoFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      if (!file.type.startsWith('video/')) {
        toast.error('Please upload an MP4 or other video file format.');
        return;
      }
      setVideoFile(file);
    }
  };

  const handleUploadSubmit = async (e) => {
    e.preventDefault();
    if (!title.trim() || !description.trim()) {
      toast.error('Title and description are required.');
      return;
    }
    if (!videoFile) {
      toast.error('Please select a video file.');
      return;
    }

    setUploading(true);
    const toastId = toast.loading('Uploading video file... This might take a moment.', { duration: 0 });

    try {
      const formData = new FormData();
      formData.append('title', title);
      formData.append('description', description);
      formData.append('duration', duration);
      formData.append('is_published', isPublished);
      formData.append('video', videoFile);
      if (selectedTopicId) {
        formData.append('topic_id', selectedTopicId);
      }

      await teacherPortalApi.uploadLectureVideo(selectedSection.id, formData);
      
      toast.success('Lecture video uploaded! Auto-generated MCQ quiz created.', { id: toastId });
      setShowUploadModal(false);
      
      // Reset state
      setTitle('');
      setDescription('');
      setDuration(30);
      setSelectedTopicId('');
      setVideoFile(null);
      setIsPublished(true);

      // Refresh list
      fetchLecturesAndTopics(selectedSection);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to upload video.', { id: toastId });
    } finally {
      setUploading(false);
    }
  };

  const handleEditSubmit = async (e) => {
    e.preventDefault();
    if (!editingLecture.title.trim() || !editingLecture.description.trim()) {
      toast.error('Title and description are required.');
      return;
    }

    try {
      const formData = new FormData();
      formData.append('title', editingLecture.title);
      formData.append('description', editingLecture.description);
      formData.append('duration', parseInt(editingLecture.duration) || 30);
      formData.append('is_published', editingLecture.is_published);
      if (editingLecture.topic_id) {
        formData.append('topic_id', editingLecture.topic_id);
      }

      await teacherPortalApi.updateLecture(editingLecture.id, formData);
      toast.success('Lecture details updated.');
      setShowEditModal(false);
      setEditingLecture(null);
      fetchLecturesAndTopics(selectedSection);
    } catch (err) {
      toast.error('Failed to update lecture.');
    }
  };

  const handleAiAvatarChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      if (!file.type.startsWith('image/')) {
        toast.error('Please upload an image file (PNG/JPG) for the avatar.');
        return;
      }
      setAiAvatarFile(file);
      const reader = new FileReader();
      reader.onload = (ev) => {
        setAiAvatarPreview(ev.target.result);
      };
      reader.readAsDataURL(file);
    }
  };

  const handleGenerateDraft = async (e) => {
    e.preventDefault();
    if (!aiTitle.trim() || !aiDescription.trim()) {
      toast.error('Title and description are required.');
      return;
    }
    if (!aiPdfFile && !aiTextInput.trim()) {
      toast.error('Please upload a PDF file or enter text.');
      return;
    }
    if (!aiTopicId) {
      toast.error('Please select a course topic.');
      return;
    }

    // Immediately wipe any old blueprint so the previous script never shows
    setBlueprint(null);
    setActiveSceneIndex(0);
    // Also tell the backend to clear its cached draft
    try { await teacherPortalApi.clearDraft(); } catch (_) { /* non-fatal */ }

    setGeneratingDraft(true);
    const toastId = toast.loading('Extracting content and generating lecture script draft...', { duration: 0 });

    try {
      const formData = new FormData();
      if (aiPdfFile) {
        formData.append('file', aiPdfFile);
      }
      if (aiTextInput.trim()) {
        formData.append('text_input', aiTextInput.trim());
      }

      const response = await teacherPortalApi.generateDraftBlueprint(formData);
      
      if (response.data && response.data.status === 'success') {
        setBlueprint(response.data.blueprint);
        setActiveSceneIndex(0);
        setAiPhase('blueprint');
        toast.success('Script draft generated successfully!', { id: toastId });
      } else {
        throw new Error(response.data?.detail || 'Failed to generate blueprint');
      }
    } catch (err) {
      console.error(err);
      toast.error(err.response?.data?.detail || err.message || 'Failed to generate script draft.', { id: toastId });
    } finally {
      setGeneratingDraft(false);
    }
  };

  const resetAIFields = () => {
    setAiTitle('');
    setAiDescription('');
    setAiTopicId('');
    setAiPdfFile(null);
    setAiTextInput('');
    setAiAvatarFile(null);
    setAiAvatarPreview(null);
    setBlueprint(null);
    setAiPhase('input');
    setRenderJobId('');
    setRenderProgress(0);
    setRenderStep('Queued...');
    const pdfInput = document.getElementById('ai-pdf-uploader');
    const avatarInput = document.getElementById('ai-avatar-uploader');
    if (pdfInput) pdfInput.value = '';
    if (avatarInput) avatarInput.value = '';
  };

  const handleSceneChange = (index, field, value) => {
    if (!blueprint) return;
    const updatedScenes = [...blueprint.scenes];
    updatedScenes[index] = {
      ...updatedScenes[index],
      [field]: value
    };
    setBlueprint({
      ...blueprint,
      scenes: updatedScenes
    });
  };

  const handleAssembleSubmit = async () => {
    if (!blueprint) return;
    setRenderingVideo(true);
    setRenderProgress(0);
    setRenderStep('Initializing render pipeline...');
    setAiPhase('rendering');

    const toastId = toast.loading('Submitting blueprint for video assembly...', { duration: 0 });

    try {
      const formData = new FormData();
      formData.append('blueprint_data', JSON.stringify(blueprint));
      if (aiAvatarFile) {
        formData.append('avatar_file', aiAvatarFile);
      }

      const response = await teacherPortalApi.assembleVideoBlueprint(formData);

      if (response.data && response.data.status === 'success') {
        setRenderJobId(response.data.job_id);
        toast.success('Video assembly started in the background.', { id: toastId });
      } else {
        throw new Error(response.data?.detail || 'Failed to start assembly.');
      }
    } catch (err) {
      console.error(err);
      toast.error(err.response?.data?.detail || err.message || 'Failed to assemble video.', { id: toastId });
      setAiPhase('blueprint');
      setRenderingVideo(false);
    }
  };

  // Guard ref so the completion block runs exactly once even if deps change
  const hasRegisteredRef = useRef(false);

  useEffect(() => {
    // Reset the guard whenever a new job starts
    hasRegisteredRef.current = false;

    let interval = null;

    if (renderJobId) {
      // Capture everything we need right now so the interval closure
      // doesn't re-run if other state updates happen mid-poll
      const jobId = renderJobId;
      const section = selectedSection;
      const bp = blueprint;
      const title = aiTitle;
      const desc = aiDescription;
      const topicId = aiTopicId;
      const published = isAiPublished;

      interval = setInterval(async () => {
        try {
          const response = await teacherPortalApi.getVideoRenderStatus(jobId);
          const data = response.data;

          if (data) {
            setRenderProgress(data.progress || 0);
            setRenderStep(data.current_step || data.message || 'Rendering...');

            if (data.status === 'completed' && !hasRegisteredRef.current) {
              // Mark as registered immediately to prevent any duplicate calls
              hasRegisteredRef.current = true;
              clearInterval(interval);

              // Calculate duration in seconds (from sum of scene durations)
              let totalDuration = 0;
              if (bp && bp.scenes) {
                totalDuration = bp.scenes.reduce((acc, s) => acc + (parseInt(s.duration) || 0), 0);
              }
              if (totalDuration === 0) totalDuration = 180;

              const videoFilename = data.video_url.split('/').pop();

              try {
                // Register the generated video as a new Lecture
                await teacherPortalApi.registerGeneratedLecture(section.id, {
                  title,
                  description: desc,
                  duration: totalDuration,
                  topic_id: topicId ? parseInt(topicId) : null,
                  is_published: published,
                  video_filename: videoFilename
                });
                // Single success toast
                toast.success('🎉 AI Lecture created and saved successfully!');
              } catch (regErr) {
                toast.error(regErr.response?.data?.detail || 'Lecture registration failed.');
              }

              resetAIFields();
              setShowAIModal(false);

              // Refresh lectures list
              fetchLecturesAndTopics(section);

            } else if (data.status === 'failed') {
              clearInterval(interval);
              toast.error(`Rendering failed: ${data.error || 'Unknown error'}`);
              setAiPhase('blueprint');
              setRenderJobId('');
            }
          }
        } catch (err) {
          console.warn('Error polling rendering status:', err);
        }
      }, 2000);
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  // Only restart interval when the job ID itself changes — not on every re-render
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [renderJobId]);

  const handleDeleteLecture = async (lectureId) => {
    if (!window.confirm('Are you sure you want to delete this lecture? The quiz, student records, and video file will be permanently removed.')) return;
    try {
      await teacherPortalApi.deleteLecture(lectureId);
      toast.success('Lecture deleted successfully.');
      fetchLecturesAndTopics(selectedSection);
    } catch (err) {
      toast.error('Failed to delete lecture.');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center" style={{ minHeight: '60vh' }}>
        <div className="loading" style={{ fontSize: '18px' }}>Loading Lectures Panel...</div>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      
      {/* Top Selector Panel */}
      <div className="card" style={{ padding: '16px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <span className="form-label" style={{ margin: 0, fontWeight: '600' }}>Active Class:</span>
            <select 
              className="form-control" 
              style={{ width: '280px', background: 'var(--bg-primary)' }}
              value={selectedSection ? selectedSection.id : ''}
              onChange={(e) => {
                const sec = sections.find(s => s.id === parseInt(e.target.value));
                setSelectedSection(sec);
              }}
            >
              {sections.map(s => (
                <option key={s.id} value={s.id}>
                  {s.course_code} - {s.course_name} (Sec {s.section_label})
                </option>
              ))}
            </select>
          </div>
          <div style={{ display: 'flex', gap: '10px' }}>
            <button 
              className="btn btn-secondary" 
              onClick={() => {
                resetAIFields();
                setAiPhase('input');
                setShowAIModal(true);
              }}
              style={{ display: 'flex', alignItems: 'center', gap: '8px', background: 'rgba(99, 102, 241, 0.1)', color: 'var(--accent)', border: '1px solid var(--accent)' }}
            >
              <Sparkles size={16} />
              AI Video Generator
            </button>
            <button 
              className="btn btn-primary" 
              onClick={() => setShowUploadModal(true)}
              style={{ display: 'flex', alignItems: 'center', gap: '6px' }}
            >
              <Plus size={18} />
              Upload Lecture Video
            </button>
          </div>
        </div>
      </div>

      {/* Lectures List Card */}
      <div className="card" style={{ padding: '24px' }}>
        <div className="card-header" style={{ padding: '0 0 16px', borderBottom: '1px solid var(--border)', marginBottom: '20px' }}>
          <h3 className="card-title flex items-center gap-2">
            <Film size={18} className="text-accent" />
            Uploaded Lectures ({lectures.length} video lectures)
          </h3>
        </div>

        {loadingLectures ? (
          <div className="flex justify-center padding-32">
            <div className="loading" style={{ fontSize: '14px', color: 'var(--text-secondary)' }}>Loading lectures list...</div>
          </div>
        ) : lectures.length === 0 ? (
          <div className="empty-state">
            <FileVideo size={36} className="text-muted" style={{ margin: '0 auto 12px' }} />
            <h3>No lecture videos uploaded yet</h3>
            <p>Upload a video lecture and the system will automatically parse and generate quizzes for students.</p>
          </div>
        ) : (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(320px, 1fr))', gap: '20px' }}>
            {lectures.map((lec) => (
              <div 
                key={lec.id} 
                className="card"
                style={{ 
                  display: 'flex', 
                  flexDirection: 'column', 
                  overflow: 'hidden', 
                  border: '1px solid var(--border)'
                }}
              >
                {/* Real HTML5 Video Player */}
                <div 
                  style={{ 
                    height: '180px', 
                    background: '#000', 
                    borderBottom: '1px solid var(--border)',
                    position: 'relative'
                  }}
                >
                  <video 
                    src={`http://localhost:8001${lec.video_url}`} 
                    controls 
                    preload="none"
                    style={{ width: '100%', height: '100%', objectFit: 'cover' }}
                  />
                  <div 
                    style={{ 
                      position: 'absolute', 
                      top: '8px', 
                      right: '8px', 
                      background: 'rgba(0,0,0,0.8)', 
                      padding: '2px 6px', 
                      borderRadius: '4px',
                      fontSize: '11px',
                      fontWeight: 'bold',
                      color: '#fff',
                      pointerEvents: 'none',
                      zIndex: 10
                    }}
                  >
                    {Math.floor(lec.duration / 60)}:{(lec.duration % 60).toString().padStart(2, '0')} mins
                  </div>
                </div>

                {/* Lecture Info */}
                <div style={{ padding: '16px', display: 'flex', flexDirection: 'column', gap: '10px', flex: 1 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: '8px' }}>
                    <h4 style={{ fontSize: '15px', fontWeight: '700', color: 'var(--text-primary)' }}>{lec.title}</h4>
                    {lec.is_published ? (
                      <span className="badge badge-success" style={{ fontSize: '9px' }}>Live</span>
                    ) : (
                      <span className="badge badge-warning" style={{ fontSize: '9px' }}>Draft</span>
                    )}
                  </div>

                  <p style={{ fontSize: '13px', color: 'var(--text-secondary)', lineHeight: '1.4', flex: 1 }}>
                    {lec.description.length > 100 ? lec.description.substring(0, 100) + '...' : lec.description}
                  </p>

                  <div style={{ fontSize: '12px', color: 'var(--text-muted)', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    {lec.topic_title && (
                      <span className="flex items-center gap-1">
                        📌 Topic: <strong className="text-accent-light">{lec.topic_title}</strong>
                      </span>
                    )}
                    <span className="flex items-center gap-1">
                      <Calendar size={12} /> Published: {lec.publish_date ? new Date(lec.publish_date).toLocaleDateString() : 'Unscheduled'}
                    </span>
                  </div>

                  {/* Actions */}
                  <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '12px', borderTop: '1px solid var(--border)', paddingTop: '12px' }}>
                    <button
                      className="btn btn-secondary btn-sm"
                      onClick={() => {
                        setEditingLecture({
                          id: lec.id,
                          title: lec.title,
                          description: lec.description,
                          duration: (lec.duration && !isNaN(lec.duration)) ? Math.floor(lec.duration / 60) : 30,
                          topic_id: lec.topic_id || '',
                          is_published: lec.is_published
                        });
                        setShowEditModal(true);
                      }}
                      style={{ padding: '6px' }}
                      title="Edit details"
                    >
                      <Edit size={14} />
                    </button>
                    <button
                      className="btn btn-danger btn-sm"
                      onClick={() => handleDeleteLecture(lec.id)}
                      style={{ padding: '6px' }}
                      title="Delete lecture"
                    >
                      <Trash2 size={14} />
                    </button>
                  </div>

                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Upload Modal */}
      {showUploadModal && (
        <div className="modal-overlay">
          <div className="modal">
            <div className="modal-header">
              <h3 className="modal-title">Upload Video Lecture</h3>
              <button className="modal-close" onClick={() => setShowUploadModal(false)}>×</button>
            </div>
            <form onSubmit={handleUploadSubmit}>
              <div className="modal-body">
                
                <div className="form-group">
                  <label className="form-label" htmlFor="lec-title">Lecture Title</label>
                  <input
                    id="lec-title"
                    type="text"
                    className="form-control"
                    placeholder="e.g. Lecture 3: Sorting Big-O Complexity"
                    required
                    value={title}
                    onChange={(e) => setTitle(e.target.value)}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label" htmlFor="lec-duration">Duration (Minutes)</label>
                  <input
                    id="lec-duration"
                    type="number"
                    min={1}
                    className="form-control"
                    placeholder="e.g. 30"
                    required
                    value={duration}
                    onChange={(e) => setDuration(parseInt(e.target.value))}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label" htmlFor="lec-desc">Description</label>
                  <textarea
                    id="lec-desc"
                    className="form-control"
                    placeholder="Provide a summary of the concepts covered in this lecture video..."
                    required
                    rows={3}
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    style={{ resize: 'vertical' }}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label" htmlFor="lec-topic">Map to Course Topic</label>
                  <select
                    id="lec-topic"
                    className="form-control"
                    value={selectedTopicId}
                    onChange={(e) => setSelectedTopicId(e.target.value)}
                  >
                    <option value="">-- Select Topic --</option>
                    {topics.map(t => (
                      <option key={t.id} value={t.id}>Topic #{t.sequence_number}: {t.title}</option>
                    ))}
                  </select>
                </div>

                {/* Drop/Upload Video Zone */}
                <div className="form-group">
                  <label className="form-label">Lecture Video File (MP4)</label>
                  <input 
                    type="file" 
                    accept="video/*" 
                    id="video-uploader" 
                    style={{ display: 'none' }}
                    onChange={handleVideoFileChange}
                  />
                  <label 
                    htmlFor="video-uploader" 
                    className="csv-drop-zone"
                    style={{ display: 'block', padding: '24px' }}
                  >
                    <UploadCloud size={32} style={{ margin: '0 auto 8px', color: 'var(--accent)' }} />
                    <h4>{videoFile ? videoFile.name : "Select MP4 video lecture"}</h4>
                    <p>{videoFile ? `${(videoFile.size / (1024 * 1024)).toFixed(1)} MB` : "Support files up to 200MB"}</p>
                  </label>
                </div>

                <div className="form-group" style={{ flexDirection: 'row', gap: '8px', alignItems: 'center' }}>
                  <input 
                    type="checkbox" 
                    id="publish-check"
                    checked={isPublished}
                    onChange={(e) => setIsPublished(e.target.checked)}
                    style={{ width: '16px', height: '16px', cursor: 'pointer' }}
                  />
                  <label htmlFor="publish-check" className="form-label" style={{ margin: 0, cursor: 'pointer' }}>
                    Publish immediately (makes video live for enrolled students)
                  </label>
                </div>

              </div>
              
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowUploadModal(false)} disabled={uploading}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={uploading}>
                  {uploading ? 'Uploading Video...' : 'Upload Video'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Edit Details Modal */}
      {showEditModal && editingLecture && (
        <div className="modal-overlay">
          <div className="modal">
            <div className="modal-header">
              <h3 className="modal-title">Edit Lecture Details</h3>
              <button className="modal-close" onClick={() => setShowEditModal(false)}>×</button>
            </div>
            <form onSubmit={handleEditSubmit}>
              <div className="modal-body">
                
                <div className="form-group">
                  <label className="form-label">Lecture Title</label>
                  <input
                    type="text"
                    className="form-control"
                    required
                    value={editingLecture.title}
                    onChange={(e) => setEditingLecture(prev => ({ ...prev, title: e.target.value }))}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Duration (Minutes)</label>
                  <input
                    type="number"
                    min={1}
                    className="form-control"
                    required
                    value={isNaN(editingLecture.duration) ? '' : editingLecture.duration}
                    onChange={(e) => setEditingLecture(prev => ({ ...prev, duration: e.target.value === '' ? '' : parseInt(e.target.value) }))}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Description</label>
                  <textarea
                    className="form-control"
                    required
                    rows={3}
                    value={editingLecture.description}
                    onChange={(e) => setEditingLecture(prev => ({ ...prev, description: e.target.value }))}
                    style={{ resize: 'vertical' }}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Course Topic</label>
                  <select
                    className="form-control"
                    value={editingLecture.topic_id}
                    onChange={(e) => setEditingLecture(prev => ({ ...prev, topic_id: e.target.value }))}
                  >
                    <option value="">-- Unmapped --</option>
                    {topics.map(t => (
                      <option key={t.id} value={t.id}>Topic #{t.sequence_number}: {t.title}</option>
                    ))}
                  </select>
                </div>

                <div className="form-group" style={{ flexDirection: 'row', gap: '8px', alignItems: 'center' }}>
                  <input 
                    type="checkbox" 
                    id="edit-publish-check"
                    checked={editingLecture.is_published}
                    onChange={(e) => setEditingLecture(prev => ({ ...prev, is_published: e.target.checked }))}
                    style={{ width: '16px', height: '16px', cursor: 'pointer' }}
                  />
                  <label htmlFor="edit-publish-check" className="form-label" style={{ margin: 0, cursor: 'pointer' }}>
                    Publish lecture (visible to students)
                  </label>
                </div>

              </div>
              
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowEditModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  Save Changes
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* AI Video Generator Modal - Phase 1: Input Form */}
      {showAIModal && aiPhase === 'input' && (
        <div className="modal-overlay">
          <div className="modal" style={{ 
            maxWidth: '600px', 
            width: '95%',
            height: 'auto',
            maxHeight: '85vh',
            margin: 'auto',
            borderRadius: '12px',
            display: 'flex',
            flexDirection: 'column'
          }}>
            <div className="modal-header">
              <h3 className="modal-title flex items-center gap-2">
                <Sparkles size={20} className="text-accent" />
                AI Lecture Video Generator
              </h3>
              <button 
                className="modal-close" 
                onClick={() => {
                  resetAIFields();
                  setShowAIModal(false);
                }}
              >
                ×
              </button>
            </div>

            <form onSubmit={handleGenerateDraft}>
              <div className="modal-body" style={{ maxHeight: '70vh', overflowY: 'auto' }}>
                
                <div className="form-group">
                  <label className="form-label" htmlFor="ai-title">Lecture Title</label>
                  <input
                    id="ai-title"
                    type="text"
                    className="form-control"
                    placeholder="e.g. AI-Generated Lecture: Intro to Arrays"
                    required
                    value={aiTitle}
                    onChange={(e) => setAiTitle(e.target.value)}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label" htmlFor="ai-desc">Description</label>
                  <textarea
                    id="ai-desc"
                    className="form-control"
                    placeholder="Provide a short description of the lecture topic..."
                    required
                    rows={2}
                    value={aiDescription}
                    onChange={(e) => setAiDescription(e.target.value)}
                  />
                </div>

                <div className="form-group">
                  <label className="form-label" htmlFor="ai-topic">Map to Course Topic</label>
                  <select
                    id="ai-topic"
                    className="form-control"
                    required
                    value={aiTopicId}
                    onChange={(e) => setAiTopicId(e.target.value)}
                  >
                    <option value="">-- Select Topic --</option>
                    {topics.map(t => (
                      <option key={t.id} value={t.id}>Topic #{t.sequence_number}: {t.title}</option>
                    ))}
                  </select>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px', margin: '16px 0' }}>
                  
                  {/* Source Document File */}
                  <div className="form-group">
                    <label className="form-label">Upload Lecture PDF / Book</label>
                    <input 
                      type="file" 
                      accept=".pdf" 
                      id="ai-pdf-uploader" 
                      style={{ display: 'none' }}
                      onChange={(e) => setAiPdfFile(e.target.files[0])}
                    />
                    <label 
                      htmlFor="ai-pdf-uploader" 
                      className="csv-drop-zone"
                      style={{ display: 'block', padding: '16px', minHeight: '120px', cursor: 'pointer' }}
                    >
                      <UploadCloud size={24} style={{ margin: '0 auto 6px', color: 'var(--accent)' }} />
                      <span style={{ fontSize: '13px', fontWeight: '600' }}>
                        {aiPdfFile ? aiPdfFile.name : "Select PDF Document"}
                      </span>
                      <p style={{ fontSize: '11px', margin: '4px 0 0' }}>
                        {aiPdfFile ? `${(aiPdfFile.size / (1024 * 1024)).toFixed(1)} MB` : "Slides, text or textbooks"}
                      </p>
                    </label>
                  </div>

                  {/* Talking Head Avatar Photo */}
                  <div className="form-group">
                    <label className="form-label">Teacher Avatar Photo (Optional)</label>
                    <input 
                      type="file" 
                      accept="image/*" 
                      id="ai-avatar-uploader" 
                      style={{ display: 'none' }}
                      onChange={handleAiAvatarChange}
                    />
                    <label 
                      htmlFor="ai-avatar-uploader" 
                      className="csv-drop-zone"
                      style={{ display: 'block', padding: '16px', minHeight: '120px', cursor: 'pointer', position: 'relative' }}
                    >
                      {aiAvatarPreview ? (
                        <div style={{ width: '60px', height: '60px', borderRadius: '50%', overflow: 'hidden', margin: '0 auto 6px', border: '2px solid var(--accent)' }}>
                          <img src={aiAvatarPreview} alt="Avatar Preview" style={{ width: '100%', height: '100%', objectFit: 'cover' }} />
                        </div>
                      ) : (
                        <UploadCloud size={24} style={{ margin: '0 auto 6px', color: 'var(--accent)' }} />
                      )}
                      <span style={{ fontSize: '13px', fontWeight: '600' }}>
                        {aiAvatarFile ? aiAvatarFile.name : "Select Avatar Photo"}
                      </span>
                      <p style={{ fontSize: '11px', margin: '4px 0 0' }}>
                        {aiAvatarFile ? "Image Loaded" : "For Talking LipSync"}
                      </p>
                    </label>
                    {aiAvatarFile && (
                      <div style={{ display: 'flex', gap: '8px', justifyContent: 'center', marginTop: '10px' }}>
                        <button
                          type="button"
                          className="btn btn-secondary btn-sm"
                          style={{ padding: '6px 12px', fontSize: '12px' }}
                          onClick={() => {
                            document.getElementById('ai-avatar-uploader').click();
                          }}
                        >
                          Change Photo
                        </button>
                        <button
                          type="button"
                          className="btn btn-danger btn-sm"
                          style={{ padding: '6px 12px', fontSize: '12px', background: '#EF4444', borderColor: '#EF4444', color: 'white' }}
                          onClick={() => {
                            setAiAvatarFile(null);
                            setAiAvatarPreview(null);
                            const avatarInput = document.getElementById('ai-avatar-uploader');
                            if (avatarInput) avatarInput.value = '';
                          }}
                        >
                          Remove
                        </button>
                      </div>
                    )}
                  </div>

                </div>

                {/* Or raw text fallback */}
                {!aiPdfFile && (
                  <div className="form-group">
                    <label className="form-label" htmlFor="ai-text-input">Or Paste Raw Lecture Text</label>
                    <textarea
                      id="ai-text-input"
                      className="form-control"
                      placeholder="Paste lecture reference material or raw text here if you don't have a PDF..."
                      rows={4}
                      value={aiTextInput}
                      onChange={(e) => setAiTextInput(e.target.value)}
                    />
                  </div>
                )}

                <div className="form-group" style={{ flexDirection: 'row', gap: '8px', alignItems: 'center', marginTop: '8px' }}>
                  <input 
                    type="checkbox" 
                    id="ai-publish-check"
                    checked={isAiPublished}
                    onChange={(e) => setIsAiPublished(e.target.checked)}
                    style={{ width: '16px', height: '16px', cursor: 'pointer' }}
                  />
                  <label htmlFor="ai-publish-check" className="form-label" style={{ margin: 0, cursor: 'pointer' }}>
                    Publish lecture immediately once generated
                  </label>
                </div>

              </div>
              
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => { resetAIFields(); setShowAIModal(false); }} disabled={generatingDraft}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" style={{ display: 'flex', alignItems: 'center', gap: '8px' }} disabled={generatingDraft}>
                  <Cpu size={16} />
                  {generatingDraft ? 'Generating Script Draft...' : 'Generate Script Draft'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* AI Video Generator - Phase 2: Immersive Full-Screen Blueprint Editor */}
      {showAIModal && aiPhase === 'blueprint' && blueprint && (
        <div style={{
          position: 'fixed',
          inset: 0,
          background: 'var(--bg-primary)',
          zIndex: 1500,
          display: 'flex',
          flexDirection: 'column',
          animation: 'fadeIn 0.2s ease',
          color: 'var(--text-primary)'
        }}>
          {/* Top Sticky Bar */}
          <div style={{
            height: '70px',
            padding: '0 24px',
            background: 'var(--bg-secondary)',
            borderBottom: '1px solid var(--border)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexShrink: 0,
            boxShadow: 'var(--shadow-sm)'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
              <div style={{
                width: '40px', height: '40px',
                borderRadius: '8px',
                background: 'linear-gradient(135deg, var(--accent), var(--accent-dark))',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                color: 'white', fontWeight: 'bold', fontSize: '18px'
              }}>
                AI
              </div>
              <div>
                <h3 style={{ margin: 0, fontSize: '16px', fontWeight: '700' }}>AI Lecture Blueprint & Script Editor</h3>
                <span style={{ fontSize: '12px', color: 'var(--text-muted)' }}>Editing: {aiTitle || 'Lecture Blueprint'}</span>
              </div>
            </div>
            <div style={{ display: 'flex', gap: '12px' }}>
              <button 
                type="button" 
                className="btn btn-secondary" 
                onClick={() => setAiPhase('input')}
                disabled={renderingVideo}
              >
                Back to Inputs
              </button>
              <button 
                type="button" 
                className="btn btn-secondary" 
                onClick={() => { resetAIFields(); setShowAIModal(false); }}
                disabled={renderingVideo}
              >
                Save Draft & Exit
              </button>
              <button 
                type="button" 
                className="btn btn-primary" 
                style={{ background: '#10B981', borderColor: '#10B981', color: 'white', display: 'flex', alignItems: 'center', gap: '8px' }} 
                onClick={handleAssembleSubmit}
                disabled={renderingVideo}
              >
                <Video size={16} />
                Assemble & Render Video
              </button>
            </div>
          </div>

          {/* Main Working Area */}
          <div style={{ display: 'flex', flex: 1, overflow: 'hidden' }}>
            {/* Left Sidebar: Slide Navigation & Outline */}
            <div style={{
              width: '320px',
              background: 'var(--bg-secondary)',
              borderRight: '1px solid var(--border)',
              padding: '24px 16px',
              display: 'flex',
              flexDirection: 'column',
              gap: '16px',
              overflowY: 'auto',
              flexShrink: 0
            }}>
              <h4 style={{ fontSize: '12px', fontWeight: '800', textTransform: 'uppercase', color: 'var(--text-secondary)', letterSpacing: '0.05em' }}>
                Lecture Outline
              </h4>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {blueprint.scenes && blueprint.scenes.map((scene, idx) => (
                  <a
                    key={scene.id || idx}
                    href={`#scene-editor-card-${idx}`}
                    onClick={(e) => {
                      e.preventDefault();
                      const element = document.getElementById(`scene-editor-card-${idx}`);
                      if (element) {
                        element.scrollIntoView({ behavior: 'smooth', block: 'center' });
                      }
                      setActiveSceneIndex(idx);
                    }}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '12px',
                      padding: '12px 16px',
                      borderRadius: '10px',
                      border: activeSceneIndex === idx ? '2px solid var(--accent)' : '1px solid var(--border)',
                      background: activeSceneIndex === idx ? 'var(--accent-glow)' : 'var(--bg-primary)',
                      color: 'var(--text-primary)',
                      textDecoration: 'none',
                      transition: 'all 0.2s',
                      cursor: 'pointer'
                    }}
                  >
                    <div style={{
                      width: '28px', height: '28px',
                      borderRadius: '50%',
                      background: activeSceneIndex === idx ? 'var(--accent)' : 'var(--border)',
                      color: activeSceneIndex === idx ? 'white' : 'var(--text-secondary)',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontSize: '13px', fontWeight: '700',
                      flexShrink: 0
                    }}>
                      {idx + 1}
                    </div>
                    <div style={{ flex: 1, overflow: 'hidden' }}>
                      <span style={{ fontSize: '10px', fontWeight: 'bold', textTransform: 'uppercase', color: activeSceneIndex === idx ? 'var(--accent)' : 'var(--text-muted)', display: 'block' }}>
                        {scene.scene_type || scene.type || 'Concept'}
                      </span>
                      <h5 style={{ margin: 0, fontSize: '13px', fontWeight: '600', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        {scene.heading_left || 'Untitled Slide'}
                      </h5>
                    </div>
                  </a>
                ))}
              </div>

              {/* Total Duration Widget */}
              <div style={{
                marginTop: 'auto',
                padding: '16px',
                borderRadius: '12px',
                background: 'var(--bg-primary)',
                border: '1px solid var(--border)',
                display: 'flex',
                alignItems: 'center',
                gap: '12px'
              }}>
                <Film className="text-accent" size={24} />
                <div>
                  <span style={{ fontSize: '10px', color: 'var(--text-muted)', fontWeight: 'bold', display: 'block' }}>ESTIMATED LENGTH</span>
                  <h4 style={{ margin: 0, fontSize: '15px', fontWeight: '800' }}>
                    {blueprint.scenes ? blueprint.scenes.reduce((acc, s) => acc + (parseInt(s.duration) || 0), 0) : 0} seconds
                  </h4>
                </div>
              </div>
            </div>

            {/* Right: Scrollable Full Script Editor */}
            <div 
              style={{
                flex: 1,
                padding: '40px 60px',
                overflowY: 'auto',
                background: 'var(--bg-primary)',
                scrollBehavior: 'smooth'
              }}
            >
              <div style={{ maxWidth: '850px', margin: '0 auto', display: 'flex', flexDirection: 'column', gap: '32px' }}>
                <div style={{ marginBottom: '8px' }}>
                  <h2 style={{ fontSize: '24px', fontWeight: '800', margin: 0 }}>Review and Edit Script Draft</h2>
                  <p style={{ color: 'var(--text-secondary)', fontSize: '14px', marginTop: '4px' }}>
                    This script was auto-generated by the Pedagogical AI Engine. You can modify slide content, bullet points, and the spoken voiceover script below.
                  </p>
                </div>

                {blueprint.scenes && blueprint.scenes.map((scene, idx) => (
                  <div
                    key={scene.id || idx}
                    id={`scene-editor-card-${idx}`}
                    style={{
                      background: 'var(--bg-secondary)',
                      borderRadius: '16px',
                      border: activeSceneIndex === idx ? '2px solid var(--accent)' : '1px solid var(--border)',
                      boxShadow: activeSceneIndex === idx ? 'var(--shadow-lg)' : 'var(--shadow-sm)',
                      padding: '32px',
                      display: 'flex',
                      flexDirection: 'column',
                      gap: '24px',
                      transition: 'all 0.2s',
                      position: 'relative'
                    }}
                    onClick={() => setActiveSceneIndex(idx)}
                  >
                    {/* Scene Tag */}
                    <div style={{
                      position: 'absolute',
                      top: '20px',
                      right: '24px',
                      background: 'var(--accent-glow)',
                      color: 'var(--accent)',
                      padding: '4px 12px',
                      borderRadius: '20px',
                      fontSize: '11px',
                      fontWeight: '700',
                      textTransform: 'uppercase',
                      letterSpacing: '0.05em'
                    }}>
                      Slide #{idx + 1} &bull; {scene.scene_type || scene.type || 'Concept'}
                    </div>

                    <h3 style={{ fontSize: '18px', fontWeight: '800', borderBottom: '1px solid var(--border)', paddingBottom: '12px', marginBottom: '4px' }}>
                      Slide #{idx + 1}: {scene.heading_left || 'Introductory Setup'}
                    </h3>

                    {/* Inputs Row 1: Left & Right Titles */}
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
                      <div className="form-group">
                        <label className="form-label" style={{ fontWeight: '700', fontSize: '13px', color: 'var(--text-primary)' }}>Heading Left (Slide Title)</label>
                        <input
                          type="text"
                          className="form-control"
                          value={scene.heading_left || ''}
                          onChange={(e) => handleSceneChange(idx, 'heading_left', e.target.value)}
                        />
                      </div>
                      <div className="form-group">
                        <label className="form-label" style={{ fontWeight: '700', fontSize: '13px', color: 'var(--text-primary)' }}>Heading Right (Sub-Concept)</label>
                        <input
                          type="text"
                          className="form-control"
                          value={scene.heading_right || ''}
                          onChange={(e) => handleSceneChange(idx, 'heading_right', e.target.value)}
                        />
                      </div>
                    </div>

                    {/* Inputs Row 2: Gold Word & Scene Duration */}
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
                      <div className="form-group">
                        <label className="form-label" style={{ fontWeight: '700', fontSize: '13px', color: 'var(--text-primary)' }}>
                          Gold Technical Word
                          <span style={{ fontSize: '11.5px', color: 'var(--text-muted)', marginLeft: '6px' }}>(styled with gold glow in video)</span>
                        </label>
                        <input
                          type="text"
                          className="form-control"
                          value={scene.gold_word || ''}
                          onChange={(e) => handleSceneChange(idx, 'gold_word', e.target.value)}
                          placeholder="e.g. recursion"
                        />
                      </div>
                      <div className="form-group">
                        <label className="form-label" style={{ fontWeight: '700', fontSize: '13px', color: 'var(--text-primary)' }}>Scene Duration (Seconds)</label>
                        <input
                          type="number"
                          className="form-control"
                          value={scene.duration || 15}
                          onChange={(e) => handleSceneChange(idx, 'duration', parseInt(e.target.value) || 0)}
                        />
                      </div>
                    </div>

                    {/* Spoken Voiceover TTS Script */}
                    <div className="form-group">
                      <label className="form-label" style={{ fontWeight: '700', fontSize: '13px', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <Film size={14} className="text-accent" />
                        AI Voiceover Script (What the teacher speaks)
                      </label>
                      <p style={{ fontSize: '11.5px', color: 'var(--text-muted)', marginTop: '-4px', marginBottom: '8px' }}>
                        Type the exact words the avatar should read aloud. Make sure it naturally flows and explains the concepts shown on screen.
                      </p>
                      <textarea
                        className="form-control"
                        rows={5}
                        style={{ lineHeight: '1.6', fontSize: '14px', padding: '12px' }}
                        value={scene.narration || ''}
                        onChange={(e) => handleSceneChange(idx, 'narration', e.target.value)}
                      />
                    </div>

                    {/* Bullet Points Area */}
                    <div className="form-group">
                      <label className="form-label" style={{ fontWeight: '700', fontSize: '13px', color: 'var(--text-primary)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                        <Plus size={14} className="text-accent" />
                        Slide Bullet Points (one per line)
                      </label>
                      <textarea
                        className="form-control"
                        rows={4}
                        style={{ lineHeight: '1.6', fontSize: '14px', padding: '12px' }}
                        value={scene.bullets ? scene.bullets.map(b => typeof b === 'string' ? b : b.text).join('\n') : ''}
                        onChange={(e) => {
                          const lines = e.target.value.split('\n');
                          const updatedBullets = lines.map((line, bIdx) => {
                            const existing = scene.bullets && scene.bullets[bIdx];
                            if (existing && typeof existing === 'object') {
                              return { ...existing, text: line };
                            }
                            return { text: line, zoom_word: '', trigger_word: '', entrance: 'slide_left', num: (bIdx + 1).toString().padStart(2, '0') };
                          });
                          handleSceneChange(idx, 'bullets', updatedBullets);
                        }}
                        placeholder="Bullet point 1&#10;Bullet point 2"
                      />
                    </div>

                    {/* Key takeaway & Analogy */}
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px' }}>
                      <div className="form-group">
                        <label className="form-label" style={{ fontWeight: '700', fontSize: '13px', color: 'var(--text-primary)' }}>Concept Analogy</label>
                        <input
                          type="text"
                          className="form-control"
                          value={scene.analogy || ''}
                          onChange={(e) => handleSceneChange(idx, 'analogy', e.target.value)}
                          placeholder="e.g. Think of it like a stack of plates..."
                        />
                      </div>
                      <div className="form-group">
                        <label className="form-label" style={{ fontWeight: '700', fontSize: '13px', color: 'var(--text-primary)' }}>Key Takeaway</label>
                        <input
                          type="text"
                          className="form-control"
                          value={scene.takeaway || ''}
                          onChange={(e) => handleSceneChange(idx, 'takeaway', e.target.value)}
                          placeholder="e.g. Last In, First Out (LIFO)"
                        />
                      </div>
                    </div>
                  </div>
                ))}

                {/* Render Button at Bottom */}
                <div style={{ display: 'flex', justifyContent: 'center', marginTop: '20px', marginBottom: '80px' }}>
                  <button
                    type="button"
                    className="btn btn-primary"
                    style={{ background: '#10B981', borderColor: '#10B981', color: 'white', display: 'flex', alignItems: 'center', gap: '10px', padding: '16px 36px', fontSize: '16px', borderRadius: '12px' }}
                    onClick={handleAssembleSubmit}
                    disabled={renderingVideo}
                  >
                    <Video size={20} />
                    {renderingVideo ? 'Rendering Pipeline Active...' : 'Submit Blueprint to Render Pipeline'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* AI Video Generator - Phase 3: Full-Screen Rendering Progress */}
      {showAIModal && aiPhase === 'rendering' && (
        <div style={{
          position: 'fixed',
          inset: 0,
          background: 'var(--bg-primary)',
          zIndex: 1500,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          animation: 'fadeIn 0.2s ease',
          padding: '40px',
          color: 'var(--text-primary)'
        }}>
          <div style={{
            background: 'var(--bg-secondary)',
            border: '1px solid var(--border)',
            borderRadius: '20px',
            boxShadow: 'var(--shadow-xl)',
            padding: '48px 32px',
            maxWidth: '520px',
            width: '100%',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: '24px',
            textAlign: 'center'
          }}>
            <div style={{ position: 'relative', width: '140px', height: '140px' }}>
              <svg width="140" height="140" viewBox="0 0 120 120">
                <circle cx="60" cy="60" r="50" fill="none" stroke="var(--border)" strokeWidth="6" />
                <circle 
                  cx="60" 
                  cy="60" 
                  r="50" 
                  fill="none" 
                  stroke="var(--accent)" 
                  strokeWidth="8" 
                  strokeDasharray="314"
                  strokeDashoffset={314 - (314 * renderProgress) / 100}
                  strokeLinecap="round"
                  style={{ transition: 'stroke-dashoffset 0.4s ease', transform: 'rotate(-90deg)', transformOrigin: '50% 50%' }}
                />
              </svg>
              <div style={{ position: 'absolute', top: '50%', left: '50%', transform: 'translate(-50%, -50%)', fontSize: '24px', fontWeight: '800', color: 'var(--text-primary)' }}>
                {renderProgress}%
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <h3 style={{ fontWeight: '800', fontSize: '20px', margin: 0 }}>Assembling Lecture Video</h3>
              <p style={{ color: 'var(--text-muted)', fontSize: '13px', lineHeight: '1.5' }}>
                We are compiling the GSAP slide timelines, generating teacher voiceovers via TTS, and stitching the final video together.
              </p>
            </div>

            <div style={{
              width: '100%',
              padding: '12px 16px',
              background: 'var(--bg-primary)',
              borderRadius: '10px',
              border: '1px solid var(--border)',
              fontSize: '14px',
              fontWeight: '600'
            }}>
              Current Step: <strong style={{ color: 'var(--accent)' }}>{renderStep}</strong>
            </div>

            <div style={{ width: '100%', borderTop: '1px solid var(--border)', paddingTop: '20px', display: 'flex', justifyContent: 'center' }}>
              <button 
                type="button" 
                className="btn btn-secondary" 
                onClick={() => setShowAIModal(false)}
                style={{ width: '100%' }}
              >
                Run in Background
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
