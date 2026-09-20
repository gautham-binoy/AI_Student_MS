import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Users,
  UserPlus,
  Search,
  Camera,
  CheckCircle2,
  XCircle,
  Trash2,
  Eye,
  AlertCircle,
  Filter
} from 'lucide-react';
import { api } from '../services/api';
import { Student } from '../types';
import { Modal } from '../components/Modal';

export const StudentsPage: React.FC = () => {
  const navigate = useNavigate();
  const [students, setStudents] = useState<Student[]>([]);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [deptFilter, setDeptFilter] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(true);

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [formData, setFormData] = useState({
    student_code: '',
    name: '',
    email: '',
    department: 'Computer Science & Engineering',
    year: '3rd Year',
    section: 'Section A'
  });
  const [selectedPhoto, setSelectedPhoto] = useState<File | null>(null);
  const [photoPreview, setPhotoPreview] = useState<string | null>(null);
  const [formSubmitting, setFormSubmitting] = useState<boolean>(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [formSuccess, setFormSuccess] = useState<string | null>(null);

  // Face Registration Modal for existing student
  const [faceModalStudent, setFaceModalStudent] = useState<Student | null>(null);
  const [faceFile, setFaceFile] = useState<File | null>(null);
  const [faceUploading, setFaceUploading] = useState<boolean>(false);
  const [faceError, setFaceError] = useState<string | null>(null);

  const fetchStudents = async () => {
    try {
      setLoading(true);
      const data = await api.getStudents();
      setStudents(data);
    } catch (err) {
      console.error('Failed to load students:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStudents();
  }, []);

  const handlePhotoChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedPhoto(file);
      setPhotoPreview(URL.createObjectURL(file));
      setFormError(null);
    }
  };

  const handleCreateStudent = async (e: React.FormEvent) => {
    e.preventDefault();
    setFormError(null);
    setFormSuccess(null);

    if (!formData.student_code.trim() || !formData.name.trim()) {
      setFormError('Please provide both Student ID and Name.');
      return;
    }

    try {
      setFormSubmitting(true);
      // 1. Create student
      const newStudent = await api.createStudent(formData);

      // 2. Upload face if provided
      if (selectedPhoto) {
        try {
          await api.uploadStudentFace(newStudent.id, selectedPhoto);
          setFormSuccess('Student created and face successfully registered!');
        } catch (faceErr: any) {
          setFormError(`Student created, but face registration failed: ${faceErr.response?.data?.detail || 'No face found'}`);
        }
      } else {
        setFormSuccess('Student created successfully (without face photo).');
      }

      await fetchStudents();
      setTimeout(() => {
        setIsModalOpen(false);
        setFormSuccess(null);
        setSelectedPhoto(null);
        setPhotoPreview(null);
        setFormData({
          student_code: '',
          name: '',
          email: '',
          department: 'Computer Science & Engineering',
          year: '3rd Year',
          section: 'Section A'
        });
      }, 1500);
    } catch (err: any) {
      setFormError(err.response?.data?.detail || 'Failed to create student.');
    } finally {
      setFormSubmitting(false);
    }
  };

  const handleUploadFaceForExisting = async () => {
    if (!faceModalStudent || !faceFile) return;
    setFaceUploading(true);
    setFaceError(null);
    try {
      await api.uploadStudentFace(faceModalStudent.id, faceFile);
      setFaceModalStudent(null);
      setFaceFile(null);
      fetchStudents();
    } catch (err: any) {
      setFaceError(err.response?.data?.detail || 'Face registration failed. Please provide a clear single-face portrait.');
    } finally {
      setFaceUploading(false);
    }
  };

  const handleDelete = async (id: number, name: string) => {
    if (confirm(`Are you sure you want to delete ${name}? All attendance logs and biometric embeddings will be removed.`)) {
      try {
        await api.deleteStudent(id);
        fetchStudents();
      } catch (err) {
        alert('Failed to delete student.');
      }
    }
  };

  const filteredStudents = students.filter((s) => {
    const matchesSearch = s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          s.student_code.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesDept = deptFilter ? s.department === deptFilter : true;
    return matchesSearch && matchesDept;
  });

  const departments = Array.from(new Set(students.map((s) => s.department).filter(Boolean)));

  return (
    <div>
      {/* Top Toolbar */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: 16,
        marginBottom: 24
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, flex: 1, maxWidth: 500 }}>
          {/* Search Input */}
          <div style={{
            position: 'relative',
            flex: 1,
            display: 'flex',
            alignItems: 'center'
          }}>
            <Search size={16} color="var(--text-muted)" style={{ position: 'absolute', left: 12 }} />
            <input
              type="text"
              className="form-input"
              placeholder="Search by student name or ID..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{ width: '100%', paddingLeft: 38 }}
            />
          </div>

          {/* Department Filter */}
          <select
            className="form-select"
            value={deptFilter}
            onChange={(e) => setDeptFilter(e.target.value)}
          >
            <option value="">All Departments</option>
            {departments.map((d) => (
              <option key={d as string} value={d as string}>{d}</option>
            ))}
          </select>
        </div>

        <button
          className="btn btn-primary"
          onClick={() => setIsModalOpen(true)}
          style={{ gap: 8 }}
        >
          <UserPlus size={16} />
          <span>Add Student</span>
        </button>
      </div>

      {/* Students Table */}
      <div className="glass-panel" style={{ padding: 0 }}>
        <div className="table-container" style={{ border: 'none' }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Student ID</th>
                <th>Full Name</th>
                <th>Department</th>
                <th>Year & Sec</th>
                <th>Biometric Status</th>
                <th style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredStudents.map((s) => (
                <tr key={s.id}>
                  <td className="font-mono" style={{ fontWeight: 600, color: 'var(--accent-cyan)' }}>
                    {s.student_code}
                  </td>
                  <td style={{ fontWeight: 600 }}>{s.name}</td>
                  <td>{s.department || '—'}</td>
                  <td>{s.year ? `${s.year}, ${s.section || ''}` : '—'}</td>
                  <td>
                    {s.has_face ? (
                      <span style={{
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: 6,
                        color: 'var(--accent-emerald)',
                        fontSize: '0.78rem',
                        fontWeight: 600
                      }}>
                        <CheckCircle2 size={15} />
                        <span>Registered</span>
                      </span>
                    ) : (
                      <button
                        className="btn btn-secondary btn-sm"
                        onClick={() => setFaceModalStudent(s)}
                        style={{ fontSize: '0.75rem', gap: 4, padding: '4px 8px' }}
                      >
                        <Camera size={13} />
                        <span>Register Face</span>
                      </button>
                    )}
                  </td>
                  <td style={{ textAlign: 'right' }}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: 8 }}>
                      <button
                        className="btn btn-secondary btn-sm"
                        onClick={() => navigate(`/students/${s.id}`)}
                        title="View Profile"
                      >
                        <Eye size={14} />
                        <span>Profile</span>
                      </button>
                      <button
                        className="btn btn-danger btn-sm"
                        onClick={() => handleDelete(s.id, s.name)}
                        title="Delete Student"
                      >
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {filteredStudents.length === 0 && !loading && (
                <tr>
                  <td colSpan={6} style={{ textAlign: 'center', padding: 36, color: 'var(--text-muted)' }}>
                    No students match your criteria.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Add Student Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="Register New Student"
        footer={
          <>
            <button className="btn btn-secondary" onClick={() => setIsModalOpen(false)}>
              Cancel
            </button>
            <button
              className="btn btn-primary"
              onClick={handleCreateStudent}
              disabled={formSubmitting}
            >
              {formSubmitting ? 'Registering...' : 'Register Student'}
            </button>
          </>
        }
      >
        {formError && (
          <div style={{
            background: 'rgba(244, 63, 94, 0.15)',
            border: '1px solid rgba(244, 63, 94, 0.3)',
            borderRadius: 'var(--radius-sm)',
            padding: '10px 14px',
            color: '#fb7185',
            fontSize: '0.84rem',
            marginBottom: 16,
            display: 'flex',
            alignItems: 'center',
            gap: 8
          }}>
            <AlertCircle size={16} />
            <span>{formError}</span>
          </div>
        )}

        {formSuccess && (
          <div style={{
            background: 'rgba(16, 185, 129, 0.15)',
            border: '1px solid rgba(16, 185, 129, 0.3)',
            borderRadius: 'var(--radius-sm)',
            padding: '10px 14px',
            color: '#34d399',
            fontSize: '0.84rem',
            marginBottom: 16,
            display: 'flex',
            alignItems: 'center',
            gap: 8
          }}>
            <CheckCircle2 size={16} />
            <span>{formSuccess}</span>
          </div>
        )}

        <form onSubmit={handleCreateStudent}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
            <div className="input-group">
              <label className="input-label">Student ID *</label>
              <input
                type="text"
                className="form-input font-mono"
                placeholder="e.g. STU-2026-009"
                value={formData.student_code}
                onChange={(e) => setFormData({ ...formData, student_code: e.target.value })}
                required
              />
            </div>

            <div className="input-group">
              <label className="input-label">Full Name *</label>
              <input
                type="text"
                className="form-input"
                placeholder="e.g. Maya Krishnan"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                required
              />
            </div>
          </div>

          <div className="input-group">
            <label className="input-label">Email Address</label>
            <input
              type="email"
              className="form-input"
              placeholder="maya@example.edu"
              value={formData.email}
              onChange={(e) => setFormData({ ...formData, email: e.target.value })}
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 14 }}>
            <div className="input-group">
              <label className="input-label">Department</label>
              <input
                type="text"
                className="form-input"
                placeholder="Computer Science"
                value={formData.department}
                onChange={(e) => setFormData({ ...formData, department: e.target.value })}
              />
            </div>

            <div className="input-group">
              <label className="input-label">Year & Section</label>
              <input
                type="text"
                className="form-input"
                placeholder="3rd Year, Sec A"
                value={formData.year}
                onChange={(e) => setFormData({ ...formData, year: e.target.value })}
              />
            </div>
          </div>

          {/* Photo Upload Section */}
          <div className="input-group" style={{ marginTop: 8 }}>
            <label className="input-label">Reference Face Portrait (Optional)</label>
            <div style={{
              border: '2px dashed var(--border-subtle)',
              borderRadius: 'var(--radius-md)',
              padding: 16,
              textAlign: 'center',
              background: 'var(--bg-surface-elevated)'
            }}>
              {photoPreview ? (
                <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 8 }}>
                  <img
                    src={photoPreview}
                    alt="Preview"
                    style={{ width: 100, height: 100, borderRadius: '50%', objectFit: 'cover', border: '2px solid var(--accent-primary)' }}
                  />
                  <label className="btn btn-secondary btn-sm" style={{ cursor: 'pointer' }}>
                    <input type="file" accept="image/*" onChange={handlePhotoChange} style={{ display: 'none' }} />
                    <span>Change Photo</span>
                  </label>
                </div>
              ) : (
                <div>
                  <Camera size={32} style={{ opacity: 0.3, marginBottom: 8 }} />
                  <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                    Upload a clear frontal portrait for biometric recognition
                  </p>
                  <label className="btn btn-secondary btn-sm" style={{ marginTop: 8, cursor: 'pointer', display: 'inline-flex' }}>
                    <input type="file" accept="image/*" onChange={handlePhotoChange} style={{ display: 'none' }} />
                    <span>Select Photo</span>
                  </label>
                </div>
              )}
            </div>
            <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: 4 }}>
              System strictly verifies that exactly 1 face is present before registering embedding.
            </span>
          </div>
        </form>
      </Modal>

      {/* Separate Face Upload Modal for Existing Student */}
      {faceModalStudent && (
        <Modal
          isOpen={true}
          onClose={() => setFaceModalStudent(null)}
          title={`Register Face for ${faceModalStudent.name}`}
          footer={
            <>
              <button className="btn btn-secondary" onClick={() => setFaceModalStudent(null)}>
                Cancel
              </button>
              <button
                className="btn btn-primary"
                onClick={handleUploadFaceForExisting}
                disabled={faceUploading || !faceFile}
              >
                {faceUploading ? 'Analyzing Face...' : 'Upload & Register'}
              </button>
            </>
          }
        >
          {faceError && (
            <div style={{
              background: 'rgba(244, 63, 94, 0.15)',
              border: '1px solid rgba(244, 63, 94, 0.3)',
              borderRadius: 'var(--radius-sm)',
              padding: '10px 14px',
              color: '#fb7185',
              fontSize: '0.84rem',
              marginBottom: 16
            }}>
              {faceError}
            </div>
          )}

          <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', marginBottom: 16 }}>
            Upload a clear, well-lit portrait of <strong>{faceModalStudent.name}</strong> ({faceModalStudent.student_code}).
          </p>

          <input
            type="file"
            accept="image/*"
            className="form-input"
            onChange={(e) => setFaceFile(e.target.files?.[0] || null)}
          />
        </Modal>
      )}
    </div>
  );
};
