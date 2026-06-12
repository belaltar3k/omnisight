import { NestFactory } from '@nestjs/core';
import { MicroserviceOptions, Transport } from '@nestjs/microservices';
import { ValidationPipe } from '@nestjs/common';
import { AlertServiceModule } from './alert-service.module';
import { AllExceptionsFilter } from '../../../libs/common/src/responses/http-exception.filter';

async function bootstrap() {
  const app = await NestFactory.create(AlertServiceModule);

  app.useGlobalPipes(new ValidationPipe({ whitelist: true, transform: true }));
  app.useGlobalFilters(new AllExceptionsFilter());

  // Kafka consumer microservice
  app.connectMicroservice<MicroserviceOptions>({
    transport: Transport.KAFKA,
    options: {
      client: {
        brokers: [(process.env.KAFKA_BROKER ?? 'localhost:9092')],
      },
      consumer: {
        groupId: 'sentinel-alert-service',
      },
    },
  });

  await app.startAllMicroservices();
  await app.listen(process.env.ALERT_PORT ?? 3005);
  console.log(`Alert service running on port ${process.env.ALERT_PORT ?? 3005}`);
}

bootstrap();
