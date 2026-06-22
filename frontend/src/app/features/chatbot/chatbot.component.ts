import { Component, signal, inject } from "@angular/core";
import { FormsModule } from "@angular/forms";
import { ButtonComponent } from "@common/components/button/button.component";
import { InputComponent } from "@common/components/input/input";
import { ChatbotService } from "@core/services";
import { BtnStylesEnum } from "@shared/enums";

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
  isLoading = signal(false);
  private sessionId: string | null = null;

  suggestions = [
    "Show assaults near parking areas",
    "Find incidents with masked subjects",
    "Loitering alerts from last 24 hours",
    "Audio events involving screaming",
  ];

  sendMessage(text: string) {
    if (!text.trim() || this.isLoading()) return;
    const now = new Date().toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
    });
    this.messages.update((msgs) => [
      ...msgs,
      { role: "user", text: text.trim(), time: now },
    ]);
    this.isLoading.set(true);

    this.chatbotService.chat(text.trim(), this.sessionId).subscribe({
      next: (response) => {
        this.sessionId = response.session_id;
        this.messages.update((msgs) => [
          ...msgs,
          { role: "assistant", text: response.answer, time: now },
        ]);
        this.isLoading.set(false);
      },
      error: () => {
        this.messages.update((msgs) => [
          ...msgs,
          { role: "assistant", text: "Sorry, I could not process your request. Please try again.", time: now },
        ]);
        this.isLoading.set(false);
      },
    });
    this.input = "";
  }

  clearSession() {
    if (this.sessionId) {
      this.chatbotService.clearSession(this.sessionId).subscribe();
    }
    this.sessionId = null;
    this.messages.set([]);
  }

  protected readonly BtnStylesEnum = BtnStylesEnum;
}
