import { inject, Injectable } from "@angular/core";
import { chatbotApiEndpoints } from "@environments";
import { Observable } from "rxjs";
import { HttpClient } from "@angular/common/http";

export interface IChatRequest {
  message: string;
  session_id?: string | null;
}

export interface IChatResponse {
  answer: string;
  session_id: string;
  sources: any[];
  tools_used: string[];
}

export interface IChatSession {
  session_id: string;
  messages: { role: string; content: string; timestamp?: string }[];
}

@Injectable({
  providedIn: "root",
})
export class ChatbotService {
  private readonly httpClient = inject(HttpClient);

  chat(message: string, sessionId?: string | null): Observable<IChatResponse> {
    return this.httpClient.post<IChatResponse>(chatbotApiEndpoints.chat, {
      message,
      session_id: sessionId ?? null,
    });
  }

  getSession(sessionId: string): Observable<IChatSession> {
    return this.httpClient.get<IChatSession>(chatbotApiEndpoints.getSession(sessionId));
  }

  clearSession(sessionId: string): Observable<{ ok: boolean }> {
    return this.httpClient.delete<{ ok: boolean }>(chatbotApiEndpoints.clearSession(sessionId));
  }
}
