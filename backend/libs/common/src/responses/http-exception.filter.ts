import {
  ArgumentsHost,
  Catch,
  ExceptionFilter,
  HttpException,
  HttpStatus,
  Logger,
} from '@nestjs/common';
import { Request, Response } from 'express';
import { QueryFailedError } from 'typeorm';
import { ApiResponse } from './api-response';

@Catch()
export class AllExceptionsFilter implements ExceptionFilter {
  private readonly logger = new Logger(AllExceptionsFilter.name);

  catch(exception: unknown, host: ArgumentsHost) {
    const ctx = host.switchToHttp();
    const response = ctx.getResponse<Response>();
    const request = ctx.getRequest<Request>();

    let statusCode: number;
    let message: string;
    let error: string;

    if (exception instanceof HttpException) {
      statusCode = exception.getStatus();
      const exceptionResponse = exception.getResponse();

      if (typeof exceptionResponse === 'object' && exceptionResponse !== null) {
        const body = exceptionResponse as Record<string, unknown>;
        // Validation errors come as an array in body.message
        const raw = body['message'];
        message = Array.isArray(raw) ? raw.join(', ') : String(raw ?? exception.message);
        error = String(body['error'] ?? HttpStatus[statusCode] ?? 'Error');
      } else {
        message = String(exceptionResponse);
        error = HttpStatus[statusCode] ?? 'Error';
      }
    } else if (exception instanceof QueryFailedError) {
      // PostgreSQL error code 22P02 = invalid UUID / bad input syntax
      const pgCode = (exception as any).code;
      if (pgCode === '22P02') {
        statusCode = HttpStatus.BAD_REQUEST;
        message = 'Invalid identifier format';
        error = 'Bad Request';
      } else if (pgCode === '23505') {
        statusCode = HttpStatus.CONFLICT;
        message = 'Resource already exists';
        error = 'Conflict';
      } else {
        statusCode = HttpStatus.INTERNAL_SERVER_ERROR;
        message = 'Database error';
        error = 'Internal Server Error';
        this.logger.error(`DB error on ${request.method} ${request.url}: ${exception.message}`);
      }
    } else {
      statusCode = HttpStatus.INTERNAL_SERVER_ERROR;
      message = 'An unexpected error occurred';
      error = 'Internal Server Error';
      this.logger.error(
        `Unhandled exception on ${request.method} ${request.url}`,
        exception instanceof Error ? exception.stack : String(exception),
      );
    }

    response.status(statusCode).json(ApiResponse.fail(message, statusCode, error));
  }
}
