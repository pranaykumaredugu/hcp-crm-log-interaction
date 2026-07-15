import React from "react";
import { useDispatch, useSelector } from "react-redux";
import { setChatDraft, sendChatMessage } from "../store/interactionSlice";

export default function ChatPanel() {
  const dispatch = useDispatch();
  const messages = useSelector((s) => s.interaction.chatMessages);
  const draft = useSelector((s) => s.interaction.chatDraft);
  const hcpName = useSelector((s) => s.interaction.form.hcpName);
  const interactionId = useSelector((s) => s.interaction.currentInteractionId);
  const bottomRef = React.useRef(null);

  React.useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const send = () => {
    if (!draft.trim()) return;
    dispatch(sendChatMessage({ message: draft, hcpName, interactionId }));
  };

  return (
    <div className="card chat-panel">
      <h2>🤖 AI Assistant</h2>
      <div style={{ fontSize: 12, color: "#6b7280", marginTop: -10, marginBottom: 8 }}>
        Log interaction via chat
      </div>

      <div className="chat-messages">
        {messages.length === 0 && (
          <div style={{ color: "#6b7280", fontSize: 13 }}>
            Log interaction details here (e.g., "Met Dr. Smith, discussed
            Product X efficacy, positive sentiment, shared brochure") or ask
            for help.
          </div>
        )}
        {messages.map((m, i) => (
          <div key={i} className={`chat-bubble ${m.role === "user" ? "user" : "ai"}`}>
            {m.text}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      <div className="chat-input-row">
        <input
          value={draft}
          placeholder="Describe interaction..."
          onChange={(e) => dispatch(setChatDraft(e.target.value))}
          onKeyDown={(e) => e.key === "Enter" && send()}
        />
        <button className="primary" onClick={send}>Log</button>
      </div>
    </div>
  );
}
