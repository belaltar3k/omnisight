import {
  BadRequestException,
  Inject,
  Injectable,
  Logger,
  NotFoundException,
  OnModuleInit,
  UnauthorizedException,
} from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository, IsNull } from 'typeorm';
import { HttpService } from '@nestjs/axios';
import { ConfigService } from '@nestjs/config';
import { JwtService } from '@nestjs/jwt';
import { ClientKafka } from '@nestjs/microservices';
import { firstValueFrom, timeout } from 'rxjs';


import { Incident, CrimeType, IncidentStatus, IncidentPriority } from '../entities/incident.entity';
import { IncidentNote } from '../entities/incident-note.entity';
import { IncidentTimeline } from '../entities/incident-timeline.entity';

import { EdgeSyncDto } from './dto/edge-sync.dto';
import { EdgeClassifyDto } from './dto/edge-classify.dto';
import { CreateIncidentDto } from './dto/create-incident.dto';
import { UpdateIncidentDto } from './dto/update-incident.dto';
import { AssignIncidentDto } from './dto/assign-incident.dto';
import { ResolveIncidentDto } from './dto/resolve-incident.dto';
import { FalsePositiveDto } from './dto/false-positive.dto';
import { AddNoteDto } from './dto/add-note.dto';
import { FilterIncidentsDto } from './dto/filter-incidents.dto';

@Injectable()
export class IncidentsService implements OnModuleInit {
  private readonly logger = new Logger(IncidentsService.name);

  private readonly cameraServiceUrl: string;
  private readonly edgeSyncSecret: string;
  private readonly cameraServiceToken: string;

  constructor(
    @InjectRepository(Incident)
    private readonly incidentRepository: Repository<Incident>,

    @InjectRepository(IncidentNote)
    private readonly noteRepository: Repository<IncidentNote>,

    @InjectRepository(IncidentTimeline)
    private readonly timelineRepository: Repository<IncidentTimeline>,

    private readonly httpService: HttpService,
    private readonly jwtService: JwtService,
    configService: ConfigService,

    @Inject('KAFKA_SERVICE')
    private readonly kafkaClient: ClientKafka,
  ) {
    this.cameraServiceUrl =
      configService.get<string>('CAMERA_SERVICE_URL') ?? 'http://localhost:3002';
    this.edgeSyncSecret =
      configService.get<string>('EDGE_SYNC_SECRET') ?? '';
    this.cameraServiceToken = this.jwtService.sign(
      { sub: 'incident-service', email: 'incident-service@internal', role: 'incident_service' },
      { expiresIn: '10y' },
    );
  }

  async onModuleInit() {
    await this.kafkaClient.connect();
    this.logger.log('Kafka producer connected');
  }

  // ─── Helper: calculate priority from crime type and confidence ─────────────

  private calculatePriority(crimeType: string, confidence: number): IncidentPriority {
    if (['assault', 'fire', 'weapon'].includes(crimeType)) {
      return IncidentPriority.CRITICAL;
    }
    if (confidence > 0.9) {
      return IncidentPriority.HIGH;
    }
    if (['theft', 'vandalism'].includes(crimeType)) {
      return IncidentPriority.HIGH;
    }
    return IncidentPriority.MEDIUM;
  }

  // ─── Helper: record timeline entry ────────────────────────────────────────

  private async addTimeline(
    incidentId: string,
    action: string,
    fromStatus: string | null,
    toStatus: string | null,
    performedBy: string | null,
    notes?: string,
  ) {
    const entry = this.timelineRepository.create({
      incidentId,
      action,
      fromStatus: fromStatus ?? undefined,
      toStatus: toStatus ?? undefined,
      performedBy: performedBy ?? undefined,
      notes,
    });
    await this.timelineRepository.save(entry);
  }

  // ─── Helper: verify secret for edge endpoints ──────────────────────────────

  verifyEdgeSecret(secret: string) {
    if (secret !== this.edgeSyncSecret) {
      throw new UnauthorizedException('Invalid edge secret');
    }
  }

  // ══════════════════════════════════════════════════════════════════════════
  // EDGE SYNC — Step 1: abnormal detection
  // ══════════════════════════════════════════════════════════════════════════

  async syncFromEdge(dto: EdgeSyncDto) {
    const createdIncidents: string[] = [];
    const skipped: string[] = [];

    // Resolve the edge node once for the whole batch — it is the same for every detection
    let edgeNode: any;
    try {
      const response = await firstValueFrom(
        this.httpService
          .get(`${this.cameraServiceUrl}/edge-nodes/by-code/${dto.edgeNodeCode}`, {
            headers: { authorization: `Bearer ${this.cameraServiceToken}` },
          })
          .pipe(timeout(5000)),
      );
      edgeNode = response.data;
    } catch (error: any) {
      this.logger.error(
        `Edge node "${dto.edgeNodeCode}" not found or camera service unreachable: ${error.message}`,
      );
      return { success: false, created: 0, skipped: dto.detections.length, incidentIds: [] };
    }

    for (const detection of dto.detections) {
      if (detection.crimeType === 'normal') {
        this.logger.debug(`Skipping normal detection trackId=${detection.trackId}`);
        skipped.push(detection.trackId);
        continue;
      }

      if (detection.confidence < 0.75) {
        this.logger.debug(
          `Skipping low-confidence detection trackId=${detection.trackId} confidence=${detection.confidence}`,
        );
        skipped.push(detection.trackId);
        continue;
      }

      // Look up camera by code to get cameraId and zoneId
      let camera: any;
      try {
        const response = await firstValueFrom(
          this.httpService
            .get(`${this.cameraServiceUrl}/cameras/by-code/${detection.cameraCode}`, {
              headers: { authorization: `Bearer ${this.cameraServiceToken}` },
            })
            .pipe(timeout(5000)),
        );
        camera = response.data;
      } catch (error: any) {
        this.logger.warn(
          `Camera "${detection.cameraCode}" not found, skipping trackId=${detection.trackId}: ${error.message}`,
        );
        skipped.push(detection.trackId);
        continue;
      }

      // Verify camera belongs to this edge node — reject spoofed reports
      if (camera.edgeNodeId !== edgeNode.id) {
        this.logger.warn(
          `Camera "${detection.cameraCode}" belongs to edge node ${camera.edgeNodeId}, ` +
          `not "${dto.edgeNodeCode}" (${edgeNode.id}). Skipping trackId=${detection.trackId}`,
        );
        skipped.push(detection.trackId);
        continue;
      }

      // Deduplicate by trackId
      const existing = await this.incidentRepository.findOne({
        where: { trackId: detection.trackId },
      });
      if (existing) {
        this.logger.debug(`Duplicate trackId=${detection.trackId}, skipping`);
        skipped.push(detection.trackId);
        continue;
      }

      const incident = this.incidentRepository.create({
        cameraId:     camera.id,
        cameraCode:   detection.cameraCode,
        zoneId:       camera.zoneId,
        edgeNodeId:   edgeNode.id,
        trackId:      detection.trackId,
        crimeType:    CrimeType.ABNORMAL,
        confidence:   detection.confidence,
        status:       IncidentStatus.DETECTING,
        priority:     this.calculatePriority(detection.crimeType, detection.confidence),
        detectedAt:   new Date(detection.detectedAt),
        videoUrl:     detection.videoUrl,
        thumbnailUrl: detection.thumbnailUrl,
        modelVersion: detection.modelVersion,
        aiMetadata:   detection.aiMetadata,
      });

      const saved = await this.incidentRepository.save(incident);

      await this.addTimeline(
        saved.id,
        'created',
        null,
        IncidentStatus.DETECTING,
        null,
        `Abnormal activity detected by edge node ${dto.edgeNodeCode}`,
      );

      // Emit immediately on detection — don't wait for classification
      this.kafkaClient.emit('sentinel.incident.new', {
        incidentId: saved.id,
        cameraId: saved.cameraId,
        cameraCode: saved.cameraCode,
        zoneId: saved.zoneId,
        crimeType: detection.crimeType,
        priority: saved.priority,
        confidence: saved.confidence,
        detectedAt: saved.detectedAt,
        edgeNodeCode: dto.edgeNodeCode,
      });

      this.logger.log(`Incident created id=${saved.id} trackId=${detection.trackId}`);
      createdIncidents.push(saved.id);
    }

    return {
      success: true,
      created: createdIncidents.length,
      skipped: skipped.length,
      incidentIds: createdIncidents,
    };
  }

  // ══════════════════════════════════════════════════════════════════════════
  // EDGE CLASSIFY — Step 2: crime type classification
  // ══════════════════════════════════════════════════════════════════════════

  async classifyFromEdge(dto: EdgeClassifyDto) {
    // Find incident by trackId
    const incident = await this.incidentRepository.findOne({
      where: { trackId: dto.trackId },
    });

    if (!incident) {
      throw new NotFoundException(`No incident found with trackId: ${dto.trackId}`);
    }

    // Only classify incidents in DETECTING status. Guarding on status (not crimeType)
    // prevents accidentally pushing a RESOLVED incident back to NEW.
    if (incident.status !== IncidentStatus.DETECTING) {
      return {
        message: 'Incident already classified',
        incidentId: incident.id,
        crimeType: incident.crimeType,
        status: incident.status,
      };
    }

    const oldStatus    = incident.status;
    const newCrimeType = dto.crimeType; // already validated as CrimeType by DTO
    const newPriority  = this.calculatePriority(dto.crimeType, dto.confidence);

    // Update incident
    incident.crimeType  = newCrimeType;
    incident.confidence = dto.confidence;
    incident.priority   = newPriority;
    incident.status     = IncidentStatus.NEW; // now ready for guards

    await this.incidentRepository.save(incident);

    // Record timeline
    await this.addTimeline(
      incident.id,
      'classified',
      oldStatus,
      IncidentStatus.NEW,
      null,
      `Classified as ${dto.crimeType} with confidence ${dto.confidence}`,
    );

    return {
      success: true,
      incidentId: incident.id,
      crimeType: newCrimeType,
      priority: newPriority,
      status: IncidentStatus.NEW,
    };
  }

  // ══════════════════════════════════════════════════════════════════════════
  // CRUD
  // ══════════════════════════════════════════════════════════════════════════

  async create(dto: CreateIncidentDto, userId: string) {
    const priority = this.calculatePriority(dto.crimeType, dto.confidence);

    const incident = this.incidentRepository.create({
      ...dto,
      detectedAt: new Date(dto.detectedAt),
      priority,
      status: IncidentStatus.NEW,
    });

    const saved = await this.incidentRepository.save(incident);

    await this.addTimeline(saved.id, 'created', null, IncidentStatus.NEW, userId);

    return saved;
  }

  async findAll(filters: FilterIncidentsDto) {
    const query = this.incidentRepository.createQueryBuilder('incident')
      .where('incident.deleted_at IS NULL');

    if (filters.crimeType) {
      query.andWhere('incident.crime_type = :crimeType', { crimeType: filters.crimeType });
    }
    if (filters.status) {
      query.andWhere('incident.status = :status', { status: filters.status });
    }
    if (filters.priority) {
      query.andWhere('incident.priority = :priority', { priority: filters.priority });
    }
    if (filters.zoneId) {
      query.andWhere('incident.zone_id = :zoneId', { zoneId: filters.zoneId });
    }
    if (filters.cameraId) {
      query.andWhere('incident.camera_id = :cameraId', { cameraId: filters.cameraId });
    }
    if (filters.assignedTo) {
      query.andWhere('incident.assigned_to = :assignedTo', { assignedTo: filters.assignedTo });
    }
    if (filters.dateFrom) {
      query.andWhere('incident.detected_at >= :dateFrom', { dateFrom: filters.dateFrom });
    }
    if (filters.dateTo) {
      query.andWhere('incident.detected_at <= :dateTo', { dateTo: filters.dateTo });
    }
    if (filters.minConfidence) {
      query.andWhere('incident.confidence >= :minConfidence', { minConfidence: filters.minConfidence });
    }
    if (filters.isFalsePositive !== undefined) {
      query.andWhere('incident.is_false_positive = :isFalsePositive', { isFalsePositive: filters.isFalsePositive });
    }

    const sortBy    = filters.sortBy ?? 'detectedAt';
    const sortOrder = (filters.sortOrder?.toUpperCase() ?? 'DESC') as 'ASC' | 'DESC';
    query.orderBy(`incident.${sortBy}`, sortOrder);

    const page  = filters.page ?? 1;
    const limit = filters.limit ?? 20;
    query.skip((page - 1) * limit).take(limit);

    const [data, total] = await query.getManyAndCount();

    return {
      data,
      total,
      page,
      limit,
      totalPages: Math.ceil(total / limit),
    };
  }

  async findOne(id: string) {
    const incident = await this.incidentRepository.findOne({
      where: { id, deletedAt: IsNull() },
      relations: ['notes', 'timeline'],
    });

    if (!incident) {
      throw new NotFoundException('Incident not found');
    }

    return incident;
  }

  async update(id: string, dto: UpdateIncidentDto, userId: string) {
    const incident = await this.findOne(id);
    Object.assign(incident, dto);
    const saved = await this.incidentRepository.save(incident);
    await this.addTimeline(id, 'updated', null, null, userId);
    return saved;
  }

  async remove(id: string, userId: string) {
    const incident = await this.findOne(id);
    incident.deletedAt = new Date();
    await this.incidentRepository.save(incident);
    await this.addTimeline(id, 'deleted', incident.status, null, userId);
    return { message: 'Incident deleted successfully' };
  }

  // ══════════════════════════════════════════════════════════════════════════
  // ACTIONS
  // ══════════════════════════════════════════════════════════════════════════

  async assign(id: string, dto: AssignIncidentDto, userId: string) {
    const incident = await this.findOne(id);

    if (incident.status === IncidentStatus.RESOLVED ||
        incident.status === IncidentStatus.FALSE_POSITIVE) {
      throw new BadRequestException('Cannot assign a closed incident');
    }

    incident.assignedTo  = dto.assignedTo;
    incident.assignedAt  = new Date();

    await this.incidentRepository.save(incident);
    await this.addTimeline(id, 'assigned', incident.status, incident.status, userId, dto.notes);

    return { message: 'Incident assigned successfully', assignedTo: dto.assignedTo };
  }

  async acknowledge(id: string, userId: string) {
    const incident = await this.findOne(id);
    this.assertTransition(incident.status, IncidentStatus.NEW, 'acknowledge');

    const oldStatus = incident.status;
    incident.status          = IncidentStatus.ACKNOWLEDGED;
    incident.acknowledgedBy  = userId;
    incident.acknowledgedAt  = new Date();

    await this.incidentRepository.save(incident);
    await this.addTimeline(id, 'acknowledged', oldStatus, IncidentStatus.ACKNOWLEDGED, userId);

    return { message: 'Incident acknowledged' };
  }

  async investigate(id: string, userId: string) {
    const incident = await this.findOne(id);
    this.assertTransition(incident.status, IncidentStatus.ACKNOWLEDGED, 'investigate');

    const oldStatus  = incident.status;
    incident.status  = IncidentStatus.INVESTIGATING;

    await this.incidentRepository.save(incident);
    await this.addTimeline(id, 'investigating', oldStatus, IncidentStatus.INVESTIGATING, userId);

    return { message: 'Incident under investigation' };
  }

  async dispatch(id: string, userId: string) {
    const incident = await this.findOne(id);
    this.assertTransition(incident.status, IncidentStatus.INVESTIGATING, 'dispatch');

    const oldStatus  = incident.status;
    incident.status  = IncidentStatus.DISPATCHED;

    await this.incidentRepository.save(incident);
    await this.addTimeline(id, 'dispatched', oldStatus, IncidentStatus.DISPATCHED, userId);

    this.kafkaClient.emit('sentinel.incident.status_changed', {
      incidentId: incident.id,
      cameraCode: incident.cameraCode,
      zoneId: incident.zoneId,
      fromStatus: oldStatus,
      toStatus: IncidentStatus.DISPATCHED,
      assignedTo: incident.assignedTo,
      performedBy: userId,
    });

    return { message: 'Guard dispatched to scene' };
  }

  async onScene(id: string, userId: string) {
    const incident = await this.findOne(id);
    this.assertTransition(incident.status, IncidentStatus.DISPATCHED, 'on-scene');

    const oldStatus  = incident.status;
    incident.status  = IncidentStatus.ON_SCENE;

    await this.incidentRepository.save(incident);
    await this.addTimeline(id, 'on_scene', oldStatus, IncidentStatus.ON_SCENE, userId);

    return { message: 'Guard arrived on scene' };
  }

  async resolve(id: string, dto: ResolveIncidentDto, userId: string) {
    const incident = await this.findOne(id);

    if (incident.status === IncidentStatus.RESOLVED ||
        incident.status === IncidentStatus.FALSE_POSITIVE) {
      throw new BadRequestException('Incident is already closed');
    }

    const oldStatus           = incident.status;
    incident.status           = IncidentStatus.RESOLVED;
    incident.resolvedBy       = userId;
    incident.resolvedAt       = new Date();
    incident.resolutionNotes  = dto.resolutionNotes ?? '';

    await this.incidentRepository.save(incident);
    await this.addTimeline(id, 'resolved', oldStatus, IncidentStatus.RESOLVED, userId, dto.resolutionNotes);

    this.kafkaClient.emit('sentinel.incident.status_changed', {
      incidentId: incident.id,
      cameraCode: incident.cameraCode,
      zoneId: incident.zoneId,
      fromStatus: oldStatus,
      toStatus: IncidentStatus.RESOLVED,
      performedBy: userId,
    });

    return { message: 'Incident resolved successfully' };
  }

  async markFalsePositive(id: string, dto: FalsePositiveDto, userId: string) {
    const incident = await this.findOne(id);

    if (incident.status === IncidentStatus.RESOLVED) {
      throw new BadRequestException('Cannot mark a resolved incident as false positive');
    }

    const oldStatus                = incident.status;
    incident.status                = IncidentStatus.FALSE_POSITIVE;
    incident.isFalsePositive       = true;
    incident.falsePositiveReason   = dto.reason;

    await this.incidentRepository.save(incident);
    await this.addTimeline(id, 'false_positive', oldStatus, IncidentStatus.FALSE_POSITIVE, userId, dto.reason);

    return { message: 'Incident marked as false positive' };
  }

  // ══════════════════════════════════════════════════════════════════════════
  // NOTES
  // ══════════════════════════════════════════════════════════════════════════

  async addNote(id: string, dto: AddNoteDto, userId: string) {
    await this.findOne(id); // verify incident exists

    const note = this.noteRepository.create({
      incidentId: id,
      authorId:   userId,
      content:    dto.content,
    });

    return this.noteRepository.save(note);
  }

  async getNotes(id: string) {
    await this.findOne(id);
    return this.noteRepository.find({
      where: { incidentId: id },
      order: { createdAt: 'ASC' },
    });
  }

  // ══════════════════════════════════════════════════════════════════════════
  // TIMELINE
  // ══════════════════════════════════════════════════════════════════════════

  async getTimeline(id: string) {
    await this.findOne(id);
    return this.timelineRepository.find({
      where: { incidentId: id },
      order: { createdAt: 'ASC' },
    });
  }

  // ─── Helper: enforce status transition rules ───────────────────────────────

  private assertTransition(
    currentStatus: IncidentStatus,
    requiredStatus: IncidentStatus,
    action: string,
  ) {
    if (currentStatus !== requiredStatus) {
      throw new BadRequestException(
        `Cannot ${action} incident with status "${currentStatus}". Required status: "${requiredStatus}"`,
      );
    }
  }
}
