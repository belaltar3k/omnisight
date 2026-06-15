import { inject, Injectable } from "@angular/core";
import { chatbotApiEndpoints } from "@environments";
import { Observable } from "rxjs";
import { HttpClient } from "@angular/common/http";
import {
  IChatbotMessage,
  IChatbotResponse,
  IChatbotSearchRequest,
} from "@shared/interfaces/chatbot";

@Injectable({
  providedIn: "root",
})
export class ChatbotService {
  private readonly httpClient = inject(HttpClient);

  search(body: IChatbotSearchRequest): Observable<IChatbotResponse> {
    return this.httpClient.post<IChatbotResponse>(
      chatbotApiEndpoints.search,
      body,
    );
  }

  sendMessage(body: IChatbotMessage): Observable<IChatbotResponse> {
    return this.httpClient.post<IChatbotResponse>(
      chatbotApiEndpoints.sendMessage,
      body,
    );
  }

  getHistory(): Observable<IChatbotMessage[]> {
    return this.httpClient.get<IChatbotMessage[]>(
      chatbotApiEndpoints.getHistory,
    );
  }
}
