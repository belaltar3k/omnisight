import {
  Body,
  Controller,
  Delete,
  Get,
  Param,
  Patch,
  Post,
  UseGuards,
} from '@nestjs/common';

import { CamerasService } from './cameras.service';
import { CreateCameraDto } from './dto/create-camera.dto';
import { UpdateCameraDto } from './dto/update-camera.dto';
import { JwtAuthGuard } from '../../../../../libs/common/src/guards/jwt-auth.guard';
import { RolesGuard } from '../../../../../libs/common/src/guards/roles.guards';
import { Roles } from '../../../../..//libs/common/src/decorators/roles.decorator';
import { UserRole } from '../../../../../libs/common/enums/user.role.enum';

@Controller('cameras')
@UseGuards(JwtAuthGuard) // ✅ All endpoints require valid JWT
export class CamerasController {
  constructor(private readonly camerasService: CamerasService) {}

  // ─── Create ────────────────────────────────────────────────────────────────
  // ✅ Admin + supervisor only
  @Post()
  @UseGuards(RolesGuard)
  @Roles(UserRole.ADMIN, UserRole.SUPERVISOR)
  create(@Body() dto: CreateCameraDto) {
    return this.camerasService.create(dto);
  }

  // ─── Read All ──────────────────────────────────────────────────────────────
  // ✅ All authenticated users can view cameras
  @Get()
  findAll() {
    return this.camerasService.findAll();
  }

  @Get('by-code/:code')
  @UseGuards(RolesGuard)
  @Roles(UserRole.ADMIN, UserRole.SUPERVISOR, UserRole.INCIDENT_SERVICE)
  findByCode(@Param('code') code: string) {
    return this.camerasService.findByCode(code);
  }

  // ─── Read by Zone ──────────────────────────────────────────────────────────
  @Get('by-zone/:zoneId')
  findByZone(@Param('zoneId') zoneId: string) {
    return this.camerasService.findByZone(zoneId);
  }

  // ─── Read by Edge Node ─────────────────────────────────────────────────────
  @Get('by-edge-node/:edgeNodeId')
  findByEdgeNode(@Param('edgeNodeId') edgeNodeId: string) {
    return this.camerasService.findByEdgeNode(edgeNodeId);
  }

  // ─── Read One ──────────────────────────────────────────────────────────────
  @Get(':id')
  findOne(@Param('id') id: string) {
    return this.camerasService.findOne(id);
  }

  // ─── Update ────────────────────────────────────────────────────────────────
  // ✅ Admin + supervisor only
  @Patch(':id')
  @UseGuards(RolesGuard)
  @Roles(UserRole.ADMIN, UserRole.SUPERVISOR)
  update(@Param('id') id: string, @Body() dto: UpdateCameraDto) {
    return this.camerasService.update(id, dto);
  }

  // ─── Delete ────────────────────────────────────────────────────────────────
  // ✅ Admin only
  @Delete(':id')
  @UseGuards(RolesGuard)
  @Roles(UserRole.ADMIN)
  remove(@Param('id') id: string) {
    return this.camerasService.remove(id);
  }
}
