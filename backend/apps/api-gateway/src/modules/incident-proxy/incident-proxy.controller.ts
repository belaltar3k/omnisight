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
  Query,
  Req,
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
export class IncidentProxyController {
  private readonly incidentServiceUrl: string;

  constructor(
    private readonly httpService: HttpService,
    configService: ConfigService,
  ) {
    this.incidentServiceUrl =
      configService.get<string>('INCIDENT_SERVICE_URL') ?? 'http://localhost:3003';
  }

  private handleError(error: any): never {
    throw new HttpException(
      error.response?.data ?? { message: 'Incident service is unavailable' },
      error.response?.status ?? 502,
    );
  }

  private authHeaders(authorization: string) {
    return { headers: { authorization } };
  }

  // ══════════════════════════════════════════════════════════════════════════
  // EDGE ENDPOINTS — no JWT (edge node uses shared secret)
  // ══════════════════════════════════════════════════════════════════════════

  @Post('edge/sync')
  async edgeSync(
    @Body() body: any,
    @Headers('x-edge-secret') secret: string,
  ) {
    try {
      const response = await firstValueFrom(
        this.httpService
          .post(`${this.incidentServiceUrl}/edge/sync`, body, {
            headers: { 'x-edge-secret': secret },
          })
          .pipe(timeout(10000)),
      );
      return response.data;
    } catch (error: any) {
      this.handleError(error);
    }
  }

  @Post('edge/classify')
  async edgeClassify(
    @Body() body: any,
    @Headers('x-edge-secret') secret: string,
  ) {
    try {
      const response = await firstValueFrom(
        this.httpService
          .post(`${this.incidentServiceUrl}/edge/classify`, body, {
            headers: { 'x-edge-secret': secret },
          })
          .pipe(timeout(10000)),
      );
      return response.data;
    } catch (error: any) {
      this.handleError(error);
    }
  }

  // ══════════════════════════════════════════════════════════════════════════
  // INCIDENTS CRUD
  // ══════════════════════════════════════════════════════════════════════════

  @Post('incidents')
  @UseGuards(JwtAuthGuard, RolesGuard)
  @Roles(UserRole.ADMIN, UserRole.SUPERVISOR)
  async createIncident(
    @Body() body: any,
    @Headers('authorization') authorization: string,
  ) {
    try {
      const response = await firstValueFrom(
        this.httpService
          .post(`${this.incidentServiceUrl}/incidents`, body, this.authHeaders(authorization))
          .pipe(timeout(5000)),
      );
      return response.data;
    } catch (error: any) {
      this.handleError(error);
    }
  }

  @Get('incidents')
  @UseGuards(JwtAuthGuard)
  async getIncidents(
    @Query() query: any,
    @Headers('authorization') authorization: string,
  ) {
    try {
      const response = await firstValueFrom(
        this.httpService
          .get(`${this.incidentServiceUrl}/incidents`, {
            headers: { authorization },
            params: query,
          })
          .pipe(timeout(5000)),
      );
      return response.data;
    } catch (error: any) {
      this.handleError(error);
    }
  }

  // ✅ IMPORTANT: /my before /:id
  @Get('incidents/my')
  @UseGuards(JwtAuthGuard)
  async getMyIncidents(
    @Query() query: any,
    @Headers('authorization') authorization: string,
  ) {
    try {
      const response = await firstValueFrom(
        this.httpService
          .get(`${this.incidentServiceUrl}/incidents/my`, {
            headers: { authorization },
            params: query,
          })
          .pipe(timeout(5000)),
      );
      return response.data;
    } catch (error: any) {
      this.handleError(error);
    }
  }

  @Get('incidents/:id')
  @UseGuards(JwtAuthGuard)
  async getIncident(
    @Param('id') id: string,
    @Headers('authorization') authorization: string,
  ) {
    try {
      const response = await firstValueFrom(
        this.httpService
          .get(`${this.incidentServiceUrl}/incidents/${id}`, this.authHeaders(authorization))
          .pipe(timeout(5000)),
      );
      return response.data;
    } catch (error: any) {
      this.handleError(error);
    }
  }

  @Patch('incidents/:id')
  @UseGuards(JwtAuthGuard, RolesGuard)
  @Roles(UserRole.ADMIN, UserRole.SUPERVISOR)
  async updateIncident(
    @Param('id') id: string,
    @Body() body: any,
    @Headers('authorization') authorization: string,
  ) {
    try {
      const response = await firstValueFrom(
        this.httpService
          .patch(`${this.incidentServiceUrl}/incidents/${id}`, body, this.authHeaders(authorization))
          .pipe(timeout(5000)),
      );
      return response.data;
    } catch (error: any) {
      this.handleError(error);
    }
  }

  @Delete('incidents/:id')
  @UseGuards(JwtAuthGuard, RolesGuard)
  @Roles(UserRole.ADMIN)
  async deleteIncident(
    @Param('id') id: string,
    @Headers('authorization') authorization: string,
  ) {
    try {
      const response = await firstValueFrom(
        this.httpService
          .delete(`${this.incidentServiceUrl}/incidents/${id}`, this.authHeaders(authorization))
          .pipe(timeout(5000)),
      );
      return response.data;
    } catch (error: any) {
      this.handleError(error);
    }
  }

  // ══════════════════════════════════════════════════════════════════════════
  // ACTIONS
  // ══════════════════════════════════════════════════════════════════════════

  @Post('incidents/:id/assign')
  @UseGuards(JwtAuthGuard, RolesGuard)
  @Roles(UserRole.ADMIN, UserRole.SUPERVISOR)
  async assign(
    @Param('id') id: string,
    @Body() body: any,
    @Headers('authorization') authorization: string,
  ) {
    try {
      const response = await firstValueFrom(
        this.httpService
          .post(`${this.incidentServiceUrl}/incidents/${id}/assign`, body, this.authHeaders(authorization))
          .pipe(timeout(5000)),
      );
      return response.data;
    } catch (error: any) {
      this.handleError(error);
    }
  }

  @Post('incidents/:id/acknowledge')
  @UseGuards(JwtAuthGuard)
  async acknowledge(
    @Param('id') id: string,
    @Headers('authorization') authorization: string,
  ) {
    try {
      const response = await firstValueFrom(
        this.httpService
          .post(`${this.incidentServiceUrl}/incidents/${id}/acknowledge`, {}, this.authHeaders(authorization))
          .pipe(timeout(5000)),
      );
      return response.data;
    } catch (error: any) {
      this.handleError(error);
    }
  }

  @Post('incidents/:id/investigate')
  @UseGuards(JwtAuthGuard)
  async investigate(
    @Param('id') id: string,
    @Headers('authorization') authorization: string,
  ) {
    try {
      const response = await firstValueFrom(
        this.httpService
          .post(`${this.incidentServiceUrl}/incidents/${id}/investigate`, {}, this.authHeaders(authorization))
          .pipe(timeout(5000)),
      );
      return response.data;
    } catch (error: any) {
      this.handleError(error);
    }
  }

  @Post('incidents/:id/dispatch')
  @UseGuards(JwtAuthGuard, RolesGuard)
  @Roles(UserRole.ADMIN, UserRole.SUPERVISOR)
  async dispatch(
    @Param('id') id: string,
    @Headers('authorization') authorization: string,
  ) {
    try {
      const response = await firstValueFrom(
        this.httpService
          .post(`${this.incidentServiceUrl}/incidents/${id}/dispatch`, {}, this.authHeaders(authorization))
          .pipe(timeout(5000)),
      );
      return response.data;
    } catch (error: any) {
      this.handleError(error);
    }
  }

  @Post('incidents/:id/on-scene')
  @UseGuards(JwtAuthGuard)
  async onScene(
    @Param('id') id: string,
    @Headers('authorization') authorization: string,
  ) {
    try {
      const response = await firstValueFrom(
        this.httpService
          .post(`${this.incidentServiceUrl}/incidents/${id}/on-scene`, {}, this.authHeaders(authorization))
          .pipe(timeout(5000)),
      );
      return response.data;
    } catch (error: any) {
      this.handleError(error);
    }
  }

  @Post('incidents/:id/resolve')
  @UseGuards(JwtAuthGuard)
  async resolve(
    @Param('id') id: string,
    @Body() body: any,
    @Headers('authorization') authorization: string,
  ) {
    try {
      const response = await firstValueFrom(
        this.httpService
          .post(`${this.incidentServiceUrl}/incidents/${id}/resolve`, body, this.authHeaders(authorization))
          .pipe(timeout(5000)),
      );
      return response.data;
    } catch (error: any) {
      this.handleError(error);
    }
  }

  @Post('incidents/:id/false-positive')
  @UseGuards(JwtAuthGuard, RolesGuard)
  @Roles(UserRole.ADMIN, UserRole.SUPERVISOR)
  async falsePositive(
    @Param('id') id: string,
    @Body() body: any,
    @Headers('authorization') authorization: string,
  ) {
    try {
      const response = await firstValueFrom(
        this.httpService
          .post(`${this.incidentServiceUrl}/incidents/${id}/false-positive`, body, this.authHeaders(authorization))
          .pipe(timeout(5000)),
      );
      return response.data;
    } catch (error: any) {
      this.handleError(error);
    }
  }

  // ══════════════════════════════════════════════════════════════════════════
  // NOTES & TIMELINE
  // ══════════════════════════════════════════════════════════════════════════

  @Post('incidents/:id/notes')
  @UseGuards(JwtAuthGuard)
  async addNote(
    @Param('id') id: string,
    @Body() body: any,
    @Headers('authorization') authorization: string,
  ) {
    try {
      const response = await firstValueFrom(
        this.httpService
          .post(`${this.incidentServiceUrl}/incidents/${id}/notes`, body, this.authHeaders(authorization))
          .pipe(timeout(5000)),
      );
      return response.data;
    } catch (error: any) {
      this.handleError(error);
    }
  }

  @Get('incidents/:id/notes')
  @UseGuards(JwtAuthGuard)
  async getNotes(
    @Param('id') id: string,
    @Headers('authorization') authorization: string,
  ) {
    try {
      const response = await firstValueFrom(
        this.httpService
          .get(`${this.incidentServiceUrl}/incidents/${id}/notes`, this.authHeaders(authorization))
          .pipe(timeout(5000)),
      );
      return response.data;
    } catch (error: any) {
      this.handleError(error);
    }
  }

  @Get('incidents/:id/timeline')
  @UseGuards(JwtAuthGuard)
  async getTimeline(
    @Param('id') id: string,
    @Headers('authorization') authorization: string,
  ) {
    try {
      const response = await firstValueFrom(
        this.httpService
          .get(`${this.incidentServiceUrl}/incidents/${id}/timeline`, this.authHeaders(authorization))
          .pipe(timeout(5000)),
      );
      return response.data;
    } catch (error: any) {
      this.handleError(error);
    }
  }
}
