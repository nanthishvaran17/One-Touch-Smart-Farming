const API_BASE = '/api/v1';

export interface User {
  id: string;
  phone_number: string;
  full_name: string;
  preferred_language: 'ta' | 'en';
  role: string;
  ui_mode: 'easy' | 'advanced';
  farm_id?: string;
  farm_name?: string;
}

export interface MotorItem {
  id: string;
  farm_id: string;
  name: string;
  motor_type: string;
  hp_rating: number;
  relay_channel: number;
  status: 'STOPPED' | 'STARTING' | 'RUNNING' | 'STOPPING' | 'FAULT' | 'OFFLINE';
  last_status_change?: string;
  total_runtime_hours: number;
  device?: {
    id: string;
    serial_number: string;
    device_name: string;
    is_online: boolean;
    firmware_version: string;
    last_heartbeat?: string;
  };
  safety_config?: {
    min_voltage: number;
    max_voltage: number;
    max_current: number;
    dry_run_current: number;
    max_runtime_minutes: number;
  };
  active_pipeline?: {
    pipeline_index: number;
    name: string;
    target_rotations: number;
    actual_rotations: number;
    status: string;
    flow_rate_lpm: number;
  };
  latest_reading?: {
    timestamp?: string;
    voltage_r?: number;
    voltage_y?: number;
    voltage_b?: number;
    current_r?: number;
    current_y?: number;
    current_b?: number;
    flow_rate_lpm: number;
    active_power_kw: number;
    controller_temp_c?: number;
    mains_healthy: boolean;
  };
}

export interface PipelineItem {
  id: string;
  pipeline_index: number;
  name: string;
  target_rotations: number;
  actual_rotations: number;
  is_enabled: boolean;
  status: 'IDLE' | 'ROTATING' | 'FLOWING' | 'COMPLETED' | 'FAULT' | 'OBSTRUCTED';
  flow_rate_lpm: number;
  fault_reason?: string;
}

export interface ScheduleItem {
  id: string;
  motor_id: string;
  motor_name: string;
  name: string;
  schedule_type: string;
  days_of_week: string;
  start_time: string;
  stop_time?: string;
  duration_minutes: number;
  pipeline_mode: string;
  pipeline_sequence: number[];
  is_active: boolean;
  timezone: string;
}

export interface FaultItem {
  id: string;
  motor_id: string;
  motor_name: string;
  fault_code: string;
  fault_name: string;
  severity: string;
  started_at: string;
  explanation: string;
  safe_action: string;
}

export interface NotificationItem {
  id: string;
  category: string;
  title: string;
  message: string;
  severity: string;
  is_read: boolean;
  created_at: string;
}

// Token helper
export const getToken = () => localStorage.getItem('fs_token');
export const setToken = (t: string) => localStorage.setItem('fs_token', t);
export const removeToken = () => localStorage.removeItem('fs_token');

const authHeaders = () => {
  const t = getToken();
  return {
    'Content-Type': 'application/json',
    ...(t ? { Authorization: `Bearer ${t}` } : {})
  };
};

export const api = {
  // Auth
  async login(phone_number: string, password: string) {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ phone_number, password })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Login failed');
    }
    return res.json();
  },

  async register(data: any) {
    const res = await fetch(`${API_BASE}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Registration failed');
    }
    return res.json();
  },

  async getProfile() {
    const res = await fetch(`${API_BASE}/auth/me`, { headers: authHeaders() });
    if (!res.ok) throw new Error('Failed to load profile');
    return res.json();
  },

  async updateSettings(settings: { preferred_language?: string; ui_mode?: string }) {
    const res = await fetch(`${API_BASE}/auth/settings`, {
      method: 'PATCH',
      headers: authHeaders(),
      body: JSON.stringify(settings)
    });
    return res.json();
  },

  // Motors
  async getMotors(farmId: string): Promise<MotorItem[]> {
    const res = await fetch(`${API_BASE}/farms/${farmId}/motors`, { headers: authHeaders() });
    if (!res.ok) throw new Error('Failed to fetch motors');
    return res.json();
  },

  async dispatchCommand(motorId: string, commandType: string, parameters: any = {}) {
    const res = await fetch(`${API_BASE}/motors/${motorId}/commands`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({ command_type: commandType, parameters })
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Command failed');
    }
    return res.json();
  },

  // 7-Pipelines
  async getPipelines(motorId: string): Promise<PipelineItem[]> {
    const res = await fetch(`${API_BASE}/motors/${motorId}/pipelines`, { headers: authHeaders() });
    if (!res.ok) throw new Error('Failed to fetch pipelines');
    return res.json();
  },

  async resetPipelines(motorId: string) {
    const res = await fetch(`${API_BASE}/motors/${motorId}/pipelines/reset`, {
      method: 'POST',
      headers: authHeaders()
    });
    return res.json();
  },

  // Schedules
  async getSchedules(motorId: string): Promise<ScheduleItem[]> {
    const res = await fetch(`${API_BASE}/motors/${motorId}/schedules`, { headers: authHeaders() });
    if (!res.ok) throw new Error('Failed to fetch schedules');
    return res.json();
  },

  async createSchedule(data: any) {
    const res = await fetch(`${API_BASE}/motors/${data.motor_id}/schedules`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify(data)
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.detail || 'Failed to create schedule');
    }
    return res.json();
  },

  async deleteSchedule(scheduleId: string) {
    const res = await fetch(`${API_BASE}/schedules/${scheduleId}`, {
      method: 'DELETE',
      headers: authHeaders()
    });
    return res.json();
  },

  // Notifications & Faults
  async getNotifications(): Promise<NotificationItem[]> {
    const res = await fetch(`${API_BASE}/notifications`, { headers: authHeaders() });
    return res.json();
  },

  async getFaults(): Promise<FaultItem[]> {
    const res = await fetch(`${API_BASE}/faults`, { headers: authHeaders() });
    return res.json();
  },

  async resolveFault(faultId: string) {
    const res = await fetch(`${API_BASE}/faults/${faultId}/resolve`, {
      method: 'POST',
      headers: authHeaders()
    });
    return res.json();
  },

  // Voice
  async sendVoiceQuery(text: string, language: string) {
    const res = await fetch(`${API_BASE}/voice/query`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({ text, language })
    });
    return res.json();
  },

  async executeConfirmedVoice(motorId: string, action: string) {
    const res = await fetch(`${API_BASE}/voice/execute-confirmed`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({ motor_id: motorId, action })
    });
    return res.json();
  },

  // Simulator Diagnostics
  async toggleSimulator(enable: boolean) {
    const res = await fetch(`${API_BASE}/devices/simulator/toggle`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({ enable })
    });
    return res.json();
  },

  async injectSimulatorFault(faultType: string | null) {
    const res = await fetch(`${API_BASE}/devices/simulator/inject-fault`, {
      method: 'POST',
      headers: authHeaders(),
      body: JSON.stringify({ fault_type: faultType })
    });
    return res.json();
  }
};
