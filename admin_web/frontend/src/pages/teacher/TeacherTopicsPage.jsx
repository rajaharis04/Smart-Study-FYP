import { useState, useEffect } from 'react';
import { teacherPortalApi } from '../../services/api';
import { BookOpen, Plus, Trash2, Upload, FileText, ChevronDown, ChevronRight, AlertCircle, RefreshCw, Eye } from 'lucide-react';
import toast from 'react-hot-toast';

export default function TeacherTopicsPage() {
  const [sections, setSections] = useState([]);
  const [selectedSection, setSelectedSection] = useState(null);
  const [topics, setTopics] = useState([]);
  const [loading, setLoading] = useState(true);
  const [loadingTopics, setLoadingTopics] = useState(false);
  const [previewMaterial, setPreviewMaterial] = useState(null);

  // Topic creation state
  const [showAddModal, setShowAddModal] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newSeq, setNewSeq] = useState(1);
  const [newBlooms, setNewBlooms] = useState('Remember');
  const [newObjectives, setNewObjectives] = useState(['']);

  // Expanded topics state
  const [expandedTopics, setExpandedTopics] = useState({});

  // File uploading states per topic
  const [uploadingTopicId, setUploadingTopicId] = useState(null);

  const fetchSections = async () => {
    try {
      const res = await teacherPortalApi.sections();
      setSections(res.data);
      if (res.data.length > 0) {
        setSelectedSection(res.data[0]);
      }
    } catch (err) {
      toast.error('Failed to load courses.');
    } finally {
      setLoading(false);
    }
  };

  const fetchTopics = async (courseId) => {
    setLoadingTopics(true);
    try {
      const res = await teacherPortalApi.listTopics(courseId);
      setTopics(res.data);
      
      // Auto-expand all topics initially
      const expanded = {};
      res.data.forEach(t => { expanded[t.id] = true; });
      setExpandedTopics(expanded);
    } catch (err) {
      toast.error('Failed to load topics.');
    } finally {
      setLoadingTopics(false);
    }
  };

  useEffect(() => {
    fetchSections();
  }, []);

  useEffect(() => {
    if (selectedSection) {
      fetchTopics(selectedSection.course_id);
    }
  }, [selectedSection]);

  // Poll for material uploads if any are still in "processing" or "extraction_complete"
  useEffect(() => {
    if (!selectedSection || topics.length === 0) return;
    
    const hasProcessing = topics.some(t => 
      t.materials?.some(m => m.upload_status === 'processing' || m.upload_status === 'extraction_complete')
    );
    
    if (!hasProcessing) return;
    
    const interval = setInterval(() => {
      teacherPortalApi.listTopics(selectedSection.course_id).then(res => {
        setTopics(res.data);
      });
    }, 3000);
    
    return () => clearInterval(interval);
  }, [topics, selectedSection]);

  const toggleExpand = (id) => {
    setExpandedTopics(prev => ({ ...prev, [id]: !prev[id] }));
  };

  const handleAddObjectiveField = () => {
    setNewObjectives(prev => [...prev, '']);
  };

  const handleRemoveObjectiveField = (index) => {
    setNewObjectives(prev => prev.filter((_, i) => i !== index));
  };

  const handleObjectiveChange = (index, value) => {
    setNewObjectives(prev => {
      const copy = [...prev];
      copy[index] = value;
      return copy;
    });
  };

  const handleCreateTopicSubmit = async (e) => {
    e.preventDefault();
    if (!newTitle.trim()) {
      toast.error('Topic title is required.');
      return;
    }
    
    const filteredObjectives = newObjectives.filter(obj => obj.trim() !== '');
    if (filteredObjectives.length === 0) {
      toast.error('Please define at least one learning objective.');
      return;
    }

    try {
      const data = {
        title: newTitle,
        sequence_number: newSeq,
        blooms_level: newBlooms,
        objectives: filteredObjectives.map(obj => ({ description: obj }))
      };
      
      await teacherPortalApi.createTopic(selectedSection.course_id, data);
      toast.success('Topic defined successfully!');
      setShowAddModal(false);
      
      // Reset form
      setNewTitle('');
      setNewSeq(topics.length + 1);
      setNewBlooms('Remember');
      setNewObjectives(['']);
      
      // Refresh list
      fetchTopics(selectedSection.course_id);
    } catch (err) {
      toast.error('Failed to create topic.');
    }
  };

  const handleDeleteTopic = async (topicId) => {
    if (!window.confirm('Are you sure you want to delete this topic? All objectives and materials will be removed.')) return;
    try {
      await teacherPortalApi.deleteTopic(topicId);
      toast.success('Topic deleted successfully.');
      fetchTopics(selectedSection.course_id);
    } catch (err) {
      toast.error('Failed to delete topic.');
    }
  };

  const handleFileUpload = async (topicId, file) => {
    if (!file) return;
    
    const formData = new FormData();
    formData.append('file', file);
    
    setUploadingTopicId(topicId);
    toast.loading('Uploading file...', { id: 'upload' });
    
    try {
      await teacherPortalApi.uploadMaterial(topicId, formData);
      toast.success('File uploaded! Back-end chunking & RAG extraction processing started.', { id: 'upload' });
      fetchTopics(selectedSection.course_id);
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to upload document.', { id: 'upload' });
    } finally {
      setUploadingTopicId(null);
    }
  };

  const handleDeleteMaterial = async (matId) => {
    if (!window.confirm('Delete this material?')) return;
    try {
      await teacherPortalApi.deleteMaterial(matId);
      toast.success('Material deleted.');
      fetchTopics(selectedSection.course_id);
    } catch (err) {
      toast.error('Failed to delete material.');
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center" style={{ minHeight: '60vh' }}>
        <div className="loading" style={{ fontSize: '18px' }}>Loading Courses & Topics...</div>
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      
      {/* Top Selector & Action */}
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
            onClick={() => {
              setNewSeq(topics.length + 1);
              setShowAddModal(true);
            }}
          >
            <Plus size={18} />
            Define New Topic
          </button>
        </div>
      </div>

      {/* Main tree list */}
      <div className="card" style={{ padding: '24px' }}>
        <div className="card-header" style={{ padding: '0 0 16px', borderBottom: '1px solid var(--border)', marginBottom: '20px' }}>
          <h3 className="card-title flex items-center gap-2">
            <BookOpen size={18} className="text-accent-light" />
            Semester Course Mapping ({topics.length} topics defined)
          </h3>
          {loadingTopics && <RefreshCw size={16} className="loading text-accent" />}
        </div>
        
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {topics.length === 0 ? (
            <div className="empty-state">
              <AlertCircle size={32} className="text-muted" style={{ margin: '0 auto 12px' }} />
              <h3>No topics defined yet</h3>
              <p>Topics defined here will automatically structure the generated quizzes, masteries, and video assignments.</p>
            </div>
          ) : (
            topics.map((t) => {
              const isExpanded = !!expandedTopics[t.id];
              return (
                <div 
                  key={t.id} 
                  className="card" 
                  style={{ 
                    border: '1px solid var(--border)',
                    background: 'rgba(255,255,255,0.01)'
                  }}
                >
                  {/* Topic Title Bar */}
                  <div 
                    style={{ 
                      padding: '16px 20px', 
                      display: 'flex', 
                      alignItems: 'center', 
                      justifyContent: 'space-between', 
                      cursor: 'pointer',
                      background: 'rgba(255,255,255,0.02)',
                      borderBottom: isExpanded ? '1px solid var(--border)' : 'none'
                    }}
                    onClick={() => toggleExpand(t.id)}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                      {isExpanded ? <ChevronDown size={18} /> : <ChevronRight size={18} />}
                      <span className="badge badge-accent" style={{ background: 'var(--bg-primary)' }}>Topic #{t.sequence_number}</span>
                      <h4 style={{ fontSize: '16px', fontWeight: '600' }}>{t.title}</h4>
                      <span className={`badge ${
                        t.blooms_level === 'Remember' ? 'badge-info' :
                        t.blooms_level === 'Understand' ? 'badge-success' :
                        t.blooms_level === 'Apply' ? 'badge-accent' :
                        t.blooms_level === 'Analyze' ? 'badge-warning' : 'badge-danger'
                      }`}>
                        Bloom's: {t.blooms_level}
                      </span>
                    </div>

                    <button 
                      type="button"
                      className="btn-icon"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDeleteTopic(t.id);
                      }}
                      style={{ border: 'none', background: 'transparent', color: 'var(--danger)', height: '24px', width: '24px' }}
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>

                  {/* Expanded Content */}
                  {isExpanded && (
                    <div className="card-body" style={{ padding: '20px', display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '32px' }}>
                      
                      {/* Left: Objectives */}
                      <div>
                        <h5 style={{ fontSize: '13px', fontWeight: '700', textTransform: 'uppercase', color: 'var(--text-secondary)', marginBottom: '12px' }}>
                          🎯 Learning Objectives
                        </h5>
                        <ul style={{ display: 'flex', flexDirection: 'column', gap: '10px', listStyle: 'none' }}>
                          {t.learning_objectives.map((obj, index) => (
                            <li 
                              key={obj.id} 
                              style={{ 
                                display: 'flex', 
                                gap: '8px', 
                                fontSize: '14px', 
                                color: 'var(--text-primary)',
                                background: 'rgba(255,255,255,0.02)',
                                padding: '8px 12px',
                                borderRadius: 'var(--radius-sm)'
                              }}
                            >
                              <span style={{ color: 'var(--accent)', fontWeight: 'bold' }}>{index + 1}.</span>
                              <span>{obj.description}</span>
                            </li>
                          ))}
                        </ul>
                      </div>

                      {/* Right: Uploaded Materials */}
                      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                        <h5 style={{ fontSize: '13px', fontWeight: '700', textTransform: 'uppercase', color: 'var(--text-secondary)' }}>
                          📁 Topic Material Files (PDF/PPT)
                        </h5>
                        
                        {/* Material Files List */}
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                          {t.materials?.length === 0 ? (
                            <p style={{ fontSize: '12px', color: 'var(--text-muted)' }}>No slides or notes uploaded yet.</p>
                          ) : (
                            t.materials?.map(mat => (
                              <div 
                                key={mat.id}
                                className="card"
                                style={{ 
                                  padding: '10px 14px', 
                                  display: 'flex', 
                                  alignItems: 'center', 
                                  justifyContent: 'space-between',
                                  background: 'var(--bg-primary)',
                                  fontSize: '13px'
                                }}
                              >
                                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flex: 1, marginRight: '16px' }}>
                                  <FileText size={16} className="text-accent" />
                                  <div style={{ display: 'flex', flexDirection: 'column', gap: '2px', flex: 1 }}>
                                    <span style={{ color: 'var(--text-primary)', wordBreak: 'break-all' }}>{mat.file_name}</span>
                                    {mat.upload_status !== 'ai_ready' ? (
                                      <div style={{ width: '100%', marginTop: '4px' }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px', color: 'var(--text-muted)' }}>
                                          <span>{mat.upload_status === 'processing' ? 'Extracting text...' : 'AI Processing...'}</span>
                                          <span>{mat.progress}%</span>
                                        </div>
                                        <div style={{ width: '100%', height: '4px', background: 'var(--border)', borderRadius: '2px', overflow: 'hidden', marginTop: '2px' }}>
                                          <div style={{ width: `${mat.progress}%`, height: '100%', background: 'var(--accent)', transition: 'width 0.5s ease' }} />
                                        </div>
                                      </div>
                                    ) : (
                                      <span className="badge badge-success" style={{ alignSelf: 'flex-start', fontSize: '9px', padding: '1px 6px' }}>AI-Ready</span>
                                    )}
                                  </div>
                                </div>
                                <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                                  {mat.upload_status === 'ai_ready' && (
                                    <button
                                      type="button"
                                      onClick={() => setPreviewMaterial(mat)}
                                      style={{ border: 'none', background: 'transparent', color: 'var(--success)', cursor: 'pointer', display: 'flex', alignItems: 'center' }}
                                      title="Preview Extracted Text"
                                    >
                                      <Eye size={15} />
                                    </button>
                                  )}
                                  <button
                                    type="button"
                                    onClick={() => handleDeleteMaterial(mat.id)}
                                    style={{ border: 'none', background: 'transparent', color: 'var(--danger)', cursor: 'pointer', display: 'flex', alignItems: 'center' }}
                                  >
                                    <Trash2 size={14} />
                                  </button>
                                </div>
                              </div>
                            ))
                          )}
                        </div>

                        {/* File Upload Trigger */}
                        <div style={{ position: 'relative' }}>
                          <input 
                            type="file" 
                            accept=".pdf,.ppt,.pptx"
                            id={`file-upload-${t.id}`}
                            style={{ display: 'none' }}
                            onChange={(e) => handleFileUpload(t.id, e.target.files[0])}
                            disabled={uploadingTopicId !== null}
                          />
                          <label 
                            htmlFor={`file-upload-${t.id}`}
                            className="btn btn-secondary w-full"
                            style={{ justifyContent: 'center', cursor: uploadingTopicId ? 'not-allowed' : 'pointer' }}
                          >
                            <Upload size={14} />
                            Upload Slides/Notes (PDF/PPT)
                          </label>
                        </div>

                      </div>

                    </div>
                  )}
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Define Topic Modal */}
      {showAddModal && (
        <div className="modal-overlay">
          <div className="modal" style={{ maxWidth: '600px' }}>
            <div className="modal-header">
              <h3 className="modal-title">Define Course Topic</h3>
              <button className="modal-close" onClick={() => setShowAddModal(false)}>×</button>
            </div>
            
            <form onSubmit={handleCreateTopicSubmit}>
              <div className="modal-body">
                <div className="form-group">
                  <label className="form-label" htmlFor="title">Topic Title</label>
                  <input
                    id="title"
                    type="text"
                    className="form-control"
                    placeholder="e.g. Tree Traversal Algorithms"
                    required
                    value={newTitle}
                    onChange={(e) => setNewTitle(e.target.value)}
                  />
                </div>

                <div className="form-grid">
                  <div className="form-group">
                    <label className="form-label" htmlFor="seq">Sequence Number</label>
                    <input
                      id="seq"
                      type="number"
                      min={1}
                      className="form-control"
                      required
                      value={newSeq}
                      onChange={(e) => setNewSeq(parseInt(e.target.value))}
                    />
                  </div>

                  <div className="form-group">
                    <label className="form-label" htmlFor="blooms">Bloom's Taxonomy Level</label>
                    <select
                      id="blooms"
                      className="form-control"
                      value={newBlooms}
                      onChange={(e) => setNewBlooms(e.target.value)}
                    >
                      <option value="Remember">Remember</option>
                      <option value="Understand">Understand</option>
                      <option value="Apply">Apply</option>
                      <option value="Analyze">Analyze</option>
                      <option value="Evaluate">Evaluate</option>
                      <option value="Create">Create</option>
                    </select>
                  </div>
                </div>

                {/* Objectives Builder */}
                <div className="form-group" style={{ borderTop: '1px solid var(--border)', paddingTop: '16px', marginTop: '8px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
                    <label className="form-label" style={{ margin: 0 }}>Learning Objectives</label>
                    <button 
                      type="button" 
                      className="btn btn-secondary btn-sm"
                      onClick={handleAddObjectiveField}
                    >
                      + Add Objective
                    </button>
                  </div>
                  
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                    {newObjectives.map((obj, index) => (
                      <div key={index} style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                        <span style={{ fontSize: '13px', fontWeight: '600', color: 'var(--text-muted)', width: '20px' }}>{index + 1}.</span>
                        <input
                          type="text"
                          className="form-control"
                          placeholder="e.g. Student will be able to perform in-order traversal of a BST"
                          required
                          value={obj}
                          onChange={(e) => handleObjectiveChange(index, e.target.value)}
                          style={{ flex: 1 }}
                        />
                        {newObjectives.length > 1 && (
                          <button
                            type="button"
                            onClick={() => handleRemoveObjectiveField(index)}
                            style={{ border: 'none', background: 'transparent', color: 'var(--danger)', cursor: 'pointer' }}
                          >
                            <Trash2 size={16} />
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                </div>

              </div>
              
              <div className="modal-footer">
                <button type="button" className="btn btn-secondary" onClick={() => setShowAddModal(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  Define Topic
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Materials Text Preview Modal */}
      {previewMaterial && (
        <div className="modal-overlay">
          <div className="modal" style={{ maxWidth: '700px' }}>
            <div className="modal-header">
              <h3 className="modal-title">Extracted Material Preview</h3>
              <button className="modal-close" onClick={() => setPreviewMaterial(null)}>×</button>
            </div>
            <div className="modal-body">
              <div className="form-group">
                <label className="form-label">File Name</label>
                <div style={{ fontSize: '13px', color: 'var(--text-secondary)', marginBottom: '12px' }}>
                  {previewMaterial.file_name}
                </div>
              </div>
              <div className="form-group">
                <label className="form-label">Simulated Extracted Text</label>
                <textarea
                  className="form-control"
                  style={{
                    height: '320px',
                    fontFamily: 'monospace',
                    fontSize: '12px',
                    lineHeight: '1.5',
                    background: 'var(--bg-primary)',
                    color: 'var(--text-primary)',
                    borderColor: 'var(--border)',
                    resize: 'none',
                    padding: '12px'
                  }}
                  readOnly
                  value={previewMaterial.extracted_text || 'No text extracted yet.'}
                />
              </div>
            </div>
            <div className="modal-footer">
              <button type="button" className="btn btn-secondary" onClick={() => setPreviewMaterial(null)}>
                Close Preview
              </button>
            </div>
          </div>
        </div>
      )}

    </div>
  );
}
