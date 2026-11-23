import { Suspense } from "react";
import ChatExperience from "@/components/chat/ChatExperience";

export default function ChatPage() {
  return (
    <Suspense
      fallback={
        <div className="container-page py-16 text-center" role="status">
          Préparation de votre session visiteur...
        </div>
      }
    >
      <ChatExperience />
    </Suspense>
  );
}
