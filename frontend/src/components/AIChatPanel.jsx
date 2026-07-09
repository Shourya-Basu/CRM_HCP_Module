import React, { useEffect, useRef, useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import { sendChatMessage, userMessageAppended } from "../store/interactionSlice";

export default function AIChatPanel() {
  const dispatch = useDispatch();
  const { messages, isThinking } = useSelector((s) => s.interaction.chat);
  const [draft, setDraft] = useState("");
  const scrollRef = useRef(null);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, isThinking]);

  const send = () => {
    const text = draft.trim();
    if (!text || isThinking) return;
    dispatch(userMessageAppended(text));
    dispatch(sendChatMessage(text));
    setDraft("");
  };

  return (
    <div className="card chat-card">
      <div className="chat-header">
        <span className="title">AI Assistant</span>
      </div>

      <div className="chat-messages" ref={scrollRef}>
        {messages.map((m) => (
          <div className={`msg ${m.role}`} key={m.id}>{m.text}</div>
        ))}
        {isThinking && <div className="msg thinking">Assistant is thinking…</div>}
      </div>

      <div className="chat-input-row">
        <input
          type="text"
          placeholder="Describe interaction…"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
        />
        <button onClick={send} disabled={!draft.trim() || isThinking}>Log</button>
      </div>
    </div>
  );
}
