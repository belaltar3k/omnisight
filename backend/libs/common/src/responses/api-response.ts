export class ApiResponse<T = unknown> {
  success!: boolean;
  statusCode!: number;
  message!: string;
  data?: T;
  error?: string;

  private constructor(init: ApiResponse<T>) {
    Object.assign(this, init);
  }

  static ok<T>(data: T, message = 'Success', statusCode = 200): ApiResponse<T> {
    return new ApiResponse<T>({ success: true, statusCode, message, data });
  }

  static created<T>(data: T, message = 'Created'): ApiResponse<T> {
    return new ApiResponse<T>({ success: true, statusCode: 201, message, data });
  }

  static fail(message: string, statusCode: number, error?: string): ApiResponse<null> {
    return new ApiResponse<null>({ success: false, statusCode, message, error });
  }
}
