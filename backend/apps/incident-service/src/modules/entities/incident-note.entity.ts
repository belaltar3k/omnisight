import {
  Column,
  CreateDateColumn,
  Entity,
  JoinColumn,
  ManyToOne,
  PrimaryGeneratedColumn,
} from 'typeorm';
import { Incident } from './incident.entity';

@Entity('incident_notes')
export class IncidentNote {
  @PrimaryGeneratedColumn('uuid')
  id!: string;

  @Column({ name: 'incident_id' })
  incidentId!: string;

  @ManyToOne(() => Incident, (incident) => incident.notes)
  @JoinColumn({ name: 'incident_id' })
  incident!: Incident;

  @Column({ name: 'author_id' })
  authorId!: string;

  @Column({ type: 'text' })
  content!: string;

  @CreateDateColumn({ name: 'created_at' })
  createdAt!: Date;
}
