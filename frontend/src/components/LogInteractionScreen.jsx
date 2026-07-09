import React from "react";
import { useSelector } from "react-redux";
import StructuredForm from "./StructuredForm";
import AIChatPanel from "./AIChatPanel";

export default function LogInteractionScreen() {
  const saveStatus = useSelector((s) => s.interaction.saveStatus);

  return (
    <div className="screen">
      <div className="screen-header">
        <h1>Log HCP Interaction</h1>
        <span className={`save-pill ${saveStatus}`}>
          {{ idle: "Not saved", saving: "Saving…", saved: "Saved", error: "Error" }[saveStatus]}
        </span>
      </div>
      <div className="layout">
        <StructuredForm />
        <AIChatPanel />
      </div>
    </div>
  );
}
