import { NestFactory } from '@nestjs/core';
import { ValidationPipe } from '@nestjs/common';
import { IncidentServiceModule } from './incident-service.module';
import { AllExceptionsFilter } from '../../../libs/common/src/responses/http-exception.filter';

async function bootstrap() {
  const app = await NestFactory.create(IncidentServiceModule);

  app.useGlobalPipes(
    new ValidationPipe({
      whitelist: true,
      forbidNonWhitelisted: true,
      transform: true,
    }),
  );
  app.useGlobalFilters(new AllExceptionsFilter());

  const port = process.env.INCIDENT_PORT ?? 3003;
  await app.listen(port);
  console.log(`Incident Service running on port ${port}`);
}

bootstrap();
