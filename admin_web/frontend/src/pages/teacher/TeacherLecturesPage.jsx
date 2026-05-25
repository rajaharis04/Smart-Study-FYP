import { useState, useEffect } from 'react';
import { teacherPortalApi } from '../../services/api';
import { Video, Plus, Trash2, Calendar, FileVideo, Edit, UploadCloud, Film } from 'lucide-react';
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
      formData.append('duration', editingLecture.duration);
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
          <button 
            className="btn btn-primary" 
            onClick={() => setShowUploadModal(true)}
          >
            <Plus size={18} />
            Upload Lecture Video
          </button>
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
                {/* Mock Video Thumbnail */}
                <div 
                  style={{ 
                    height: '160px', 
                    background: '#0d111a', 
                    display: 'flex', 
                    alignItems: 'center', 
                    justifyContent: 'center',
                    borderBottom: '1px solid var(--border)',
                    position: 'relative'
                  }}
                >
                  <FileVideo size={48} className="text-accent" style={{ opacity: 0.8 }} />
                  <div 
                    style={{ 
                      position: 'absolute', 
                      bottom: '8px', 
                      right: '8px', 
                      background: 'rgba(0,0,0,0.8)', 
                      padding: '2px 6px', 
                      borderRadius: '4px',
                      fontSize: '11px',
                      fontWeight: 'bold',
                      color: '#fff'
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
                          duration: Math.floor(lec.duration / 60),
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
                    value={editingLecture.duration}
                    onChange={(e) => setEditingLecture(prev => ({ ...prev, duration: parseInt(e.target.value) }))}
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

    </div>
  );
}
