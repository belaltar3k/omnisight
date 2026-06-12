import { NestFactory } from '@nestjs/core';
import { ValidationPipe } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { UserServiceModule } from './user-service.module';
import { AllExceptionsFilter } from '../../../libs/common/src/responses/http-exception.filter';

async function bootstrap() {
  const app = await NestFactory.create(UserServiceModule);

  app.useGlobalPipes(
    new ValidationPipe({
      whitelist: true,
      forbidNonWhitelisted: true,
      transform: true,
    }),
  );
  app.useGlobalFilters(new AllExceptionsFilter());

  const configService = app.get(ConfigService);
  const port = configService.get<number>('USER_PORT') || 3004;

  await app.listen(port);
  console.log(`User Service running on port ${port}`);
}

bootstrap();