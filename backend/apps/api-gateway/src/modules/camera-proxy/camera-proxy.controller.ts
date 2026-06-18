import {
  Body,
  Controller,
  Delete,
  Get,
  Headers,
  HttpException,
  Param,
  Patch,
  Post,
  UseGuards,
} from '@nestjs/common';
import { HttpService } from '@nestjs/axios';
import { ConfigService } from '@nestjs/config';
import { firstValueFrom, timeout } from 'rxjs';

import { JwtAuthGuard } from '../../../../../libs/common/src/guards/jwt-auth.guard';
import { RolesGuard } from '../../../../../libs/common/src/guards/roles.guards';
import { Roles } from '../../../../../libs/common/src/decorators/roles.decorator';
import { UserRole } from '../../../../../libs/common/enums/user.role.enum';

@Controller('api/v1')
@UseGuards(JwtAuthGuard) // ✅ All routes require valid JWT
export class CameraProxyController {
  private readonly cameraServiceUrl: string;

  constructor(
    private readonly httpService: HttpService,
    // ✅ Fixed: use ConfigService instead of process.env
    configService: ConfigService,
  ) {
    this.cameraServiceUrl =
      configService.get<string>('CAMERA_SERVICE_URL') ?? 'http://localhost:3012';
  }

  // ─── Helper: forward errors cleanly ───────────────────────────────────────
  private handleError(error: any): never {
    throw new HttpException(
      error.response?.data ?? { message: 'Camera service is unavailable' },
      error.response?.status ?? 502,
    );
  }

  // ─── Helper: build auth headers to forward JWT to camera-service ──────────
  // ✅ Fixed: every call forwards the JWT so camera-service guards don't reject
  private authHeaders(authorization: string) {
    return { headers: { authorization } };
  }

  // ══════════════════════════════════════════════════════════════════════════
  // ZONES
  // ══════════════════════════════════════════════════════════════════════════

  // POST /api/v1/zones
  @Post('zones')
  @UseGuards(RolesGuard)
  @Roles(UserRole.ADMIN, UserRole.SUPERVISOR)
  async createZone(
    @Body() body: any,
    @Headers('authorization') authorization: string,
  ) {
    try {
      const response = await firstValueFrom(
        this.httpService
          .post(`${this.cameraServiceUrl}/zones`, body, this.authHeaders(authorization))
          .pipe(timeout(5000)),
      );
      return response.data;
    } catch (error: any) {
      this.handleError(error);
    }
  }

  // GET /api/v1/zones
  @Get('zones')
  async getZones(@Headers('authorization') authorization: string) {
    try {
      const response = await firstValueFrom(
        this.httpService
          .get(`${this.cameraServiceUrl}/zones`, this.authHeaders(authorization))
          .pipe(timeout(5000)),
      );
      return response.data;
    } catch (error: any) {
      this.handleError(error);
    }
  }

  // GET /api/v1/zones/:id
  // ✅ IMPORTANT: stays ABOVE /:id dynamic routes — defined before patch/delete
  @Get('zones/:id')
  async getZoneById(
    @Param('id') id: string,
    @Headers('authorization') authorization: string,
  ) {
    try {
      const response = await firstValueFrom(
        this.httpService
          .get(`${this.cameraServiceUrl}/zones/${id}`, this.authHeaders(authorization))
          .pipe(timeout(5000)),
      );
      return response.data;
    } catch (error: any) {
      this.handleError(error);
    }
  }

  // PATCH /api/v1/zones/:id
  @Patch('zones/:id')
  @UseGuards(RolesGuard)
  @Roles(UserRole.ADMIN, UserRole.SUPERVISOR)
  async updateZone(
    @Param('id') id: string,
    @Body() body: any,
    @Headers('authorization') authorization: string,
  ) {
    try {
      const response = await firstValueFrom(
        this.httpService
          .patch(`${this.cameraServiceUrl}/zones/${id}`, body, this.authHeaders(authorization))
          .pipe(timeout(5000)),
      );
      return response.data;
    } catch (error: any) {
      this.handleError(error);
    }
  }

  // DELETE /api/v1/zones/:id
  @Delete('zones/:id')
  @UseGuards(RolesGuard)
  @Roles(UserRole.ADMIN)
  async deleteZone(
    @Param('id') id: string,
    @Headers('authorization') authorization: string,
  ) {
    try {
      const response = await firstValueFrom(
        this.httpService
          .delete(`${this.cameraServiceUrl}/zones/${id}`, this.authHeaders(authorization))
          .pipe(timeout(5000)),
      );
      return response.data;
    } catch (error: any) {
      this.handleError(error);
    }
  }

  // ══════════════════════════════════════════════════════════════════════════
  // EDGE NODES
  // ══════════════════════════════════════════════════════════════════════════

  // POST /api/v1/edge-nodes
  @Post('edge-nodes')
  @UseGuards(RolesGuard)
  @Roles(UserRole.ADMIN)
  async createEdgeNode(
    @Body() body: any,
    @Headers('authorization') authorization: string,
  ) {
    try {
      const response = await firstValueFrom(
        this.httpService
          .post(`${this.cameraServiceUrl}/edge-nodes`, body, this.authHeaders(authorization))
          .pipe(timeout(5000)),
      );
      return response.data;
    } catch (error: any) {
      this.handleError(error);
    }
  }

  // GET /api/v1/edge-nodes
  @Get('edge-nodes')
  @UseGuards(RolesGuard)
  @Roles(UserRole.ADMIN, UserRole.SUPERVISOR)
  async getEdgeNodes(@Headers('authorization') authorization: string) {
    try {
      const response = await firstValueFrom(
        this.httpService
          .get(`${this.cameraServiceUrl}/edge-nodes`, this.authHeaders(authorization))
          .pipe(timeout(5000)),
      );
      return response.data;
    } catch (error: any) {
      this.handleError(error);
    }
  }

  // GET /api/v1/edge-nodes/:id
  @Get('edge-nodes/:id')
  @UseGuards(RolesGuard)
  @Roles(UserRole.ADMIN, UserRole.SUPERVISOR)
  async getEdgeNodeById(
    @Param('id') id: string,
    @Headers('authorization') authorization: string,
  ) {
    try {
      const response = await firstValueFrom(
        this.httpService
          .get(`${this.cameraServiceUrl}/edge-nodes/${id}`, this.authHeaders(authorization))
          .pipe(timeout(5000)),
      );
      return response.data;
    } catch (error: any) {
      this.handleError(error);
    }
  }

  // PATCH /api/v1/edge-nodes/:id
  @Patch('edge-nodes/:id')
  @UseGuards(RolesGuard)
  @Roles(UserRole.ADMIN)
  async updateEdgeNode(
    @Param('id') id: string,
    @Body() body: any,
    @Headers('authorization') authorization: string,
  ) {
    try {
      const response = await firstValueFrom(
        this.httpService
          .patch(`${this.cameraServiceUrl}/edge-nodes/${id}`, body, this.authHeaders(authorization))
          .pipe(timeout(5000)),
      );
      return response.data;
    } catch (error: any) {
      this.handleError(error);
    }
  }

  // DELETE /api/v1/edge-nodes/:id
  @Delete('edge-nodes/:id')
  @UseGuards(RolesGuard)
  @Roles(UserRole.ADMIN)
  async deleteEdgeNode(
    @Param('id') id: string,
    @Headers('authorization') authorization: string,
  ) {
    try {
      const response = await firstValueFrom(
        this.httpService
          .delete(`${this.cameraServiceUrl}/edge-nodes/${id}`, this.authHeaders(authorization))
          .pipe(timeout(5000)),
      );
      return response.data;
    } catch (error: any) {
      this.handleError(error);
    }
  }

  // ══════════════════════════════════════════════════════════════════════════
  // CAMERAS
  // ✅ IMPORTANT: specific routes (by-zone, by-edge-node) MUST come before /:id
  // ══════════════════════════════════════════════════════════════════════════

  // POST /api/v1/cameras
  @Post('cameras')
  @UseGuards(RolesGuard)
  @Roles(UserRole.ADMIN, UserRole.SUPERVISOR)
  async createCamera(
    @Body() body: any,
    @Headers('authorization') authorization: string,
  ) {
    try {
      const response = await firstValueFrom(
        this.httpService
          .post(`${this.cameraServiceUrl}/cameras`, body, this.authHeaders(authorization))
          .pipe(timeout(5000)),
      );
      return response.data;
    } catch (error: any) {
      this.handleError(error);
    }
  }

  // GET /api/v1/cameras
  @Get('cameras')
  async getCameras(@Headers('authorization') authorization: string) {
    try {
      const response = await firstValueFrom(
        this.httpService
          .get(`${this.cameraServiceUrl}/cameras`, this.authHeaders(authorization))
          .pipe(timeout(5000)),
      );
      return response.data;
    } catch (error: any) {
      this.handleError(error);
    }
  }

  // GET /api/v1/cameras/by-zone/:zoneId
  // ✅ IMPORTANT: before /:id
  @Get('cameras/by-zone/:zoneId')
  async getCamerasByZone(
    @Param('zoneId') zoneId: string,
    @Headers('authorization') authorization: string,
  ) {
    try {
      const response = await firstValueFrom(
        this.httpService
          .get(`${this.cameraServiceUrl}/cameras/by-zone/${zoneId}`, this.authHeaders(authorization))
          .pipe(timeout(5000)),
      );
      return response.data;
    } catch (error: any) {
      this.handleError(error);
    }
  }

  // GET /api/v1/cameras/by-edge-node/:edgeNodeId
  // ✅ IMPORTANT: before /:id
  @Get('cameras/by-edge-node/:edgeNodeId')
  async getCamerasByEdgeNode(
    @Param('edgeNodeId') edgeNodeId: string,
    @Headers('authorization') authorization: string,
  ) {
    try {
      const response = await firstValueFrom(
        this.httpService
          .get(
            `${this.cameraServiceUrl}/cameras/by-edge-node/${edgeNodeId}`,
            this.authHeaders(authorization),
          )
          .pipe(timeout(5000)),
      );
      return response.data;
    } catch (error: any) {
      this.handleError(error);
    }
  }

  // GET /api/v1/cameras/:id
  // ✅ IMPORTANT: after specific routes
  @Get('cameras/:id')
  async getCameraById(
    @Param('id') id: string,
    @Headers('authorization') authorization: string,
  ) {
    try {
      const response = await firstValueFrom(
        this.httpService
          .get(`${this.cameraServiceUrl}/cameras/${id}`, this.authHeaders(authorization))
          .pipe(timeout(5000)),
      );
      return response.data;
    } catch (error: any) {
      this.handleError(error);
    }
  }

  // PATCH /api/v1/cameras/:id
  @Patch('cameras/:id')
  @UseGuards(RolesGuard)
  @Roles(UserRole.ADMIN, UserRole.SUPERVISOR)
  async updateCamera(
    @Param('id') id: string,
    @Body() body: any,
    @Headers('authorization') authorization: string,
  ) {
    try {
      const response = await firstValueFrom(
        this.httpService
          .patch(`${this.cameraServiceUrl}/cameras/${id}`, body, this.authHeaders(authorization))
          .pipe(timeout(5000)),
      );
      return response.data;
    } catch (error: any) {
      this.handleError(error);
    }
  }

  // DELETE /api/v1/cameras/:id
  @Delete('cameras/:id')
  @UseGuards(RolesGuard)
  @Roles(UserRole.ADMIN)
  async deleteCamera(
    @Param('id') id: string,
    @Headers('authorization') authorization: string,
  ) {
    try {
      const response = await firstValueFrom(
        this.httpService
          .delete(`${this.cameraServiceUrl}/cameras/${id}`, this.authHeaders(authorization))
          .pipe(timeout(5000)),
      );
      return response.data;
    } catch (error: any) {
      this.handleError(error);
    }
  }
}
