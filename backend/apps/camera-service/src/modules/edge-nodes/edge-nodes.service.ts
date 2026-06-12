import { BadRequestException, ConflictException, Injectable, NotFoundException } from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { EdgeNode } from './entities/edge-node.entity';
import { Repository } from 'typeorm';
import { CreateEdgeNodeDto } from './dto/create-edge-node.dto';
import { Camera } from '../cameras/entities/camera.entity';
import { UpdateEdgeNodeDto } from './dto/update-edge-node.dto';
@Injectable()
export class EdgeNodesService {
  constructor(
    @InjectRepository(EdgeNode)
    private readonly edgeNodeRepository: Repository<EdgeNode>,
    @InjectRepository(Camera)
    private readonly cameraRepository: Repository<Camera>,
  ) {}


  async create(dto: CreateEdgeNodeDto) {
    const exists = await this.edgeNodeRepository.findOne({
      where: { code: dto.code },
    });

    if (exists) {
      throw new ConflictException('Edge node code already exists');
    }

    const edgeNode = this.edgeNodeRepository.create(dto);
    return this.edgeNodeRepository.save(edgeNode);
  }

  async findByCode(code: string) {
    const edgeNode = await this.edgeNodeRepository.findOne({
      where: { code },
    });
    
    if (!edgeNode) {
      throw new NotFoundException('Edge node not found');
    }
    return edgeNode;
  }
  async findAll() {
    return this.edgeNodeRepository.find({
      order: { createdAt: 'DESC' },
    });
  }
  async findOne(id: string) {
  const edgeNode = await this.edgeNodeRepository.findOne({
    where: { id },
  });

  if (!edgeNode) {
    throw new NotFoundException('Edge node not found');
  }

  return edgeNode;
}

async remove(id: string) {
  const edgeNode = await this.findOne(id);

  const camerasCount = await this.cameraRepository.count({
    where: { edgeNodeId: id },
  });

  if (camerasCount > 0) {
    throw new BadRequestException(
      'Cannot delete edge node because it has cameras assigned to it',
    );
  }

  await this.edgeNodeRepository.remove(edgeNode);

  return {
    message: 'Edge node deleted successfully',
  };
}
async update(id: string, dto: UpdateEdgeNodeDto) {
  const edgeNode = await this.findOne(id);

  Object.assign(edgeNode, dto);

  return this.edgeNodeRepository.save(edgeNode);
}
}