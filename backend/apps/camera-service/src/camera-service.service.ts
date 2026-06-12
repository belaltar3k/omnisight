import { Injectable } from '@nestjs/common';

@Injectable()
export class CameraServiceService {
  getHello(): string {
    return 'Hello World!';
  }
}
