import React from "react";
import { useDispatch, useSelector } from "react-redux";
import { updateField, submitInteraction, resetForm } from "../store/interactionSlice";

const INTERACTION_TYPES = ["Meeting", "Call", "Email", "Conference"];

function ListEditor({ label, values, onAdd, placeholder }) {
  const [draft, setDraft] = React.useState("");
  return (
    <div className="field">
      <label>{label}</label>
      <div style={{ display: "flex", gap: 6 }}>
        <input
          value={draft}
          placeholder={placeholder}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && draft.trim()) {
              onAdd(draft.trim());
              setDraft("");
            }
          }}
        />
        <button
          className="secondary"
          type="button"
          onClick={() => {
            if (draft.trim()) {
              onAdd(draft.trim());
              setDraft("");
            }
          }}
        >
          Add
        </button>
      </div>
      {values.length > 0 && (
        <div style={{ fontSize: 12, color: "#6b7280", marginTop: 4 }}>
          {values.join(", ")}
        </div>
      )}
    </div>
  );
}

export default function LogInteractionForm() {
  const dispatch = useDispatch();
  const form = useSelector((s) => s.interaction.form);
  const status = useSelector((s) => s.interaction.status);

  const set = (field) => (e) =>
    dispatch(updateField({ field, value: e.target.value }));

  return (
    <div className="card">
      <h2>Log HCP Interaction</h2>

      <div className="row">
        <div className="field">
          <label>HCP Name</label>
          <input
            value={form.hcpName}
            onChange={set("hcpName")}
            placeholder="Search or select HCP..."
          />
        </div>
        <div className="field">
          <label>Interaction Type</label>
          <select value={form.interactionType} onChange={set("interactionType")}>
            {INTERACTION_TYPES.map((t) => (
              <option key={t} value={t}>{t}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="row">
        <div className="field">
          <label>Date</label>
          <input type="date" value={form.date} onChange={set("date")} />
        </div>
        <div className="field">
          <label>Time</label>
          <input type="time" value={form.time} onChange={set("time")} />
        </div>
      </div>

      <ListEditor
        label="Attendees"
        values={form.attendees}
        placeholder="Enter names or search..."
        onAdd={(v) =>
          dispatch(updateField({ field: "attendees", value: [...form.attendees, v] }))
        }
      />

      <div className="field">
        <label>Topics Discussed</label>
        <textarea rows={3} value={form.topicsDiscussed} onChange={set("topicsDiscussed")} />
      </div>

      <ListEditor
        label="Materials Shared"
        values={form.materialsShared}
        placeholder="Search / add material..."
        onAdd={(v) =>
          dispatch(updateField({ field: "materialsShared", value: [...form.materialsShared, v] }))
        }
      />

      <ListEditor
        label="Samples Distributed"
        values={form.samplesDistributed}
        placeholder="Add sample..."
        onAdd={(v) =>
          dispatch(updateField({ field: "samplesDistributed", value: [...form.samplesDistributed, v] }))
        }
      />

      <div className="field">
        <label>Observed / Inferred HCP Sentiment</label>
        <div className="sentiment-options">
          {["positive", "neutral", "negative"].map((s) => (
            <label key={s}>
              <input
                type="radio"
                name="sentiment"
                checked={form.sentiment === s}
                onChange={() => dispatch(updateField({ field: "sentiment", value: s }))}
              />
              {s[0].toUpperCase() + s.slice(1)}
            </label>
          ))}
        </div>
      </div>

      <div className="field">
        <label>Outcomes</label>
        <textarea rows={2} value={form.outcomes} onChange={set("outcomes")} />
      </div>

      <div className="field">
        <label>Follow-up Actions</label>
        <textarea rows={2} value={form.followUpActions} onChange={set("followUpActions")} />
      </div>

      {form.aiSuggestedFollowups.length > 0 && (
        <div className="suggestions">
          <strong>AI Suggested Follow-ups:</strong>
          <ul>
            {form.aiSuggestedFollowups.map((s, i) => (
              <li key={i}>+ {s}</li>
            ))}
          </ul>
        </div>
      )}

      <div style={{ marginTop: 16, display: "flex", gap: 8 }}>
        <button
          className="primary"
          disabled={status === "loading"}
          onClick={() => dispatch(submitInteraction())}
        >
          {status === "loading" ? "Logging..." : "Log Interaction"}
        </button>
        <button className="secondary" onClick={() => dispatch(resetForm())}>
          Reset
        </button>
      </div>
    </div>
  );
}
