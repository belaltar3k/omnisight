export interface IChatbotMessage {
  id?: string;
  content: string;
  sender: "user" | "assistant";
  timestamp?: string;
}

export interface IChatbotSearchRequest {
  query: string;
  limit?: number;
}

export interface IChatbotResponse {
  response: string;
  confidence?: number;
  sources?: string[];
}
