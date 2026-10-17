import React, { useState, useEffect } from 'react';
import {
  api,
  getToken,
  setToken,
  removeToken
} from './api';
import type {
  User,
  MotorItem,
  PipelineItem,
  ScheduleItem,
  FaultItem,
  NotificationItem
} from './api';
import { translations } from './i18n';
import type { Language } from './i18n';
import {
  Power,
  RotateCw,
  Calendar,
  AlertTriangle,
  Settings,
  Mic,
  MicOff,
  Activity,
  CheckCircle2,
  XCircle,
  Volume2,
  RefreshCw,
  LogOut,
  ShieldAlert,
  Zap,
  Droplets,
  Gauge,
  Sliders
} from 'lucide-react';

export default function App() {
  // Auth state
  const [user, setUser] = useState<User | null>(null);
  const [token, setAuthToken] = useState<string | null>(getToken());
  const [authPhone, setAuthPhone] = useState('9876543210');
  const [authPass, setAuthPass] = useState('FarmerPass123!');
  const [authError, setAuthError] = useState('');
  const [authLoading, setAuthLoading] = useState(false);

  // App settings
  const [lang, setLang] = useState<Language>('ta');
  const [uiMode, setUiMode] = useState<'easy' | 'advanced'>('easy');

  // Navigation tab
  const [activeTab, setActiveTab] = useState<'home' | 'pipelines' | 'schedules' | 'alerts' | 'tech'>('home');

  // Core Data
  const [motors, setMotors] = useState<MotorItem[]>([]);
  const [selectedMotorId, setSelectedMotorId] = useState<string>('');
  const [pipelines, setPipelines] = useState<PipelineItem[]>([]);
  const [schedules, setSchedules] = useState<ScheduleItem[]>([]);
  const [faults, setFaults] = useState<FaultItem[]>([]);
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);

  // Live WebSocket Telemetry
  const [wsConnected, setWsConnected] = useState(false);
  const [liveTelemetry, setLiveTelemetry] = useState<any>(null);

  // Action confirmations & modals
  const [confirmModal, setConfirmModal] = useState<{
    open: boolean;
    type: 'START' | 'STOP';
    motorId: string;
    motorName: string;
  } | null>(null);

  // Voice Assistant state
  const [voiceOpen, setVoiceOpen] = useState(false);
  const [voiceQuery, setVoiceQuery] = useState('');
  const [voiceResponse, setVoiceResponse] = useState('');
  const [isListening, setIsListening] = useState(false);
  const [voicePendingAction, setVoicePendingAction] = useState<any>(null);

  // Schedule modal
  const [scheduleModalOpen, setScheduleModalOpen] = useState(false);
  const [newSchedName, setNewSchedName] = useState('Morning Paddy Run');
  const [newSchedStart, setNewSchedStart] = useState('06:00');
  const [newSchedStop, setNewSchedStop] = useState('07:30');
  const [newSchedDays, setNewSchedDays] = useState('mon,tue,wed,thu,fri,sat,sun');

  // Loading indicator for commands
  const [commandLoading, setCommandLoading] = useState(false);

  const t = translations[lang];

  // 1. Initial Load & Auth Check
  useEffect(() => {
    if (token) {
      api.getProfile()
        .then((profile) => {
          setUser(profile);
          setLang(profile.preferred_language || 'ta');
          setUiMode(profile.ui_mode || 'easy');
          if (profile.farm_id) {
            loadFarmData(profile.farm_id);
          }
        })
        .catch(() => {
          removeToken();
          setAuthToken(null);
          setUser(null);
        });
    }
  }, [token]);

  const loadFarmData = async (farmId: string) => {
    try {
      const motorList = await api.getMotors(farmId);
      setMotors(motorList);
      if (motorList.length > 0 && !selectedMotorId) {
        setSelectedMotorId(motorList[0].id);
      }
      const faultList = await api.getFaults();
      setFaults(faultList);
      const notifList = await api.getNotifications();
      setNotifications(notifList);
    } catch (e) {
      console.error('Error loading farm data', e);
    }
  };

  // 2. Load Selected Motor Pipelines and Schedules
  useEffect(() => {
    if (selectedMotorId) {
      api.getPipelines(selectedMotorId).then(setPipelines).catch(console.error);
      api.getSchedules(selectedMotorId).then(setSchedules).catch(console.error);
    }
  }, [selectedMotorId]);

  // 3. Real-Time WebSocket Connection
  useEffect(() => {
    if (!token) return;
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/api/v1/ws/live`;
    let ws: WebSocket;

    try {
      ws = new WebSocket(wsUrl);
      ws.onopen = () => setWsConnected(true);
      ws.onclose = () => setWsConnected(false);
      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === 'TELEMETRY_UPDATE') {
            setLiveTelemetry(msg.telemetry);
            // Update motor status locally
            setMotors((prev) =>
              prev.map((m) =>
                m.id === msg.motor_id
                  ? {
                      ...m,
                      status: msg.motor_status,
                      total_runtime_hours: msg.total_runtime_hours
                    }
                  : m
              )
            );
            // Refresh pipelines if active motor matches
            if (msg.motor_id === selectedMotorId) {
              setPipelines((prev) =>
                prev.map((p) => ({
                  ...p,
                  actual_rotations:
                    p.pipeline_index === msg.telemetry.active_pipeline
                      ? msg.telemetry.current_rotation
                      : p.actual_rotations,
                  status:
                    p.pipeline_index === msg.telemetry.active_pipeline
                      ? 'ROTATING'
                      : p.status
                }))
              );
            }
          }
        } catch (err) {
          console.error('WS parse error', err);
        }
      };
    } catch (e) {
      console.error('WebSocket connection failed', e);
    }

    return () => {
      if (ws) ws.close();
    };
  }, [token, selectedMotorId]);

  // Handle Login
  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setAuthError('');
    setAuthLoading(true);
    try {
      const res = await api.login(authPhone, authPass);
      setToken(res.access_token);
      setAuthToken(res.access_token);
      setUser(res.user);
      setLang(res.user.preferred_language || 'ta');
      setUiMode(res.user.ui_mode || 'easy');
      if (res.user.farm_id) {
        await loadFarmData(res.user.farm_id);
      }
    } catch (err: any) {
      setAuthError(err.message || 'Login failed');
    } finally {
      setAuthLoading(false);
    }
  };

  const handleLogout = () => {
    removeToken();
    setAuthToken(null);
    setUser(null);
  };

  // Motor Commands
  const executeCommand = async (motorId: string, cmdType: 'START' | 'STOP') => {
    setCommandLoading(true);
    try {
      await api.dispatchCommand(motorId, cmdType);
      // reload motors
      if (user?.farm_id) {
        await loadFarmData(user.farm_id);
      }
      setConfirmModal(null);
    } catch (err: any) {
      alert(err.message || 'Command failed');
    } finally {
      setCommandLoading(false);
    }
  };

  // Voice Assistant with Web Speech API
  const startSpeechRecognition = () => {
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert('Speech Recognition is not supported by this browser. You can type your command.');
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.lang = lang === 'ta' ? 'ta-IN' : 'en-US';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    setIsListening(true);
    recognition.start();

    recognition.onresult = (event: any) => {
      const speechResult = event.results[0][0].transcript;
      setVoiceQuery(speechResult);
      setIsListening(false);
      handleVoiceQuery(speechResult);
    };

    recognition.onerror = () => setIsListening(false);
    recognition.onend = () => setIsListening(false);
  };

  const handleVoiceQuery = async (queryText: string) => {
    if (!queryText.trim()) return;
    try {
      const result = await api.sendVoiceQuery(queryText, lang);
      setVoiceResponse(result.response_text);

      // Play audio response using SpeechSynthesis
      if ('speechSynthesis' in window) {
        const utterance = new SpeechSynthesisUtterance(result.response_text);
        utterance.lang = lang === 'ta' ? 'ta-IN' : 'en-US';
        window.speechSynthesis.speak(utterance);
      }

      if (result.requires_confirmation) {
        setVoicePendingAction(result);
      } else {
        setVoicePendingAction(null);
      }
    } catch (e) {
      setVoiceResponse('Sorry, failed to process command.');
    }
  };

  const confirmVoiceAction = async () => {
    if (!voicePendingAction) return;
    try {
      const res = await api.executeConfirmedVoice(
        voicePendingAction.motor_id,
        voicePendingAction.action
      );
      setVoiceResponse(res.response_text);
      setVoicePendingAction(null);
      if (user?.farm_id) {
        await loadFarmData(user.farm_id);
      }
    } catch (err: any) {
      setVoiceResponse(err.message || 'Failed to execute action');
    }
  };

  // Selected motor object
  const currentMotor = motors.find((m) => m.id === selectedMotorId) || motors[0];

  // ---------------- LOGIN SCREEN ----------------
  if (!token || !user) {
    return (
      <div className="app-container" style={{ justifyContent: 'center', padding: '24px' }}>
        <div style={{ textAlign: 'center', marginBottom: '32px' }}>
          <div
            className="brand-icon-wrapper"
            style={{ width: '72px', height: '72px', margin: '0 auto 16px auto', borderRadius: '20px' }}
          >
            <Droplets size={38} />
          </div>
          <h1 style={{ fontFamily: 'var(--font-heading)', fontSize: '2rem', fontWeight: 800, color: 'var(--primary-deep)' }}>
            {t.appTitle}
          </h1>
          <p style={{ color: 'var(--primary-dark)', fontWeight: 600, fontSize: '0.95rem', marginTop: '4px' }}>
            {t.tagline}
          </p>
        </div>

        {/* Language Selection on Login */}
        <div style={{ display: 'flex', justifyContent: 'center', gap: '10px', marginBottom: '24px' }}>
          <button
            type="button"
            className={`toggle-pill ${lang === 'ta' ? 'active' : ''}`}
            onClick={() => setLang('ta')}
            style={{ padding: '8px 20px', fontSize: '0.95rem' }}
          >
            தமிழ் (Tamil)
          </button>
          <button
            type="button"
            className={`toggle-pill ${lang === 'en' ? 'active' : ''}`}
            onClick={() => setLang('en')}
            style={{ padding: '8px 20px', fontSize: '0.95rem' }}
          >
            English
          </button>
        </div>

        <div className="card">
          <h2 className="card-title" style={{ marginBottom: '18px' }}>
            {t.loginTitle}
          </h2>
          {authError && (
            <div
              style={{
                background: 'var(--danger-light)',
                color: 'var(--danger)',
                padding: '12px',
                borderRadius: 'var(--radius-sm)',
                marginBottom: '16px',
                fontWeight: 600,
                fontSize: '0.9rem'
              }}
            >
              {authError}
            </div>
          )}
          <form onSubmit={handleLogin}>
            <div style={{ marginBottom: '16px' }}>
              <label style={{ display: 'block', fontWeight: 700, marginBottom: '6px', fontSize: '0.9rem' }}>
                {t.phoneNumber}
              </label>
              <input
                type="tel"
                value={authPhone}
                onChange={(e) => setAuthPhone(e.target.value)}
                required
                style={{
                  width: '100%',
                  minHeight: '48px',
                  padding: '10px 14px',
                  borderRadius: 'var(--radius-md)',
                  border: '1.5px solid var(--border)',
                  fontSize: '1.1rem',
                  fontFamily: 'inherit'
                }}
              />
            </div>

            <div style={{ marginBottom: '22px' }}>
              <label style={{ display: 'block', fontWeight: 700, marginBottom: '6px', fontSize: '0.9rem' }}>
                {t.password}
              </label>
              <input
                type="password"
                value={authPass}
                onChange={(e) => setAuthPass(e.target.value)}
                required
                style={{
                  width: '100%',
                  minHeight: '48px',
                  padding: '10px 14px',
                  borderRadius: 'var(--radius-md)',
                  border: '1.5px solid var(--border)',
                  fontSize: '1.1rem',
                  fontFamily: 'inherit'
                }}
              />
            </div>

            <button
              type="submit"
              className="btn-huge btn-start"
              disabled={authLoading}
              style={{ minHeight: '56px', fontSize: '1.15rem' }}
            >
              {authLoading ? 'Signing in...' : t.loginBtn}
            </button>
          </form>

          <div
            style={{
              marginTop: '16px',
              padding: '10px',
              background: 'var(--surface-alt)',
              borderRadius: 'var(--radius-sm)',
              textAlign: 'center',
              fontSize: '0.82rem',
              color: 'var(--text-muted)'
            }}
          >
            {t.testCredentials}
          </div>
        </div>
      </div>
    );
  }

  // ---------------- MAIN APPLICATION ----------------
  return (
    <div className={`app-container ${uiMode === 'easy' ? 'easy-mode' : ''}`}>
      {/* Top Header */}
      <header className="app-header">
        <div className="brand-badge">
          <div className="brand-icon-wrapper">
            <Droplets size={24} />
          </div>
          <div>
            <div className="brand-title">{t.appTitle}</div>
            <div className="brand-sub">
              {user.farm_name || 'Pollachi Farm'} • {wsConnected ? '● Live' : '○ Offline'}
            </div>
          </div>
        </div>

        <div className="header-actions">
          {/* Mode Switcher */}
          <button
            className={`toggle-pill ${uiMode === 'easy' ? 'active' : ''}`}
            onClick={() => {
              const nextMode = uiMode === 'easy' ? 'advanced' : 'easy';
              setUiMode(nextMode);
              api.updateSettings({ ui_mode: nextMode });
            }}
            title="Switch Easy / Advanced Mode"
          >
            <Sliders size={14} style={{ marginRight: '4px' }} />
            {uiMode === 'easy' ? t.easyMode : t.advMode}
          </button>

          {/* Language Switcher */}
          <button
            className="toggle-pill"
            onClick={() => {
              const nextLang = lang === 'ta' ? 'en' : 'ta';
              setLang(nextLang);
              api.updateSettings({ preferred_language: nextLang });
            }}
          >
            {lang === 'ta' ? 'English' : 'தமிழ்'}
          </button>

          {/* Logout */}
          <button
            onClick={handleLogout}
            className="btn-outline"
            style={{ minHeight: '40px', padding: '0 10px', border: 'none', color: 'var(--danger)' }}
            title="Logout"
          >
            <LogOut size={18} />
          </button>
        </div>
      </header>

      {/* Main Content Area */}
      <main style={{ padding: '16px', flex: 1, paddingBottom: '90px' }}>
        {/* Active Fault Alert Banner (if any) */}
        {faults.length > 0 && (
          <div
            style={{
              background: 'var(--danger-light)',
              border: '2px solid #f87171',
              borderRadius: 'var(--radius-lg)',
              padding: '16px',
              marginBottom: '16px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '12px'
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <ShieldAlert size={28} color="var(--danger)" />
              <div>
                <strong style={{ color: '#991b1b', fontSize: '0.95rem' }}>
                  {faults[0].fault_name}
                </strong>
                <p style={{ fontSize: '0.82rem', color: '#7f1d1d' }}>
                  {faults[0].explanation}
                </p>
              </div>
            </div>
            <button
              onClick={() => setActiveTab('alerts')}
              className="btn-outline"
              style={{ minHeight: '36px', fontSize: '0.8rem', whiteSpace: 'nowrap', borderColor: '#f87171' }}
            >
              {t.safeAction}
            </button>
          </div>
        )}

        {/* ----------------- TAB: HOME / DASHBOARD ----------------- */}
        {activeTab === 'home' && (
          <div>
            {/* Motor Selection Bar (if multiple motors exist) */}
            {motors.length > 1 && (
              <div style={{ display: 'flex', gap: '8px', overflowX: 'auto', marginBottom: '14px', paddingBottom: '4px' }}>
                {motors.map((m) => (
                  <button
                    key={m.id}
                    onClick={() => setSelectedMotorId(m.id)}
                    className={`toggle-pill ${selectedMotorId === m.id ? 'active' : ''}`}
                    style={{ minHeight: '44px', whiteSpace: 'nowrap' }}
                  >
                    {m.name}
                  </button>
                ))}
              </div>
            )}

            {/* Primary Motor Card */}
            {currentMotor ? (
              <div className="card" style={{ borderTop: '4px solid var(--primary)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
                  <div>
                    <h2 className="card-title">{currentMotor.name}</h2>
                    <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>
                      {currentMotor.hp_rating} HP • Channel {currentMotor.relay_channel} •{' '}
                      {currentMotor.device?.is_online ? 'Controller Active' : 'Controller Offline'}
                    </span>
                  </div>

                  {/* Status Pill */}
                  <div
                    className={`status-pill ${
                      currentMotor.status === 'RUNNING'
                        ? 'status-running'
                        : currentMotor.status === 'FAULT'
                        ? 'status-fault'
                        : 'status-stopped'
                    }`}
                  >
                    {currentMotor.status === 'RUNNING' && <Activity size={16} className="rotating" />}
                    {currentMotor.status === 'RUNNING'
                      ? t.statusRunning
                      : currentMotor.status === 'FAULT'
                      ? t.statusFault
                      : t.statusStopped}
                  </div>
                </div>

                {/* Primary Action Buttons (Accessible, >64dp) */}
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', margin: '20px 0' }}>
                  {currentMotor.status !== 'RUNNING' ? (
                    <button
                      className="btn-huge btn-start"
                      disabled={commandLoading || currentMotor.status === 'FAULT'}
                      onClick={() =>
                        setConfirmModal({
                          open: true,
                          type: 'START',
                          motorId: currentMotor.id,
                          motorName: currentMotor.name
                        })
                      }
                    >
                      <Power size={28} />
                      {t.startMotor}
                    </button>
                  ) : (
                    <button
                      className="btn-huge btn-stop"
                      disabled={commandLoading}
                      onClick={() =>
                        setConfirmModal({
                          open: true,
                          type: 'STOP',
                          motorId: currentMotor.id,
                          motorName: currentMotor.name
                        })
                      }
                    >
                      <Power size={28} />
                      {t.stopMotor}
                    </button>
                  )}
                </div>

                {/* Active Seven-Pipeline Quick Card */}
                <div
                  style={{
                    background: 'var(--surface-alt)',
                    padding: '14px',
                    borderRadius: 'var(--radius-md)',
                    border: '1.5px solid var(--border)',
                    marginBottom: '16px'
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <RotateCw
                        size={20}
                        color="var(--primary)"
                        className={currentMotor.status === 'RUNNING' ? 'rotating' : ''}
                      />
                      <span style={{ fontWeight: 700, fontSize: '0.92rem' }}>
                        {t.activePipeline}: Line {liveTelemetry?.active_pipeline || 1}
                      </span>
                    </div>
                    <span
                      style={{
                        background: 'var(--primary-light)',
                        color: 'var(--primary-dark)',
                        padding: '4px 10px',
                        borderRadius: 'var(--radius-full)',
                        fontWeight: 800,
                        fontSize: '0.84rem'
                      }}
                    >
                      {liveTelemetry?.current_rotation || 0} / 5 {lang === 'ta' ? 'சுற்றுகள்' : 'rotations'}
                    </span>
                  </div>
                </div>

                {/* Live Sensors Grid */}
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(2, 1fr)',
                    gap: '10px'
                  }}
                >
                  <div
                    style={{
                      background: 'var(--surface-alt)',
                      padding: '12px',
                      borderRadius: 'var(--radius-md)',
                      border: '1px solid var(--border)'
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                      <Zap size={14} color="#eab308" />
                      {t.voltage}
                    </div>
                    <div style={{ fontSize: '1.35rem', fontWeight: 800, marginTop: '4px' }}>
                      {liveTelemetry?.avg_voltage || 230} V
                    </div>
                  </div>

                  <div
                    style={{
                      background: 'var(--surface-alt)',
                      padding: '12px',
                      borderRadius: 'var(--radius-md)',
                      border: '1px solid var(--border)'
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                      <Activity size={14} color="var(--primary)" />
                      {t.current}
                    </div>
                    <div style={{ fontSize: '1.35rem', fontWeight: 800, marginTop: '4px' }}>
                      {liveTelemetry?.avg_current || 0.0} A
                    </div>
                  </div>

                  <div
                    style={{
                      background: 'var(--surface-alt)',
                      padding: '12px',
                      borderRadius: 'var(--radius-md)',
                      border: '1px solid var(--border)'
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                      <Droplets size={14} color="var(--water-blue)" />
                      {t.flowRate}
                    </div>
                    <div style={{ fontSize: '1.35rem', fontWeight: 800, marginTop: '4px' }}>
                      {liveTelemetry?.flow_rate_lpm || 0} {t.litresPerMin}
                    </div>
                  </div>

                  <div
                    style={{
                      background: 'var(--surface-alt)',
                      padding: '12px',
                      borderRadius: 'var(--radius-md)',
                      border: '1px solid var(--border)'
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                      <Gauge size={14} color="var(--text-muted)" />
                      {t.runtimeHours}
                    </div>
                    <div style={{ fontSize: '1.35rem', fontWeight: 800, marginTop: '4px' }}>
                      {currentMotor.total_runtime_hours} {t.hours}
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="card">{t.registeredMotors}</div>
            )}
          </div>
        )}

        {/* ----------------- TAB: SEVEN-PIPELINES ----------------- */}
        {activeTab === 'pipelines' && (
          <div>
            <div className="card">
              <h2 className="card-title">{t.pipelineTitle}</h2>
              <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '14px' }}>
                {t.pipelineSub}
              </p>

              {/* 7-Pipeline Visual Wheel */}
              <div className="pipeline-rotary-container">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontWeight: 800, fontSize: '0.95rem' }}>
                    Active: Line {liveTelemetry?.active_pipeline || 1}
                  </span>
                  <span style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--primary)' }}>
                    {liveTelemetry?.current_rotation || 0} / 5 Rotations
                  </span>
                </div>

                <div className="pipeline-wheel">
                  {[1, 2, 3, 4, 5, 6, 7].map((num) => {
                    const isActive = (liveTelemetry?.active_pipeline || 1) === num;
                    const pipeData = pipelines.find((p) => p.pipeline_index === num);
                    const isObstructed = pipeData?.status === 'OBSTRUCTED';

                    return (
                      <div
                        key={num}
                        className={`pipeline-node ${isActive ? 'active' : ''} ${
                          isObstructed ? 'obstructed' : ''
                        }`}
                      >
                        <div className="pipe-num">{num}</div>
                        <div className="pipe-rotations">
                          {isActive ? `${liveTelemetry?.current_rotation || 0}/5` : '5/5'}
                        </div>
                      </div>
                    );
                  })}
                </div>

                <button
                  onClick={() => api.resetPipelines(selectedMotorId)}
                  className="btn-outline"
                  style={{ width: '100%', minHeight: '44px', marginTop: '6px' }}
                >
                  <RefreshCw size={16} style={{ marginRight: '6px' }} />
                  {t.resetSequence}
                </button>
              </div>

              {/* Detailed Pipelines List */}
              <div style={{ marginTop: '18px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {pipelines.map((p) => (
                  <div
                    key={p.id}
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      padding: '12px 14px',
                      background: 'var(--surface-alt)',
                      borderRadius: 'var(--radius-md)',
                      border: '1px solid var(--border)'
                    }}
                  >
                    <div>
                      <strong style={{ fontSize: '0.92rem' }}>Line {p.pipeline_index}: {p.name}</strong>
                      <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                        Target: {p.target_rotations} rotations • Flow: {p.flow_rate_lpm} LPM
                      </div>
                    </div>
                    <span
                      style={{
                        padding: '4px 8px',
                        borderRadius: 'var(--radius-sm)',
                        fontSize: '0.75rem',
                        fontWeight: 700,
                        background:
                          p.status === 'FLOWING' || p.status === 'ROTATING'
                            ? '#dcfce7'
                            : p.status === 'OBSTRUCTED'
                            ? '#fee2e2'
                            : '#f1f5f9',
                        color:
                          p.status === 'FLOWING' || p.status === 'ROTATING'
                            ? '#15803d'
                            : p.status === 'OBSTRUCTED'
                            ? '#b91c1c'
                            : '#475569'
                      }}
                    >
                      {p.status}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ----------------- TAB: SCHEDULES ----------------- */}
        {activeTab === 'schedules' && (
          <div>
            <div className="card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
                <h2 className="card-title">{t.scheduleTitle}</h2>
                <button
                  onClick={() => setScheduleModalOpen(true)}
                  className="btn-primary"
                  style={{ minHeight: '40px', fontSize: '0.85rem' }}
                >
                  + {t.addSchedule}
                </button>
              </div>

              {schedules.length === 0 ? (
                <p style={{ color: 'var(--text-muted)', textAlign: 'center', padding: '20px 0' }}>
                  {t.noSchedules}
                </p>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
                  {schedules.map((s) => (
                    <div
                      key={s.id}
                      style={{
                        padding: '14px',
                        background: 'var(--surface-alt)',
                        borderRadius: 'var(--radius-md)',
                        border: '1px solid var(--border)',
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center'
                      }}
                    >
                      <div>
                        <strong style={{ fontSize: '1rem', display: 'block' }}>{s.name}</strong>
                        <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                          {s.start_time} - {s.stop_time || `${s.duration_minutes}m`} • {s.days_of_week}
                        </span>
                        <div style={{ fontSize: '0.78rem', color: 'var(--primary)', fontWeight: 600, marginTop: '2px' }}>
                          Mode: {s.pipeline_mode} ({s.timezone})
                        </div>
                      </div>
                      <button
                        onClick={async () => {
                          await api.deleteSchedule(s.id);
                          setSchedules(schedules.filter((x) => x.id !== s.id));
                        }}
                        style={{
                          background: 'none',
                          border: 'none',
                          color: 'var(--danger)',
                          cursor: 'pointer',
                          padding: '6px'
                        }}
                      >
                        <XCircle size={20} />
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        )}

        {/* ----------------- TAB: ALERTS & FAULTS ----------------- */}
        {activeTab === 'alerts' && (
          <div>
            <div className="card">
              <h2 className="card-title">{t.alertsTitle}</h2>

              {faults.length === 0 ? (
                <div style={{ textAlign: 'center', padding: '30px 0', color: 'var(--primary)' }}>
                  <CheckCircle2 size={48} style={{ margin: '0 auto 12px auto' }} />
                  <p style={{ fontWeight: 700 }}>{t.noAlerts}</p>
                </div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {faults.map((f) => (
                    <div
                      key={f.id}
                      style={{
                        background: 'var(--danger-light)',
                        border: '1.5px solid #fca5a5',
                        borderRadius: 'var(--radius-md)',
                        padding: '16px'
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#991b1b', marginBottom: '8px' }}>
                        <AlertTriangle size={20} />
                        <strong style={{ fontSize: '1rem' }}>{f.fault_name}</strong>
                      </div>
                      <p style={{ fontSize: '0.88rem', color: '#7f1d1d', marginBottom: '8px' }}>
                        <strong>{t.cause}</strong> {f.explanation}
                      </p>
                      <p style={{ fontSize: '0.88rem', color: '#7f1d1d', marginBottom: '14px' }}>
                        <strong>{t.safeAction}</strong> {f.safe_action}
                      </p>
                      <button
                        onClick={async () => {
                          await api.resolveFault(f.id);
                          setFaults(faults.filter((x) => x.id !== f.id));
                          if (user.farm_id) await loadFarmData(user.farm_id);
                        }}
                        className="btn-outline"
                        style={{ background: '#fff', color: '#991b1b', borderColor: '#f87171', width: '100%' }}
                      >
                        {t.markResolved}
                      </button>
                    </div>
                  ))}
                </div>
              )}

              {/* Notification History */}
              <h3 style={{ fontSize: '1rem', fontWeight: 700, margin: '24px 0 12px 0' }}>
                Recent Notifications
              </h3>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {notifications.map((n) => (
                  <div
                    key={n.id}
                    style={{
                      padding: '12px',
                      background: 'var(--surface-alt)',
                      borderRadius: 'var(--radius-sm)',
                      fontSize: '0.85rem'
                    }}
                  >
                    <div style={{ fontWeight: 700 }}>{n.title}</div>
                    <div style={{ color: 'var(--text-muted)' }}>{n.message}</div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* ----------------- TAB: TECHNICIAN & SIMULATOR ----------------- */}
        {activeTab === 'tech' && (
          <div>
            <div className="card">
              <h2 className="card-title">{t.techPanel}</h2>
              <div
                style={{
                  background: 'var(--surface-alt)',
                  padding: '14px',
                  borderRadius: 'var(--radius-md)',
                  marginBottom: '16px'
                }}
              >
                <strong>{t.hardwareStatus}</strong>
                <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
                  Serial: FS-CTRL-88219 • Firmware: v2.4.0-prod • 7.5 HP Contactor Interlocked
                </p>
              </div>

              <strong style={{ display: 'block', marginBottom: '10px', fontSize: '0.9rem' }}>
                {t.injectFault}
              </strong>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '10px' }}>
                <button
                  className="btn-outline"
                  onClick={() => api.injectSimulatorFault('UNDER_VOLTAGE')}
                  style={{ borderColor: 'var(--warning)', color: 'var(--warning)', fontSize: '0.82rem' }}
                >
                  {t.injectUnderVolt}
                </button>
                <button
                  className="btn-outline"
                  onClick={() => api.injectSimulatorFault('OVERLOAD')}
                  style={{ borderColor: 'var(--danger)', color: 'var(--danger)', fontSize: '0.82rem' }}
                >
                  {t.injectOverload}
                </button>
                <button
                  className="btn-outline"
                  onClick={() => api.injectSimulatorFault('DRY_RUN')}
                  style={{ borderColor: 'var(--danger)', color: 'var(--danger)', fontSize: '0.82rem' }}
                >
                  {t.injectDryRun}
                </button>
                <button
                  className="btn-outline"
                  onClick={() => api.injectSimulatorFault('OBSTRUCTION')}
                  style={{ borderColor: '#7c3aed', color: '#7c3aed', fontSize: '0.82rem' }}
                >
                  {t.injectObstruction}
                </button>
              </div>

              <button
                className="btn-primary"
                onClick={() => api.injectSimulatorFault(null)}
                style={{ width: '100%', marginTop: '14px', background: 'var(--primary)' }}
              >
                {t.clearFaults}
              </button>
            </div>
          </div>
        )}
      </main>

      {/* Floating Voice Assistant Button (Accessible, prominent) */}
      <button
        className={`voice-fab ${isListening ? 'listening' : ''}`}
        onClick={() => setVoiceOpen(true)}
        title="Farm Saathi Voice Assistant"
      >
        <Mic size={30} />
      </button>

      {/* Voice Assistant Modal / Drawer */}
      {voiceOpen && (
        <div className="modal-overlay" onClick={() => setVoiceOpen(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Volume2 size={24} color="var(--primary)" />
                <h3 style={{ fontFamily: 'var(--font-heading)', fontSize: '1.2rem', fontWeight: 800 }}>
                  {t.voiceTitle}
                </h3>
              </div>
              <button
                onClick={() => setVoiceOpen(false)}
                style={{ background: 'none', border: 'none', cursor: 'pointer' }}
              >
                <XCircle size={24} />
              </button>
            </div>

            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '14px' }}>
              {t.voiceSpeakPrompt}
            </p>

            {/* Mic trigger and input */}
            <div style={{ display: 'flex', gap: '8px', marginBottom: '16px' }}>
              <input
                type="text"
                placeholder={t.voicePlaceholder}
                value={voiceQuery}
                onChange={(e) => setVoiceQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleVoiceQuery(voiceQuery)}
                style={{
                  flex: 1,
                  padding: '12px 14px',
                  borderRadius: 'var(--radius-md)',
                  border: '1.5px solid var(--border)',
                  fontSize: '1rem'
                }}
              />
              <button
                type="button"
                onClick={startSpeechRecognition}
                className="btn-outline"
                style={{
                  padding: '0 16px',
                  background: isListening ? 'var(--danger-light)' : 'var(--surface-alt)'
                }}
              >
                {isListening ? <MicOff size={22} color="var(--danger)" /> : <Mic size={22} color="var(--primary)" />}
              </button>
              <button
                type="button"
                onClick={() => handleVoiceQuery(voiceQuery)}
                className="btn-primary"
              >
                {t.voiceSend}
              </button>
            </div>

            {/* Spoken / Text Response Box */}
            {voiceResponse && (
              <div
                style={{
                  background: 'var(--primary-light)',
                  border: '1.5px solid var(--primary-border)',
                  borderRadius: 'var(--radius-md)',
                  padding: '16px',
                  color: 'var(--primary-dark)',
                  fontSize: '1.05rem',
                  fontWeight: 700,
                  marginBottom: '16px'
                }}
              >
                {voiceResponse}
              </div>
            )}

            {/* Consequential action confirmation button */}
            {voicePendingAction && (
              <div style={{ display: 'flex', gap: '10px' }}>
                <button
                  onClick={confirmVoiceAction}
                  className="btn-huge btn-start"
                  style={{ minHeight: '52px', fontSize: '1rem' }}
                >
                  {t.confirmYes}
                </button>
                <button
                  onClick={() => setVoicePendingAction(null)}
                  className="btn-outline"
                  style={{ flex: 1, minHeight: '52px' }}
                >
                  {t.cancel}
                </button>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Confirmation Modal for Start / Stop */}
      {confirmModal && (
        <div className="modal-overlay" onClick={() => setConfirmModal(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h3 style={{ fontFamily: 'var(--font-heading)', fontSize: '1.3rem', fontWeight: 800, marginBottom: '8px' }}>
              {confirmModal.type === 'START' ? t.startMotor : t.stopMotor}
            </h3>
            <p style={{ fontSize: '1rem', color: 'var(--text-muted)', marginBottom: '20px' }}>
              {confirmModal.type === 'START' ? t.confirmStart : t.confirmStop} ({confirmModal.motorName})
            </p>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <button
                className={`btn-huge ${confirmModal.type === 'START' ? 'btn-start' : 'btn-stop'}`}
                onClick={() => executeCommand(confirmModal.motorId, confirmModal.type)}
                disabled={commandLoading}
              >
                {confirmModal.type === 'START' ? t.confirmYes : t.confirmStopYes}
              </button>
              <button
                className="btn-outline"
                onClick={() => setConfirmModal(null)}
                style={{ minHeight: '48px' }}
              >
                {t.cancel}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Schedule Creation Modal */}
      {scheduleModalOpen && (
        <div className="modal-overlay" onClick={() => setScheduleModalOpen(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h3 style={{ fontFamily: 'var(--font-heading)', fontSize: '1.3rem', fontWeight: 800, marginBottom: '14px' }}>
              {t.addSchedule}
            </h3>

            <div style={{ marginBottom: '12px' }}>
              <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 700, marginBottom: '4px' }}>
                {t.scheduleName}
              </label>
              <input
                type="text"
                value={newSchedName}
                onChange={(e) => setNewSchedName(e.target.value)}
                style={{ width: '100%', padding: '10px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)' }}
              />
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '10px', marginBottom: '12px' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 700, marginBottom: '4px' }}>
                  {t.startTime}
                </label>
                <input
                  type="time"
                  value={newSchedStart}
                  onChange={(e) => setNewSchedStart(e.target.value)}
                  style={{ width: '100%', padding: '10px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)' }}
                />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 700, marginBottom: '4px' }}>
                  {t.stopTime}
                </label>
                <input
                  type="time"
                  value={newSchedStop}
                  onChange={(e) => setNewSchedStop(e.target.value)}
                  style={{ width: '100%', padding: '10px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)' }}
                />
              </div>
            </div>

            <div style={{ marginBottom: '12px' }}>
              <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 700, marginBottom: '4px' }}>
                {t.activeDays}
              </label>
              <input
                type="text"
                value={newSchedDays}
                onChange={(e) => setNewSchedDays(e.target.value)}
                placeholder="mon,tue,wed,thu,fri,sat,sun"
                style={{ width: '100%', padding: '10px', borderRadius: 'var(--radius-sm)', border: '1px solid var(--border)' }}
              />
            </div>

            <div style={{ marginBottom: '18px' }}>
              <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 700, marginBottom: '4px' }}>
                Pipeline Mode
              </label>
              <div
                style={{
                  background: 'var(--surface-alt)',
                  padding: '10px',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '0.85rem',
                  fontWeight: 600
                }}
              >
                {t.all7PipelineMode}
              </div>
            </div>

            <button
              className="btn-huge btn-start"
              onClick={async () => {
                if (!selectedMotorId) return;
                await api.createSchedule({
                  motor_id: selectedMotorId,
                  name: newSchedName,
                  start_time: newSchedStart,
                  stop_time: newSchedStop,
                  days_of_week: newSchedDays,
                  pipeline_mode: 'ALL_7_SEQUENTIAL'
                });
                const updated = await api.getSchedules(selectedMotorId);
                setSchedules(updated);
                setScheduleModalOpen(false);
              }}
              style={{ minHeight: '52px', fontSize: '1.05rem' }}
            >
              {t.saveSchedule}
            </button>
          </div>
        </div>
      )}

      {/* Bottom Navigation Bar */}
      <nav className="bottom-nav">
        <button
          className={`nav-item ${activeTab === 'home' ? 'active' : ''}`}
          onClick={() => setActiveTab('home')}
        >
          <Power size={22} />
          {t.navHome}
        </button>

        <button
          className={`nav-item ${activeTab === 'pipelines' ? 'active' : ''}`}
          onClick={() => setActiveTab('pipelines')}
        >
          <RotateCw size={22} />
          {t.navPipelines}
        </button>

        <button
          className={`nav-item ${activeTab === 'schedules' ? 'active' : ''}`}
          onClick={() => setActiveTab('schedules')}
        >
          <Calendar size={22} />
          {t.navSchedules}
        </button>

        <button
          className={`nav-item ${activeTab === 'alerts' ? 'active' : ''}`}
          onClick={() => setActiveTab('alerts')}
        >
          <AlertTriangle size={22} />
          {t.navAlerts}
        </button>

        <button
          className={`nav-item ${activeTab === 'tech' ? 'active' : ''}`}
          onClick={() => setActiveTab('tech')}
        >
          <Settings size={22} />
          {t.navSettings}
        </button>
      </nav>
    </div>
  );
}
