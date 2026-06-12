import { Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { In, Repository } from 'typeorm';
import { DeviceToken } from './entities/device-token.entity';
import { RegisterTokenDto } from './dto/register-token.dto';

@Injectable()
export class DeviceTokensService {
  constructor(
    @InjectRepository(DeviceToken)
    private readonly repo: Repository<DeviceToken>,
  ) {}

  async register(userId: string, role: string, dto: RegisterTokenDto): Promise<DeviceToken> {
    // Upsert: same fcmToken → update userId/role; same userId → update token
    const existing = await this.repo.findOne({ where: { fcmToken: dto.fcmToken } });

    if (existing) {
      existing.userId = userId;
      existing.role = role;
      existing.deviceType = dto.deviceType ?? existing.deviceType;
      return this.repo.save(existing);
    }

    const token = this.repo.create({
      userId,
      role,
      fcmToken: dto.fcmToken,
      deviceType: dto.deviceType,
    });
    return this.repo.save(token);
  }

  async unregister(userId: string, fcmToken: string): Promise<{ message: string }> {
    await this.repo.delete({ userId, fcmToken });
    return { message: 'Device token unregistered' };
  }

  async findByRoles(roles: string[]): Promise<DeviceToken[]> {
    return this.repo
      .createQueryBuilder('t')
      .where('t.role IN (:...roles)', { roles })
      .getMany();
  }

  async findByUserId(userId: string): Promise<DeviceToken[]> {
    return this.repo.find({ where: { userId } });
  }

  async findByUserIds(userIds: string[]): Promise<DeviceToken[]> {
    if (userIds.length === 0) return [];
    return this.repo.find({ where: { userId: In(userIds) } });
  }
}
