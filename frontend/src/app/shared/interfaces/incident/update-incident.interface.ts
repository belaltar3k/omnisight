import { IncidentStatus, Priority } from '@shared/enums';

export interface IUpdateIncidentRequest {
  status?: IncidentStatus;
  priority?: Priority;
  assignedTo?: string;
  resolutionNotes?: string;
}

export interface IAssignIncidentRequest {
  assignedTo: string;
}

export interface IResolveIncidentRequest {
  resolutionNotes?: string;
}

export interface IMarkFalsePositiveRequest {
  falsePositiveReason?: string;
}

export interface IAddNoteRequest {
  content: string;
  noteType?: 'general' | 'update' | 'resolution' | 'handoff' | 'vlm_review';
}
