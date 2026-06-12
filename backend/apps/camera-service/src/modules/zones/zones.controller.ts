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

import { ZonesService } from './zones.service';
import { CreateZoneDto } from './dto/create-zone.dto';
import { UpdateZoneDto } from './dto/update-zone.dto';
import { JwtAuthGuard } from '../../../../../libs/common/src/guards/jwt-auth.guard';
import { RolesGuard } from '../../../../../libs/common/src/guards/roles.guards';
import { Roles } from '../../../../../libs/common/src/decorators/roles.decorator';
import { UserRole } from '../../../../../libs/common/enums/user.role.enum';

@Controller('zones')
@UseGuards(JwtAuthGuard) // ✅ All endpoints require valid JWT
export class ZonesController {
  constructor(private readonly zonesService: ZonesService) {}

  // ─── Create ────────────────────────────────────────────────────────────────
  // ✅ Admin + supervisor only
  @Post()
  @UseGuards(RolesGuard)
  @Roles(UserRole.ADMIN, UserRole.SUPERVISOR)
  create(@Body() dto: CreateZoneDto) {
    return this.zonesService.create(dto);
  }

  // ─── Read All ──────────────────────────────────────────────────────────────
  // ✅ All authenticated users can view zones
  @Get()
  findAll() {
    return this.zonesService.findAll();
  }

  // ─── Read One ──────────────────────────────────────────────────────────────
  @Get(':id')
  findOne(@Param('id') id: string) {
    return this.zonesService.findOne(id);
  }

  // ─── Update ────────────────────────────────────────────────────────────────
  // ✅ Admin + supervisor only
  @Patch(':id')
  @UseGuards(RolesGuard)
  @Roles(UserRole.ADMIN, UserRole.SUPERVISOR)
  update(@Param('id') id: string, @Body() dto: UpdateZoneDto) {
    return this.zonesService.update(id, dto);
  }

  // ─── Delete ────────────────────────────────────────────────────────────────
  // ✅ Admin only — deleting a zone is destructive
  @Delete(':id')
  @UseGuards(RolesGuard)
  @Roles(UserRole.ADMIN)
  remove(@Param('id') id: string) {
    return this.zonesService.remove(id);
  }
}
