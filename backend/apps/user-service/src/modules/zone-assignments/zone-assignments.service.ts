import {
  ConflictException,
  Injectable,
  NotFoundException,
} from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository, In } from 'typeorm';
import { HttpService } from '@nestjs/axios';
import { ConfigService } from '@nestjs/config';
import { JwtService } from '@nestjs/jwt';
import { firstValueFrom, timeout } from 'rxjs';

import { ZoneAssignment } from './entities/zone-assignment.entity';
import { UserProfile } from '../profiles/entities/user-profile.entity';
import { CreateZoneAssignmentDto } from './dto/create-zone-assignment.dto';
import { ReassignZoneDto } from './dto/reassign-zone.dto';

@Injectable()
export class ZoneAssignmentsService {
  private readonly authServiceUrl: string;
  private readonly cameraServiceUrl: string;
  private readonly cameraServiceToken: string;

  constructor(
    @InjectRepository(ZoneAssignment)
    private readonly zoneAssignmentRepository: Repository<ZoneAssignment>,

    @InjectRepository(UserProfile)
    private readonly profileRepository: Repository<UserProfile>,

    private readonly httpService: HttpService,
    private readonly configService: ConfigService,
    private readonly jwtService: JwtService,
  ) {
    this.authServiceUrl =
      this.configService.get<string>('AUTH_SERVICE_URL') ?? 'http://localhost:3001';
    this.cameraServiceUrl =
      this.configService.get<string>('CAMERA_SERVICE_URL') ?? 'http://localhost:3012';
    this.cameraServiceToken = this.jwtService.sign(
      { sub: 'user-service', email: 'user-service@internal', role: 'user_service' },
      { expiresIn: '10y' },
    );
  }

  // ─── Create ────────────────────────────────────────────────────────────────

  async create(dto: CreateZoneAssignmentDto) {
    // ✅ Fixed: env URL + 5s timeout
    try {
      await firstValueFrom(
        this.httpService
          .get(`${this.authServiceUrl}/auth/users/${dto.authUserId}`)
          .pipe(timeout(5000)),
      );
    } catch {
      throw new NotFoundException('Auth user does not exist');
    }

    try {
      await firstValueFrom(
        this.httpService
          .get(`${this.cameraServiceUrl}/zones/${dto.zoneId}`, {
            headers: { authorization: `Bearer ${this.cameraServiceToken}` },
          })
          .pipe(timeout(5000)),
      );
    } catch {
      throw new NotFoundException('Zone does not exist');
    }

    // Check duplicate assignment
    const exists = await this.zoneAssignmentRepository.findOne({
      where: {
        authUserId: dto.authUserId,
        zoneId: dto.zoneId,
      },
    });

    if (exists) {
      throw new ConflictException('User is already assigned to this zone');
    }

    const assignment = this.zoneAssignmentRepository.create(dto);
    return this.zoneAssignmentRepository.save(assignment);
  }

  // ─── Read All ──────────────────────────────────────────────────────────────

  async findAll() {
    return this.zoneAssignmentRepository.find({
      order: { assignedAt: 'DESC' },
    });
  }

  // ─── Read by User ──────────────────────────────────────────────────────────

  async findByUser(authUserId: string) {
    return this.zoneAssignmentRepository.find({
      where: { authUserId },
      order: { assignedAt: 'DESC' },
    });
  }

  // ─── Read by Zone ──────────────────────────────────────────────────────────

  async findByZone(zoneId: string) {
    return this.zoneAssignmentRepository.find({
      where: { zoneId },
      order: { assignedAt: 'DESC' },
    });
  }

  // ─── Users by Zone (with profiles) ────────────────────────────────────────

  async findUsersByZone(zoneId: string) {
    const assignments = await this.zoneAssignmentRepository.find({
      where: { zoneId },
      order: { assignedAt: 'DESC' },
    });

    if (assignments.length === 0) {
      return [];
    }

    // ✅ Fixed: was N+1 queries (1 per assignment) — now ONE query using IN
    const authUserIds = assignments.map((a) => a.authUserId);
    const profiles = await this.profileRepository.find({
      where: { authUserId: In(authUserIds) },
    });

    // Build a map for O(1) lookup
    const profileMap = new Map(profiles.map((p) => [p.authUserId, p]));

    return assignments.map((assignment) => ({
      assignmentId: assignment.id,
      authUserId: assignment.authUserId,
      zoneId: assignment.zoneId,
      assignedAt: assignment.assignedAt,
      notes: assignment.notes,
      profile: profileMap.get(assignment.authUserId) ?? null,
    }));
  }

  // ─── Delete by ID ──────────────────────────────────────────────────────────

  async remove(id: string) {
    const assignment = await this.zoneAssignmentRepository.findOne({
      where: { id },
    });

    if (!assignment) {
      throw new NotFoundException('Zone assignment not found');
    }

    await this.zoneAssignmentRepository.remove(assignment);

    return { message: 'User unassigned from zone successfully' };
  }

  // ─── Delete by User + Zone ─────────────────────────────────────────────────

  async removeByUserAndZone(authUserId: string, zoneId: string) {
    const assignment = await this.zoneAssignmentRepository.findOne({
      where: { authUserId, zoneId },
    });

    if (!assignment) {
      throw new NotFoundException('Zone assignment not found');
    }

    await this.zoneAssignmentRepository.remove(assignment);

    return { message: 'User unassigned from zone successfully' };
  }

  // ─── Reassign to New Zone ──────────────────────────────────────────────────

  async reassign(id: string, dto: ReassignZoneDto) {
    const assignment = await this.zoneAssignmentRepository.findOne({
      where: { id },
    });

    if (!assignment) {
      throw new NotFoundException('Zone assignment not found');
    }

    try {
      await firstValueFrom(
        this.httpService
          .get(`${this.cameraServiceUrl}/zones/${dto.newZoneId}`, {
            headers: { authorization: `Bearer ${this.cameraServiceToken}` },
          })
          .pipe(timeout(5000)),
      );
    } catch {
      throw new NotFoundException('New zone does not exist');
    }

    // ✅ Fixed: check user isn't already assigned to the new zone
    const duplicate = await this.zoneAssignmentRepository.findOne({
      where: {
        authUserId: assignment.authUserId,
        zoneId: dto.newZoneId,
      },
    });

    if (duplicate) {
      throw new ConflictException('User is already assigned to the new zone');
    }

    assignment.zoneId = dto.newZoneId;
    return this.zoneAssignmentRepository.save(assignment);
  }
}
