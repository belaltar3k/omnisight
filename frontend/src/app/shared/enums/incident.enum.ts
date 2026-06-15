export enum IncidentStatus {
  New = 'new',
  VlmVerifying = 'vlm_verifying',
  Acknowledged = 'acknowledged',
  Investigating = 'investigating',
  Dispatched = 'dispatched',
  OnScene = 'on_scene',
  Resolved = 'resolved',
  FalsePositive = 'false_positive',
  Escalated = 'escalated',
}

export enum CrimeType {
  Assault = 'assault',
  Arrest = 'arrest',
  Arson = 'arson',
  Vandalism = 'vandalism',
  Fighting = 'fighting',
  Robbery = 'robbery',
  Burglary = 'burglary',
  Shooting = 'shooting',
  Shoplifting = 'shoplifting',
  Stealing = 'stealing',
}

export enum Priority {
  Critical = 'critical',
  High = 'high',
  Medium = 'medium',
  Low = 'low',
}
