import { Component, signal, inject } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { ButtonComponent } from "@common/components/button/button.component";
import { InputComponent } from "@common/components/input/input";
import { ChatbotService } from "@core/services";
import {BtnStylesEnum} from "@shared/enums";

interface Message {
  role: "user" | "assistant";
  text: string;
  time: string;
}

@Component({
  selector: "app-chatbot",
  standalone: true,
  imports: [FormsModule, ButtonComponent, InputComponent],
  templateUrl: "./chatbot.component.html",
})
export class ChatbotComponent {
  private readonly chatbotService = inject(ChatbotService);

  messages = signal<Message[]>([]);
  input = "";

  suggestions = [
    "Show assaults near parking areas",
    "Find incidents with masked subjects",
    "Loitering alerts from last 24 hours",
    "Audio events involving screaming",
  ];

  sendMessage(text: string) {
    if (!text.trim()) return;
    const now = new Date().toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });
    this.messages.update((msgs) => [
      ...msgs,
      { role: "user", text: text.trim(), time: now },
    ]);

    this.chatbotService.search({ query: text.trim() }).subscribe({
      next: (response) => {
        this.messages.update((msgs) => [
          ...msgs,
          { role: "assistant", text: response.response, time: now },
        ]);
      },
      error: (error) => {
        console.error("Chatbot error:", error);
      },
    });
    this.input = "";
  }

    protected readonly BtnStylesEnum = BtnStylesEnum;
}