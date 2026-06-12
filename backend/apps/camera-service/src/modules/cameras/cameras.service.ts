import {
  ConflictException,
  Injectable,
  NotFoundException,
} from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';

import { Camera } from './entities/camera.entity';
import { Zone } from '../zones/entities/zone.entity';
import { EdgeNode } from '../edge-nodes/entities/edge-node.entity';
import { CreateCameraDto } from './dto/create-camera.dto';
import { UpdateCameraDto } from './dto/update-camera.dto';

@Injectable()
export class CamerasService {
  constructor(
    @InjectRepository(Camera)
    private readonly cameraRepository: Repository<Camera>,

    @InjectRepository(Zone)
    private readonly zoneRepository: Repository<Zone>,

    @InjectRepository(EdgeNode)
    private readonly edgeNodeRepository: Repository<EdgeNode>,
  ) {}

  // ─── Create ────────────────────────────────────────────────────────────────

  async create(dto: CreateCameraDto) {
    // Check camera code uniqueness
    const exists = await this.cameraRepository.findOne({
      where: { code: dto.code },
    });
    if (exists) {
      throw new ConflictException('Camera code already exists');
    }

    // Verify zone exists
    const zone = await this.zoneRepository.findOne({
      where: { id: dto.zoneId },
    });
    if (!zone) {
      throw new NotFoundException('Zone not found');
    }

    // Verify edge node exists
    const edgeNode = await this.edgeNodeRepository.findOne({
      where: { id: dto.edgeNodeId },
    });
    if (!edgeNode) {
      throw new NotFoundException('Edge node not found');
    }

    const camera = this.cameraRepository.create(dto);
    return this.cameraRepository.save(camera);
  }


  async findByCode(code: string) {
    const camera = await this.cameraRepository.findOne({
      where: { code },
      relations: ['zone', 'edgeNode'],
    });
    
    if (!camera) {
      throw new NotFoundException('Camera not found');
    }
    return camera;
  }
  // ─── Read All ──────────────────────────────────────────────────────────────

  async findAll() {
    return this.cameraRepository.find({
      relations: ['zone', 'edgeNode'],
      order: { createdAt: 'DESC' },
    });
  }

  // ─── Read One ──────────────────────────────────────────────────────────────

  async findOne(id: string) {
    const camera = await this.cameraRepository.findOne({
      where: { id },
      relations: ['zone', 'edgeNode'],
    });

    if (!camera) {
      throw new NotFoundException('Camera not found');
    }

    return camera;
  }

  // ─── Read by Zone ──────────────────────────────────────────────────────────

  async findByZone(zoneId: string) {
    return this.cameraRepository.find({
      where: { zoneId },
      relations: ['zone', 'edgeNode'],
      order: { createdAt: 'DESC' },
    });
  }

  // ─── Read by Edge Node ─────────────────────────────────────────────────────

  async findByEdgeNode(edgeNodeId: string) {
    return this.cameraRepository.find({
      where: { edgeNodeId },
      relations: ['zone', 'edgeNode'],
      order: { createdAt: 'DESC' },
    });
  }

  // ─── Update ────────────────────────────────────────────────────────────────

  async update(id: string, dto: UpdateCameraDto) {
    const camera = await this.findOne(id);

    // ✅ Fixed: validate zoneId if being changed
    if (dto.zoneId && dto.zoneId !== camera.zoneId) {
      const zone = await this.zoneRepository.findOne({
        where: { id: dto.zoneId },
      });
      if (!zone) {
        throw new NotFoundException('Zone not found');
      }
    }

    // ✅ Fixed: validate edgeNodeId if being changed
    if (dto.edgeNodeId && dto.edgeNodeId !== camera.edgeNodeId) {
      const edgeNode = await this.edgeNodeRepository.findOne({
        where: { id: dto.edgeNodeId },
      });
      if (!edgeNode) {
        throw new NotFoundException('Edge node not found');
      }
    }

    // ✅ Fixed: validate code uniqueness if being changed
    if (dto.code && dto.code !== camera.code) {
      const codeExists = await this.cameraRepository.findOne({
        where: { code: dto.code },
      });
      if (codeExists) {
        throw new ConflictException('Camera code already exists');
      }
    }

    Object.assign(camera, dto);
    return this.cameraRepository.save(camera);
  }

  // ─── Delete ────────────────────────────────────────────────────────────────

  async remove(id: string) {
    const camera = await this.findOne(id);
    await this.cameraRepository.remove(camera);
    return { message: 'Camera deleted successfully' };
  }
}
