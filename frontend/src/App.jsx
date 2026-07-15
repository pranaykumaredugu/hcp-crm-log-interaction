import React from "react";
import LogInteractionForm from "./components/LogInteractionForm";
import ChatPanel from "./components/ChatPanel";

export default function App() {
  return (
    <div className="screen">
      <LogInteractionForm />
      <ChatPanel />
    </div>
  );
}
