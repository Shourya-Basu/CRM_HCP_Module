import React, { useState } from "react";
import { useDispatch, useSelector } from "react-redux";
import {
  fieldChanged,
  materialAdded,
  sampleAdded,
  submitStructuredInteraction,
} from "../store/interactionSlice";

const SENTIMENTS = ["Positive", "Neutral", "Negative"];
const TYPES = ["Meeting", "Call", "Email", "Conference"];

function Field({ name, label, aiFilled, children }) {
  return (
    <div className={`field ${aiFilled ? "ai-filled" : ""}`}>
      <label htmlFor={name}>{label}</label>
      {children}
    </div>
  );
}

export default function StructuredForm() {
  const dispatch = useDispatch();
  const form = useSelector((s) => s.interaction.form);
  const aiFilledFields = useSelector((s) => s.interaction.aiFilledFields);
  const suggestedFollowUps = useSelector((s) => s.interaction.suggestedFollowUps);
  const saveStatus = useSelector((s) => s.interaction.saveStatus);
  const [materialDraft, setMaterialDraft] = useState("");
  const [sampleDraft, setSampleDraft] = useState("");

  const isAi = (field) => aiFilledFields.includes(field);
  const set = (field) => (e) => dispatch(fieldChanged({ field, value: e.target.value }));

  return (
    <div className="card form-card">
      <h2>Interaction Details</h2>

      <div className="field-row">
        <Field name="hcpName" label="HCP Name" aiFilled={isAi("hcpName")}>
          <input
            id="hcpName"
            type="text"
            placeholder="Search or select HCP…"
            value={form.hcpName}
            onChange={set("hcpName")}
          />
        </Field>
        <Field name="interactionType" label="Interaction Type" aiFilled={isAi("interactionType")}>
          <select id="interactionType" value={form.interactionType} onChange={set("interactionType")}>
            {TYPES.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </Field>
      </div>
            <br />
      <div className="field-row">
        <Field name="date" label="Date" aiFilled={isAi("date")}>
          <input id="date" type="date" value={form.date} onChange={set("date")} />
        </Field>
        <Field name="time" label="Time" aiFilled={isAi("time")}>
          <input id="time" type="time" value={form.time} onChange={set("time")} />
        </Field>
      </div>
            <br />
      <Field name="attendees" label="Attendees" aiFilled={isAi("attendees")}>
        <input id="attendees" type="text" placeholder="Enter names or search…" value={form.attendees} onChange={set("attendees")} />
      </Field>
            <br />
      <Field name="topicsDiscussed" label="Topics Discussed" aiFilled={isAi("topicsDiscussed")}>
        <textarea id="topicsDiscussed" placeholder="Enter key discussion points…" value={form.topicsDiscussed} onChange={set("topicsDiscussed")} />
      </Field><br />
      <button className="voice-note-btn" type="button" title="Requires consent">
        🎙 Summarize from Voice Note (Requires Consent)
      </button>
            <br /><br />
      <div className="field" style={{ marginTop: 16 }}>
        <label>Materials Shared</label>
        <div className="chip-row">
          {form.materials.map((m, i) => (
            <span className="chip" key={i}>{m}</span>
          ))}
          <input
            type="text"
            placeholder="Add material…"
            value={materialDraft}
            onChange={(e) => setMaterialDraft(e.target.value)}
            style={{ flex: "1 1 140px", padding: "6px 10px", borderRadius: 8, border: "1px solid var(--border)" }}
            onKeyDown={(e) => {
              if (e.key === "Enter" && materialDraft.trim()) {
                dispatch(materialAdded(materialDraft.trim()));
                setMaterialDraft("");
              }
            }}
          />
        </div>
      </div>
            <br />
      <div className="field" style={{ marginTop: 12 }}>
        <label>Samples Distributed</label>
        <div className="chip-row">
          {form.samples.map((s, i) => (
            <span className="chip" key={i}>{s}</span>
          ))}
          <input
            type="text"
            placeholder="Add sample…"
            value={sampleDraft}
            onChange={(e) => setSampleDraft(e.target.value)}
            style={{ flex: "1 1 140px", padding: "6px 10px", borderRadius: 8, border: "1px solid var(--border)" }}
            onKeyDown={(e) => {
              if (e.key === "Enter" && sampleDraft.trim()) {
                dispatch(sampleAdded(sampleDraft.trim()));
                setSampleDraft("");
              }
            }}
          />
        </div>
      </div>
            <br />
      <div className="field" style={{ marginTop: 16 }}>
        <label>Observed / Inferred HCP Sentiment</label>
        <div className={`sentiment-group ${isAi("sentiment") ? "ai-filled" : ""}`}>
          {SENTIMENTS.map((s) => (
            <button
              key={s}
              type="button"
              className={`sentiment-btn ${form.sentiment === s ? `selected ${s}` : ""}`}
              onClick={() => dispatch(fieldChanged({ field: "sentiment", value: s }))}
            >
              {s}
            </button>
          ))}
        </div>
      </div>
          <br />
      <div style={{ marginTop: 14 }}>
        <Field name="outcomes" label="Outcomes" aiFilled={isAi("outcomes")}>
          <textarea id="outcomes" placeholder="Key outcomes or agreements…" value={form.outcomes} onChange={set("outcomes")} />
        </Field>
      </div>
          <br />
      <div style={{ marginTop: 14 }}>
        <Field name="followUpActions" label="Follow-up Actions" aiFilled={isAi("followUpActions")}>
          <textarea id="followUpActions" placeholder="Enter next steps or tasks…" value={form.followUpActions} onChange={set("followUpActions")} />
        </Field>
      </div>

      {suggestedFollowUps.length > 0 && (
        <div className="followups">
          <h3>AI Suggested Follow-ups</h3>
          <ul>
            {suggestedFollowUps.map((f, i) => (
              <li key={i}>{f}</li>
            ))}
          </ul>
        </div>
      )}
    <br />
      <div style={{ marginTop: 18 }}>
        <button
          className="primary-btn"
          disabled={!form.hcpName || saveStatus === "saving"}
          onClick={() => dispatch(submitStructuredInteraction())}
        >
          {saveStatus === "saving" ? "Saving…" : "Save Interaction"}
        </button>
      </div>
    </div>
  );
}
