import React, { useEffect, useRef, useState } from 'react';
import {
  Camera,
  Video,
  Play,
  Square,
  Upload,
  Activity,
  UserCheck,
  Users,
  Radio,
  RefreshCw,
  Eye,
  Sparkles,
  AlertCircle
} from 'lucide-react';
import { api } from '../services/api';
import { Session, LiveFrameUpdate, LiveDetection } from '../types';
import { Badge } from '../components/Badge';

export const LiveClassroomPage: React.FC = () => {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [selectedSessionId, setSelectedSessionId] = useState<number | null>(null);
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [sourceMode, setSourceMode] = useState<'webcam' | 'image' | 'video'>('webcam');

  // Live WebSocket state
  const [wsConnected, setWsConnected] = useState<boolean>(false);
  const [fps, setFps] = useState<number>(0);
  const [activeTracksCount, setActiveTracksCount] = useState<number>(0);
  const [presentCount, setPresentCount] = useState<number>(0);
  const [totalStudents, setTotalStudents] = useState<number>(0);
  const [avgEngagement, setAvgEngagement] = useState<number>(0);
  const [liveDetections, setLiveDetections] = useState<LiveDetection[]>([]);
  const [statusMessage, setStatusMessage] = useState<string>('Select session and start live feed');

  // References
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const streamIntervalRef = useRef<any>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);

  // Single inference result image (for image upload)
  const [inferredImageSrc, setInferredImageSrc] = useState<string | null>(null);
  const [uploadLoading, setUploadLoading] = useState<boolean>(false);

  // Load sessions
  const loadSessions = async () => {
    try {
      const data = await api.getSessions();
      setSessions(data);
      const active = data.find((s) => s.status === 'active');
      if (active) {
        setSelectedSessionId(active.id);
      } else if (data.length > 0 && !selectedSessionId) {
        setSelectedSessionId(data[0].id);
      }
    } catch (err) {
      console.error('Failed to load sessions:', err);
    }
  };

  useEffect(() => {
    loadSessions();
    return () => {
      stopCameraStream();
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  // WebSocket Connection
  const connectWebSocket = () => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/api/live`;

    console.log('Connecting to WebSocket:', wsUrl);
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log('WebSocket connected');
      setWsConnected(true);
      setStatusMessage('Live stream connected. AI tracking active.');
    };

    ws.onmessage = (event) => {
      try {
        const data: LiveFrameUpdate = JSON.parse(event.data);
        if (data.type === 'frame_update') {
          setFps(data.fps);
          setActiveTracksCount(data.counts.active_tracks);
          setPresentCount(data.counts.present);
          setTotalStudents(data.counts.total_students);
          setAvgEngagement(data.avg_engagement);
          setLiveDetections(data.detections);

          // Draw AI detections on HUD canvas
          drawDetectionsOnCanvas(data.detections, data.fps, data.avg_engagement);
        }
      } catch (err) {
        console.error('WS parse error:', err);
      }
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
      setWsConnected(false);
    };

    ws.onerror = (err) => {
      console.error('WebSocket error:', err);
      setWsConnected(false);
    };

    wsRef.current = ws;
  };

  // Draw bounding boxes, names, and HUD directly on the front-end overlay canvas
  const drawDetectionsOnCanvas = (
    detections: LiveDetection[],
    currentFps: number,
    engagement: number
  ) => {
    const canvas = canvasRef.current;
    const video = videoRef.current;
    if (!canvas || !video) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Match canvas dimensions to video
    if (canvas.width !== video.videoWidth && video.videoWidth > 0) {
      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
    }

    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw each detection
    detections.forEach((det) => {
      const { x1, y1, x2, y2 } = det.bbox;
      const isPresent = det.confirmed_present;
      const isKnown = det.student_name !== 'Unknown';

      // Colors
      const strokeColor = isPresent ? '#10b981' : isKnown ? '#06b6d4' : '#f59e0b';

      ctx.strokeStyle = strokeColor;
      ctx.lineWidth = 2.5;

      // Draw bounding box
      ctx.beginPath();
      ctx.roundRect(x1, y1, x2 - x1, y2 - y1, 6);
      ctx.stroke();

      // Label background
      const label = `#${det.track_id} ${det.student_name} | ${Math.round(det.engagement_score * 100)}%`;
      ctx.font = 'bold 13px Outfit, sans-serif';
      const textWidth = ctx.measureText(label).width;

      ctx.fillStyle = 'rgba(17, 22, 34, 0.85)';
      ctx.fillRect(x1, Math.max(0, y1 - 24), textWidth + 12, 22);

      // Label border
      ctx.strokeStyle = strokeColor;
      ctx.lineWidth = 1;
      ctx.strokeRect(x1, Math.max(0, y1 - 24), textWidth + 12, 22);

      // Label text
      ctx.fillStyle = '#ffffff';
      ctx.fillText(label, x1 + 6, Math.max(16, y1 - 8));
    });
  };

  // Start Webcam Stream
  const startCameraStream = async () => {
    try {
      connectWebSocket();
      setStatusMessage('Requesting camera permissions...');

      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: 'user' },
        audio: false
      });

      mediaStreamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        videoRef.current.play();
      }

      setIsStreaming(true);
      setStatusMessage('Streaming webcam frames to AI pipeline...');

      // Capture and send frames to WebSocket at ~10 FPS
      const offscreenCanvas = document.createElement('canvas');
      offscreenCanvas.width = 640;
      offscreenCanvas.height = 480;
      const offscreenCtx = offscreenCanvas.getContext('2d');

      streamIntervalRef.current = setInterval(() => {
        if (!videoRef.current || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
          return;
        }

        if (videoRef.current.readyState >= 2 && offscreenCtx) {
          offscreenCtx.drawImage(videoRef.current, 0, 0, 640, 480);
          const base64Data = offscreenCanvas.toDataURL('image/jpeg', 0.65);

          wsRef.current.send(JSON.stringify({
            action: 'frame',
            session_id: selectedSessionId,
            image: base64Data,
            include_annotated: false
          }));
        }
      }, 90); // ~11 FPS
    } catch (err: any) {
      console.error('Camera access failed:', err);
      setStatusMessage(`Camera unavailable: ${err.message || 'Permission denied'}. You can use image or video upload mode below.`);
      setIsStreaming(false);
    }
  };

  // Stop Webcam Stream
  const stopCameraStream = () => {
    if (streamIntervalRef.current) {
      clearInterval(streamIntervalRef.current);
      streamIntervalRef.current = null;
    }
    if (mediaStreamRef.current) {
      mediaStreamRef.current.getTracks().forEach((t) => t.stop());
      mediaStreamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
    setIsStreaming(false);
    setStatusMessage('Live stream stopped.');
  };

  // Handle Image Upload Inference
  const handleImageUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploadLoading(true);
    setStatusMessage('Processing image with YOLO face detector & FaceNet...');
    try {
      const res = await api.inferImage(file, selectedSessionId || undefined);
      if (res.success) {
        setInferredImageSrc(res.annotated_image);
        setFps(res.metrics.total_ms > 0 ? Math.round(1000 / res.metrics.total_ms) : 0);
        setActiveTracksCount(res.counts.active_tracks);
        setPresentCount(res.counts.present);
        setTotalStudents(res.counts.total_students);
        setAvgEngagement(res.avg_engagement);
        setLiveDetections(res.detections);
        setStatusMessage(`Image processed in ${res.metrics.total_ms}ms. Found ${res.detections.length} faces.`);
      }
    } catch (err: any) {
      console.error('Image inference error:', err);
      setStatusMessage(`Inference failed: ${err.response?.data?.detail || err.message}`);
    } finally {
      setUploadLoading(false);
    }
  };

  // Handle Video Upload Inference
  const handleVideoUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !selectedSessionId) {
      alert('Please select a session before uploading a video file.');
      return;
    }

    setUploadLoading(true);
    setStatusMessage('Uploading and analyzing classroom video through AI pipeline...');
    try {
      const res = await api.inferVideo(file, selectedSessionId, 2);
      if (res.success) {
        setStatusMessage(res.message);
        loadSessions();
      }
    } catch (err: any) {
      console.error('Video inference error:', err);
      setStatusMessage(`Video processing failed: ${err.response?.data?.detail || err.message}`);
    } finally {
      setUploadLoading(false);
    }
  };

  const selectedSession = sessions.find((s) => s.id === selectedSessionId);

  return (
    <div>
      {/* Session Toolbar */}
      <div style={{
        background: 'var(--bg-surface)',
        border: '1px solid var(--border-subtle)',
        borderRadius: 'var(--radius-md)',
        padding: '16px 24px',
        marginBottom: '24px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: 16
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 14 }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', textTransform: 'uppercase' }}>
              Target Session
            </span>
            <select
              className="form-select"
              value={selectedSessionId ?? ''}
              onChange={(e) => setSelectedSessionId(Number(e.target.value))}
              style={{ minWidth: 260 }}
            >
              {sessions.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name} ({s.status})
                </option>
              ))}
            </select>
          </div>

          {selectedSession && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 18 }}>
              <Badge status={selectedSession.status} />
              <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                {selectedSession.subject || 'Class'} &bull; {selectedSession.date}
              </span>
            </div>
          )}
        </div>

        {/* Source Mode Tabs */}
        <div style={{
          display: 'flex',
          background: 'var(--bg-surface-elevated)',
          padding: 4,
          borderRadius: 'var(--radius-sm)',
          gap: 4
        }}>
          <button
            className={`btn btn-sm ${sourceMode === 'webcam' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => setSourceMode('webcam')}
            style={{ border: 'none' }}
          >
            <Camera size={14} />
            <span>Webcam</span>
          </button>
          <button
            className={`btn btn-sm ${sourceMode === 'image' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => {
              stopCameraStream();
              setSourceMode('image');
            }}
            style={{ border: 'none' }}
          >
            <Upload size={14} />
            <span>Image Test</span>
          </button>
          <button
            className={`btn btn-sm ${sourceMode === 'video' ? 'btn-primary' : 'btn-secondary'}`}
            onClick={() => {
              stopCameraStream();
              setSourceMode('video');
            }}
            style={{ border: 'none' }}
          >
            <Video size={14} />
            <span>Video Upload</span>
          </button>
        </div>
      </div>

      {/* Main Grid: Video Stream & Sidebar Metrics */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: 24 }}>
        {/* Video Canvas Container */}
        <div>
          <div className="video-hud-container" style={{ minHeight: 440 }}>
            {sourceMode === 'webcam' && (
              <>
                <video
                  ref={videoRef}
                  playsInline
                  muted
                  className="video-element"
                  style={{ display: isStreaming ? 'block' : 'none' }}
                />
                <canvas
                  ref={canvasRef}
                  className="canvas-element"
                  style={{
                    position: 'absolute',
                    top: 0,
                    left: 0,
                    pointerEvents: 'none',
                    display: isStreaming ? 'block' : 'none'
                  }}
                />

                {!isStreaming && (
                  <div style={{ textAlign: 'center', color: 'var(--text-muted)', padding: 32 }}>
                    <Camera size={48} style={{ opacity: 0.3, marginBottom: 12 }} />
                    <p style={{ fontSize: '1rem', color: '#fff', fontWeight: 600 }}>Webcam Stream Standby</p>
                    <p style={{ fontSize: '0.82rem', marginTop: 4 }}>
                      Click "Start Live Camera" to begin real-time face detection, recognition, and tracking.
                    </p>
                    <button
                      className="btn btn-primary"
                      onClick={startCameraStream}
                      style={{ marginTop: 16 }}
                    >
                      <Play size={16} />
                      <span>Start Live Camera</span>
                    </button>
                  </div>
                )}
              </>
            )}

            {sourceMode === 'image' && (
              <div style={{ width: '100%', height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                {inferredImageSrc ? (
                  <img
                    src={inferredImageSrc}
                    alt="Inference Output"
                    style={{ maxHeight: '100%', maxWidth: '100%', objectFit: 'contain' }}
                  />
                ) : (
                  <div style={{ textAlign: 'center', padding: 32 }}>
                    <Upload size={48} style={{ opacity: 0.3, marginBottom: 12 }} />
                    <p style={{ fontSize: '1rem', color: '#fff', fontWeight: 600 }}>Upload Classroom or Student Photo</p>
                    <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginTop: 4 }}>
                      Test single-image YOLO detection, FaceNet embeddings, and observable engagement.
                    </p>
                    <label className="btn btn-primary" style={{ marginTop: 16, display: 'inline-flex' }}>
                      <input type="file" accept="image/*" onChange={handleImageUpload} style={{ display: 'none' }} />
                      <span>Select Photo</span>
                    </label>
                  </div>
                )}
              </div>
            )}

            {sourceMode === 'video' && (
              <div style={{ textAlign: 'center', padding: 48 }}>
                <Video size={48} style={{ opacity: 0.3, marginBottom: 12 }} />
                <p style={{ fontSize: '1rem', color: '#fff', fontWeight: 600 }}>Classroom Video Inference</p>
                <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)', marginTop: 4, maxWidth: 420, margin: '6px auto' }}>
                  Upload a classroom recording or the synthetic demo video (located at <code>data/sessions/demo_classroom.mp4</code>)
                  to run automated multi-target tracking and session attendance.
                </p>
                <label className="btn btn-primary" style={{ marginTop: 16, display: 'inline-flex' }}>
                  <input type="file" accept="video/*" onChange={handleVideoUpload} style={{ display: 'none' }} />
                  <span>Upload Video File</span>
                </label>
              </div>
            )}

            {/* Live Top HUD Pills */}
            <div className="hud-overlay">
              <div className="hud-pill">
                <span style={{
                  width: 8,
                  height: 8,
                  borderRadius: '50%',
                  background: isStreaming ? 'var(--accent-emerald)' : 'var(--accent-amber)'
                }} />
                <span>{isStreaming ? 'STREAMING' : 'READY'}</span>
              </div>
              <div className="hud-pill">
                <span className="font-mono">FPS: {fps}</span>
              </div>
              <div className="hud-pill">
                <Users size={13} color="var(--accent-cyan)" />
                <span>Tracks: {activeTracksCount}</span>
              </div>
            </div>
          </div>

          {/* Live Controls & Status Bar */}
          <div style={{
            marginTop: 14,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: 'var(--bg-surface)',
            padding: '12px 18px',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--border-subtle)'
          }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, fontSize: '0.82rem' }}>
              <Radio size={15} color={isStreaming ? 'var(--accent-emerald)' : 'var(--text-muted)'} />
              <span style={{ color: 'var(--text-secondary)' }}>{statusMessage}</span>
            </div>

            {sourceMode === 'webcam' && isStreaming && (
              <button className="btn btn-danger btn-sm" onClick={stopCameraStream}>
                <Square size={14} />
                <span>Stop Stream</span>
              </button>
            )}

            {sourceMode === 'image' && inferredImageSrc && (
              <label className="btn btn-secondary btn-sm" style={{ cursor: 'pointer' }}>
                <input type="file" accept="image/*" onChange={handleImageUpload} style={{ display: 'none' }} />
                <span>Test Another Photo</span>
              </label>
            )}
          </div>
        </div>

        {/* Real-time Session Sidebar Metrics */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Live Attendance Counter */}
          <div className="glass-panel" style={{ padding: 20 }}>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', textTransform: 'uppercase', fontWeight: 600 }}>
              Live Attendance
            </div>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: 8, marginTop: 8 }}>
              <span style={{ fontSize: '2.4rem', fontWeight: 700, color: 'var(--accent-emerald)' }}>
                {presentCount}
              </span>
              <span style={{ fontSize: '1rem', color: 'var(--text-muted)' }}>
                / {totalStudents} Enrolled
              </span>
            </div>

            {/* Attendance Progress Bar */}
            <div style={{
              width: '100%',
              height: 8,
              background: 'var(--bg-surface-elevated)',
              borderRadius: 999,
              marginTop: 12,
              overflow: 'hidden'
            }}>
              <div style={{
                height: '100%',
                width: `${totalStudents > 0 ? (presentCount / totalStudents) * 100 : 0}%`,
                background: 'linear-gradient(90deg, var(--accent-emerald), var(--accent-cyan))',
                borderRadius: 999,
                transition: 'width 0.3s ease'
              }} />
            </div>
          </div>

          {/* Observable Engagement Meter */}
          <div className="glass-panel" style={{ padding: 20 }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', textTransform: 'uppercase', fontWeight: 600 }}>
                Engagement Estimate
              </span>
              <Sparkles size={16} color="var(--accent-purple)" />
            </div>

            <div style={{ marginTop: 12, display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span style={{ fontSize: '2rem', fontWeight: 700, color: '#fff' }}>
                {Math.round(avgEngagement * 100)}%
              </span>
              <span style={{
                fontSize: '0.75rem',
                padding: '4px 10px',
                borderRadius: 999,
                background: avgEngagement >= 0.7 ? 'rgba(16, 185, 129, 0.15)' : 'rgba(245, 158, 11, 0.15)',
                color: avgEngagement >= 0.7 ? '#34d399' : '#fbbf24',
                fontWeight: 600
              }}>
                {avgEngagement >= 0.7 ? 'High' : avgEngagement >= 0.4 ? 'Moderate' : 'Low'}
              </span>
            </div>

            <p style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: 8 }}>
              Observable CV metric derived from facial orientation, detection confidence, and temporal presence.
            </p>
          </div>

          {/* Detected Faces Roster List */}
          <div className="glass-panel" style={{ padding: 20, flex: 1, display: 'flex', flexDirection: 'column' }}>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', textTransform: 'uppercase', fontWeight: 600, marginBottom: 12 }}>
              Active Detections ({liveDetections.length})
            </div>

            <div style={{ overflowY: 'auto', maxHeight: 220, display: 'flex', flexDirection: 'column', gap: 8 }}>
              {liveDetections.map((d) => (
                <div
                  key={d.track_id}
                  style={{
                    background: 'var(--bg-surface-elevated)',
                    padding: '8px 12px',
                    borderRadius: 'var(--radius-sm)',
                    border: '1px solid var(--border-subtle)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between'
                  }}
                >
                  <div style={{ display: 'flex', flexDirection: 'column' }}>
                    <span style={{ fontSize: '0.84rem', fontWeight: 600, color: '#fff' }}>
                      {d.student_name}
                    </span>
                    <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                      Track #{d.track_id} &bull; Conf: {Math.round(d.confidence * 100)}%
                    </span>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                    <span style={{
                      fontSize: '0.72rem',
                      fontWeight: 600,
                      color: 'var(--accent-purple)'
                    }}>
                      {Math.round(d.engagement_score * 100)}%
                    </span>
                    {d.confirmed_present && (
                      <UserCheck size={16} color="var(--accent-emerald)" />
                    )}
                  </div>
                </div>
              ))}

              {liveDetections.length === 0 && (
                <div style={{ textAlign: 'center', padding: '24px 0', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                  No active faces in current frame
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
