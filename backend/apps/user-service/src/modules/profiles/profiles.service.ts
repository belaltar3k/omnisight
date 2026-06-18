import {
  ConflictException,
  Injectable,
  NotFoundException,
} from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { HttpService } from '@nestjs/axios';
import { ConfigService } from '@nestjs/config';
import { firstValueFrom, timeout } from 'rxjs';

import { UserProfile } from './entities/user-profile.entity';
import { ZoneAssignment } from '../zone-assignments/entities/zone-assignment.entity';
import { CreateProfileDto } from './dto/create-profile.dto';
import { UpdateProfileDto } from './dto/update-profile.dto';

@Injectable()
export class ProfilesService {
  private readonly authServiceUrl: string;
  private readonly cameraServiceUrl: string;

  constructor(
    @InjectRepository(UserProfile)
    private readonly profileRepository: Repository<UserProfile>,

    @InjectRepository(ZoneAssignment)
    private readonly zoneAssignmentRepository: Repository<ZoneAssignment>,

    private readonly httpService: HttpService,

    // ✅ Fixed: URLs come from env, not hardcoded localhost
    private readonly configService: ConfigService,
  ) {
    this.authServiceUrl = this.configService.get<string>('AUTH_SERVICE_URL') ?? 'http://localhost:3001';
    this.cameraServiceUrl = this.configService.get<string>('CAMERA_SERVICE_URL') ?? 'http://localhost:3012';
  }

  // ─── Create ────────────────────────────────────────────────────────────────

  async create(dto: CreateProfileDto) {
    // Verify the auth user actually exists in auth-service
    try {
      await firstValueFrom(
        this.httpService
          .get(`${this.authServiceUrl}/auth/users/${dto.authUserId}`)
          .pipe(timeout(5000)), // ✅ Added: 5s timeout so one bad call doesn't hang forever
      );
    } catch {
      throw new NotFoundException('Auth user does not exist');
    }

    // Check profile doesn't already exist
    const exists = await this.profileRepository.findOne({
      where: { authUserId: dto.authUserId },
    });
    if (exists) {
      throw new ConflictException('Profile already exists for this user');
    }

    // Check employee code uniqueness
    if (dto.employeeCode) {
      const employeeExists = await this.profileRepository.findOne({
        where: { employeeCode: dto.employeeCode },
      });
      if (employeeExists) {
        throw new ConflictException('Employee code already exists');
      }
    }

    const profile = this.profileRepository.create(dto);
    return this.profileRepository.save(profile);
  }

  // ─── Read All ──────────────────────────────────────────────────────────────

  async findAll() {
    return this.profileRepository.find({
      order: { createdAt: 'DESC' },
    });
  }

  // ─── Read One by authUserId ────────────────────────────────────────────────

  async findByAuthUserId(authUserId: string) {
    const profile = await this.profileRepository.findOne({
      where: { authUserId },
    });

    // ✅ Fixed: was commented out — now throws proper 404 instead of returning null
    if (!profile) {
      throw new NotFoundException('Profile not found');
    }

    return profile;
  }

  // ─── Update ────────────────────────────────────────────────────────────────

  // ✅ New: PATCH endpoint support
  async update(authUserId: string, dto: UpdateProfileDto) {
    const profile = await this.findByAuthUserId(authUserId);

    // If updating employeeCode, check it's not taken by someone else
    if (dto.employeeCode && dto.employeeCode !== profile.employeeCode) {
      const employeeExists = await this.profileRepository.findOne({
        where: { employeeCode: dto.employeeCode },
      });
      if (employeeExists) {
        throw new ConflictException('Employee code already exists');
      }
    }

    Object.assign(profile, dto);
    return this.profileRepository.save(profile);
  }

  // ─── Full Profile (profile + zone assignments enriched) ───────────────────

  async findFullProfile(authUserId: string) {
    const profile = await this.findByAuthUserId(authUserId);

    const assignments = await this.zoneAssignmentRepository.find({
      where: { authUserId },
      order: { assignedAt: 'DESC' },
    });

    // ✅ Improved: each zone fetch has a 5s timeout so one dead zone won't hang all
    const assignmentsWithZones = await Promise.all(
      assignments.map(async (assignment) => {
        try {
          const response = await firstValueFrom(
            this.httpService
              .get(`${this.cameraServiceUrl}/zones/${assignment.zoneId}`)
              .pipe(timeout(5000)),
          );

          return {
            id: assignment.id,
            authUserId: assignment.authUserId,
            zoneId: assignment.zoneId,
            notes: assignment.notes,
            assignedAt: assignment.assignedAt,
            status: 'active',
            zone: response.data,
          };
        } catch {
          return {
            id: assignment.id,
            authUserId: assignment.authUserId,
            zoneId: assignment.zoneId,
            notes: assignment.notes,
            assignedAt: assignment.assignedAt,
            status: 'orphaned',
            zone: null,
            message: 'Assigned zone no longer exists',
          };
        }
      }),
    );

    return {
      profile,
      assignments: assignmentsWithZones,
    };
  }
}
