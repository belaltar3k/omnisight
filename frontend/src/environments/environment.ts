const GATEWAY = `/api/v1`;

export const environment = {
    auth: `${GATEWAY}/auth`,
    camera: `${GATEWAY}/cameras`,
    profile: `${GATEWAY}/profiles`,
    zoneAssignment: `${GATEWAY}/zone-assignments`,
    zone: `${GATEWAY}/zones`,
    edgeNode: `${GATEWAY}/edge-nodes`,
    alert: `${GATEWAY}/alerts`,
    annotation: `${GATEWAY}/annotations`,
    dataset: `${GATEWAY}/datasets`,
    incident: `${GATEWAY}/incidents`,
    mlModel: `${GATEWAY}/ml-models`,
    training: `${GATEWAY}/training`,
    user: `${GATEWAY}/users`,
    notification: `${GATEWAY}/notifications`,
    analytics: `${GATEWAY}/analytics`,
    deviceToken: `${GATEWAY}/device-tokens`,
    settings: `${GATEWAY}/settings`,
};
export const authApiEndpoints = {
  register: `${environment.auth}/register`,
  login: `${environment.auth}/login`,
  refresh: `${environment.auth}/refresh`,
  logout: `${environment.auth}/logout`,
  me: `${environment.auth}/me`,
  forgotPassword: `${environment.auth}/forgot-password`,
  resetPassword: `${environment.auth}/reset-password`,
};

export const profileApiEndpoints = {
  createProfile: `${environment.profile}`,
  getProfiles: `${environment.profile}`,
  getProfileByAuthId: (id: string) => `${environment.profile}/auth/${id}`,
  getFullProfile: (id: string) => `${environment.profile}/auth/${id}/full`,
  updateProfile: (id: string) => `${environment.profile}/auth/${id}`,
  deleteProfile: (id: string) => `${environment.profile}/auth/${id}`,
};

export const zoneAssignmentApiEndpoints = {
  createAssignment: `${environment.zoneAssignment}`,
  getAssignments: `${environment.zoneAssignment}`,
  getAssignmentsByUser: (id: string) => `${environment.zoneAssignment}/user/${id}`,
  getAssignmentsByZone: (id: string) => `${environment.zoneAssignment}/zone/${id}`,
  getZoneUsers: (id: string) => `${environment.zoneAssignment}/zone/${id}/users`,
  reassignZone: (id: string) => `${environment.zoneAssignment}/${id}/reassign`,
  deleteByUserAndZone: (uid: string, zid: string) =>
    `${environment.zoneAssignment}/user/${uid}/zone/${zid}`,
  deleteById: (id: string) => `${environment.zoneAssignment}/${id}`,
};

export const zoneApiEndpoints = {
  createZone: `${environment.zone}`,
  getZones: `${environment.zone}`,
  getZoneById: (id: string) => `${environment.zone}/${id}`,
  updateZone: (id: string) => `${environment.zone}/${id}`,
  deleteZone: (id: string) => `${environment.zone}/${id}`,
};

export const edgeNodeApiEndpoints = {
  createEdgeNode: `${environment.edgeNode}`,
  getEdgeNodes: `${environment.edgeNode}`,
  getEdgeNodeById: (id: string) => `${environment.edgeNode}/${id}`,
  getEdgeNodeByCode: (code: string) => `${environment.edgeNode}/by-code/${code}`,
  updateEdgeNode: (id: string) => `${environment.edgeNode}/${id}`,
  deleteEdgeNode: (id: string) => `${environment.edgeNode}/${id}`,
};

export const cameraApiEndpoints = {
  createCamera: `${environment.camera}`,
  getCameras: `${environment.camera}`,
  getCameraById: (id: string) => `${environment.camera}/${id}`,
  getCameraByCode: (code: string) => `${environment.camera}/by-code/${code}`,
  getCamerasByZone: (zoneId: string) => `${environment.camera}/by-zone/${zoneId}`,
  getCamerasByEdgeNode: (id: string) => `${environment.camera}/by-edge-node/${id}`,
  updateCamera: (id: string) => `${environment.camera}/${id}`,
  deleteCamera: (id: string) => `${environment.camera}/${id}`,
};

export const alertApiEndpoints = {
  getAlerts: `${environment.alert}`,
  getAlertById: (id: string) => `${environment.alert}/${id}`,
  acknowledgeAlert: (id: string) => `${environment.alert}/${id}/acknowledge`,
  getPreferences: `${environment.alert}/preferences`,
  updatePreferences: `${environment.alert}/preferences`,
  sendTestAlert: `${environment.alert}/test`,
  getHistory: `${environment.alert}/history`,
};

export const annotationApiEndpoints = {
  createTask: `${environment.annotation}/tasks`,
  getTasks: `${environment.annotation}/tasks`,
  getTaskById: (id: string) => `${environment.annotation}/tasks/${id}`,
  assignTask: (id: string) => `${environment.annotation}/tasks/${id}/assign`,
  exportTask: (id: string) => `${environment.annotation}/tasks/${id}/export`,
  reviewTask: (id: string) => `${environment.annotation}/tasks/${id}/review`,
  getStats: `${environment.annotation}/stats`,
  importAnnotations: `${environment.annotation}/import`,
};

export const datasetApiEndpoints = {
  createDataset: `${environment.dataset}`,
  getDatasets: `${environment.dataset}`,
  getDatasetById: (id: string) => `${environment.dataset}/${id}`,
  updateDataset: (id: string) => `${environment.dataset}/${id}`,
  deleteDataset: (id: string) => `${environment.dataset}/${id}`,
};

export const incidentApiEndpoints = {
  createIncident: `${environment.incident}`,
  getIncidents: `${environment.incident}`,
  searchIncidents: `${environment.incident}/search`,
  getIncidentById: (id: string) => `${environment.incident}/${id}`,
  updateIncident: (id: string) => `${environment.incident}/${id}`,
  deleteIncident: (id: string) => `${environment.incident}/${id}`,
  acknowledgeIncident: (id: string) => `${environment.incident}/${id}/acknowledge`,
  assignIncident: (id: string) => `${environment.incident}/${id}/assign`,
  resolveIncident: (id: string) => `${environment.incident}/${id}/resolve`,
  escalateIncident: (id: string) => `${environment.incident}/${id}/escalate`,
  markFalsePositive: (id: string) => `${environment.incident}/${id}/false-positive`,
  getTimeline: (id: string) => `${environment.incident}/${id}/timeline`,
  addNote: (id: string) => `${environment.incident}/${id}/notes`,
  getNotes: (id: string) => `${environment.incident}/${id}/notes`,
  getEvidence: (id: string) => `${environment.incident}/${id}/evidence`,
  uploadEvidence: (id: string) => `${environment.incident}/${id}/evidence`,
};

export const mlModelApiEndpoints = {
  uploadModel: `${environment.mlModel}/upload`,
  getModels: `${environment.mlModel}`,
  getModelVersions: `${environment.mlModel}/versions`,
  getModelById: (id: string) => `${environment.mlModel}/${id}`,
  deployModel: (id: string) => `${environment.mlModel}/${id}/deploy`,
  rollbackModel: (id: string) => `${environment.mlModel}/${id}/rollback`,
  getModelMetrics: (id: string) => `${environment.mlModel}/${id}/metrics`,
  getDeploymentHistory: (id: string) => `${environment.mlModel}/${id}/deployments`,
  validateModel: (id: string) => `${environment.mlModel}/${id}/validate`,
  promoteModel: (id: string) => `${environment.mlModel}/${id}/promote`,
};

export const trainingApiEndpoints = {
  submitJob: `${environment.training}/jobs`,
  getJobs: `${environment.training}/jobs`,
  getJobById: (id: string) => `${environment.training}/jobs/${id}`,
  cancelJob: (id: string) => `${environment.training}/jobs/${id}`,
  getJobLogs: (id: string) => `${environment.training}/jobs/${id}/logs`,
  getJobMetrics: (id: string) => `${environment.training}/jobs/${id}/metrics`,
  resumeJob: (id: string) => `${environment.training}/jobs/${id}/resume`,
  getDatasets: `${environment.training}/datasets`,
  uploadDataset: `${environment.training}/datasets`,
  getExperiments: `${environment.training}/experiments`,
};

export const userApiEndpoints = {
  createUser: `${environment.user}`,
  getUsers: `${environment.user}`,
  getUserById: (id: string) => `${environment.user}/${id}`,
  updateUser: (id: string) => `${environment.user}/${id}`,
  deleteUser: (id: string) => `${environment.user}/${id}`,
};

export const notificationApiEndpoints = {
  createNotification: `${environment.notification}`,
  getNotifications: `${environment.notification}`,
  getNotificationById: (id: string) => `${environment.notification}/${id}`,
  updateNotification: (id: string) => `${environment.notification}/${id}`,
  deleteNotification: (id: string) => `${environment.notification}/${id}`,
};

export const chatbotApiEndpoints = {
  chat: `${environment.analytics}/chatbot/chat`,
  getSession: (id: string) => `${environment.analytics}/chatbot/sessions/${id}`,
  clearSession: (id: string) => `${environment.analytics}/chatbot/sessions/${id}`,
};

export const analyticsApiEndpoints = {
  dashboard: `${environment.analytics}/dashboard/`,
  incidentStats: `${environment.analytics}/incidents/stats`,
  incidentTrends: `${environment.analytics}/incidents/trends`,
  responseTimes: `${environment.analytics}/incidents/response-times`,
  cameraPerformance: `${environment.analytics}/cameras/performance`,
  heatmap: `${environment.analytics}/heatmap/`,
  surveillanceSummary: `${environment.analytics}/surveillance/summary`,
  surveillanceLatest: `${environment.analytics}/surveillance/latest`,
  surveillanceCrowd: `${environment.analytics}/surveillance/crowd`,
  surveillanceTraffic: `${environment.analytics}/surveillance/traffic`,
  generateReport: `${environment.analytics}/reports/generate`,
  vlmAnalyses: `${environment.analytics}/vlm/analyses`,
  vlmAnalysis: (id: string) => `${environment.analytics}/vlm/analyses/${id}`,
  vlmSummary: `${environment.analytics}/vlm/summary`,
};

export const vlmApiEndpoints = {
  getAnalyses: `${environment.analytics}/vlm/analyses`,
  getAnalysis: (id: string) => `${environment.analytics}/vlm/analyses/${id}`,
  getSummary: `${environment.analytics}/vlm/summary`,
};

export const deviceTokenApiEndpoints = {
  register: `${environment.deviceToken}`,
  unregister: `${environment.deviceToken}`,
};

export const settingsApiEndpoints = {
  getSettings: `${environment.settings}`,
  updateSettings: `${environment.settings}`,
};
