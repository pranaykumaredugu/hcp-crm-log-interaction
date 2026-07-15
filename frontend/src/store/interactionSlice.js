import { createSlice, createAsyncThunk } from "@reduxjs/toolkit";
import axios from "axios";

const initialFormState = {
  hcpName: "",
  interactionType: "Meeting",
  date: new Date().toISOString().slice(0, 10),
  time: new Date().toTimeString().slice(0, 5),
  attendees: [],
  topicsDiscussed: "",
  materialsShared: [],
  samplesDistributed: [],
  sentiment: "neutral",
  outcomes: "",
  followUpActions: "",
  aiSuggestedFollowups: [],
};

export const submitInteraction = createAsyncThunk(
  "interaction/submit",
  async (_args, { getState }) => {
    const { form } = getState().interaction;
    const payload = {
      hcp_name: form.hcpName,
      interaction_type: form.interactionType,
      attendees: form.attendees,
      topics_discussed: form.topicsDiscussed,
      materials_shared: form.materialsShared,
      samples_distributed: form.samplesDistributed,
      sentiment: form.sentiment,
      outcomes: form.outcomes,
      follow_up_actions: form.followUpActions,
    };
    const { data } = await axios.post("/api/interactions", payload);
    return data;
  }
);

export const sendChatMessage = createAsyncThunk(
  "interaction/sendChatMessage",
  async ({ message, hcpName, interactionId }) => {
    const { data } = await axios.post("/api/chat", {
      message,
      hcp_name: hcpName || null,
      interaction_id: interactionId || null,
    });
    return data;
  }
);

const interactionSlice = createSlice({
  name: "interaction",
  initialState: {
    form: initialFormState,
    currentInteractionId: null,
    chatMessages: [], // { role: 'user' | 'ai', text: string }
    chatDraft: "",
    status: "idle",
    error: null,
  },
  reducers: {
    updateField(state, action) {
      const { field, value } = action.payload;
      state.form[field] = value;
    },
    setChatDraft(state, action) {
      state.chatDraft = action.payload;
    },
    resetForm(state) {
      state.form = initialFormState;
      state.currentInteractionId = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(submitInteraction.pending, (state) => {
        state.status = "loading";
      })
      .addCase(submitInteraction.fulfilled, (state, action) => {
        state.status = "succeeded";
        state.currentInteractionId = action.payload.id;
      })
      .addCase(submitInteraction.rejected, (state, action) => {
        state.status = "failed";
        state.error = action.error.message;
      })
      .addCase(sendChatMessage.pending, (state) => {
        state.chatMessages.push({ role: "user", text: state.chatDraft });
        state.chatDraft = "";
      })
      .addCase(sendChatMessage.fulfilled, (state, action) => {
        state.chatMessages.push({ role: "ai", text: action.payload.reply });
        const interaction = action.payload.interaction;
        if (interaction) {
          state.currentInteractionId = interaction.id;
          // Sync the structured form with what the agent extracted, so the
          // chat + form stay consistent (same underlying Interaction row).
          state.form.hcpName = interaction.hcp_name || state.form.hcpName;
          state.form.interactionType = interaction.interaction_type;
          state.form.attendees = interaction.attendees;
          state.form.topicsDiscussed = interaction.topics_discussed || "";
          state.form.materialsShared = interaction.materials_shared;
          state.form.samplesDistributed = interaction.samples_distributed;
          state.form.sentiment = interaction.sentiment;
          state.form.outcomes = interaction.outcomes || "";
          state.form.followUpActions = interaction.follow_up_actions || "";
          state.form.aiSuggestedFollowups = interaction.ai_suggested_followups || [];
        }
      });
  },
});

export const { updateField, setChatDraft, resetForm } = interactionSlice.actions;
export default interactionSlice.reducer;
