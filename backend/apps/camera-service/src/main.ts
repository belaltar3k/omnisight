import { NestFactory } from '@nestjs/core';
import { ValidationPipe } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { CameraServiceModule } from './camera-service.module';
import { AllExceptionsFilter } from '../../../libs/common/src/responses/http-exception.filter';

async function bootstrap() {
  const app = await NestFactory.create(CameraServiceModule);

  app.useGlobalPipes(
    new ValidationPipe({
      whitelist: true,
      forbidNonWhitelisted: true,
      transform: true,
    }),
  );
  app.useGlobalFilters(new AllExceptionsFilter());

  const configService = app.get(ConfigService);
  const port = configService.get<number>('CAMERA_PORT') || 3012;

  await app.listen(port);
  console.log(`Camera Service running on port ${port}`);
}

bootstrap();