import { ConflictException, Injectable } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Zone } from './entities/zone.entity';
import { Repository } from 'typeorm';
import { CreateZoneDto } from './dto/create-zone.dto';
import { NotFoundException } from '@nestjs/common';
import { UpdateZoneDto } from './dto/update-zone.dto';
import { BadRequestException } from '@nestjs/common';
import { Camera } from '../cameras/entities/camera.entity';

@Injectable()
export class ZonesService {
  constructor(
  @InjectRepository(Zone)
  private readonly zoneRepository: Repository<Zone>,

  @InjectRepository(Camera)
  private readonly cameraRepository: Repository<Camera>,
) {}

  async create(dto: CreateZoneDto) {
    const exists = await this.zoneRepository.findOne({
      where: { name: dto.name },
    });

    if (exists) {
      throw new ConflictException('Zone name already exists');
    }

    const zone = this.zoneRepository.create(dto);
    return this.zoneRepository.save(zone);
  }

  
  async findAll() {
    return this.zoneRepository.find({
      order: { createdAt: 'DESC' },
    });
  }

  async findOne(id: string) {
  const zone = await this.zoneRepository.findOne({
    where: { id },
  });

  if (!zone) {
    throw new NotFoundException('Zone not found');
  }

  return zone;
}

async update(id: string, dto: UpdateZoneDto) {
  const zone = await this.findOne(id);

  Object.assign(zone, dto);

  return this.zoneRepository.save(zone);
}

async remove(id: string) {
  const zone = await this.findOne(id);

  const camerasCount = await this.cameraRepository.count({
    where: { zoneId: id },
  });

  if (camerasCount > 0) {
    throw new BadRequestException(
      'Cannot delete zone because it has cameras assigned to it',
    );
  }

  await this.zoneRepository.remove(zone);

  return {
    message: 'Zone deleted successfully',
  };
}
}