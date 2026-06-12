import {
  Column,
  CreateDateColumn,
  Entity,
  OneToMany,
  PrimaryGeneratedColumn,
  UpdateDateColumn,
} from 'typeorm';
import { IncidentNote } from './incident-note.entity';
import { IncidentTimeline } from './incident-timeline.entity';

export enum CrimeType {
  ABNORMAL    = 'abnormal',
  ASSAULT     = 'assault',
  THEFT       = 'theft',
  SHOPLIFTING = 'shoplifting',
  VANDALISM   = 'vandalism',
  FIRE        = 'fire',
  WEAPON      = 'weapon',
  INTRUSION   = 'intrusion',
  ACCIDENT    = 'accident',
  SUSPICIOUS  = 'suspicious',
}

export enum IncidentStatus {
  DETECTING      = 'detecting',
  NEW            = 'new',
  ACKNOWLEDGED   = 'acknowledged',
  INVESTIGATING  = 'investigating',
  DISPATCHED     = 'dispatched',
  ON_SCENE       = 'on_scene',
  RESOLVED       = 'resolved',
  FALSE_POSITIVE = 'false_positive',
}

export enum IncidentPriority {
  CRITICAL = 'critical',
  HIGH     = 'high',
  MEDIUM   = 'medium',
  LOW      = 'low',
}

@Entity('incidents')
export class Incident {
  @PrimaryGeneratedColumn('uuid')
  id!: string;

  @Column({ name: 'camera_id' })
  cameraId!: string;

  @Column({ name: 'camera_code' })
  cameraCode!: string;

  @Column({ name: 'zone_id' })
  zoneId!: string;

  @Column({ name: 'edge_node_id' })
  edgeNodeId!: string;

  @Column({ name: 'track_id', nullable: true })
  trackId!: string;

  @Column({ name: 'crime_type', type: 'enum', enum: CrimeType, default: CrimeType.ABNORMAL })
  crimeType!: CrimeType;

  @Column({ type: 'float' })
  confidence!: number;

  @Column({ type: 'enum', enum: IncidentStatus, default: IncidentStatus.DETECTING })
  status!: IncidentStatus;

  @Column({ type: 'enum', enum: IncidentPriority, default: IncidentPriority.MEDIUM })
  priority!: IncidentPriority;

  @Column({ name: 'detected_at' })
  detectedAt!: Date;

  @Column({ name: 'model_version', nullable: true })
  modelVersion!: string;

  @Column({ name: 'video_url', nullable: true })
  videoUrl!: string;

  @Column({ name: 'thumbnail_url', nullable: true })
  thumbnailUrl!: string;

  @Column({ name: 'ai_metadata', type: 'jsonb', nullable: true })
  aiMetadata!: { keypoints?: any[]; boundingBoxes?: any[]; raw?: any };

  @Column({ name: 'assigned_to', nullable: true })
  assignedTo!: string;

  @Column({ name: 'assigned_at', nullable: true })
  assignedAt!: Date;

  @Column({ name: 'acknowledged_by', nullable: true })
  acknowledgedBy!: string;

  @Column({ name: 'acknowledged_at', nullable: true })
  acknowledgedAt!: Date;

  @Column({ name: 'resolved_by', nullable: true })
  resolvedBy!: string;

  @Column({ name: 'resolved_at', nullable: true })
  resolvedAt!: Date;

  @Column({ name: 'resolution_notes', nullable: true })
  resolutionNotes!: string;

  @Column({ name: 'is_false_positive', default: false })
  isFalsePositive!: boolean;

  @Column({ name: 'false_positive_reason', nullable: true })
  falsePositiveReason!: string;

  @Column({ name: 'deleted_at', nullable: true })
  deletedAt!: Date;

  @CreateDateColumn({ name: 'created_at' })
  createdAt!: Date;

  @UpdateDateColumn({ name: 'updated_at' })
  updatedAt!: Date;

  @OneToMany(() => IncidentNote, (note) => note.incident)
  notes!: IncidentNote[];

  @OneToMany(() => IncidentTimeline, (t) => t.incident)
  timeline!: IncidentTimeline[];
}
