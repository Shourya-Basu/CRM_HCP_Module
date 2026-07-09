import { createSlice, createAsyncThunk, nanoid } from "@reduxjs/toolkit";
import { api } from "../api/client";

const initialState = {
  form: {
    id: null,
    hcpName: "",
    interactionType: "Meeting",
    date: new Date().toISOString().slice(0, 10),
    time: new Date().toTimeString().slice(0, 5),
    attendees: "",
    topicsDiscussed: "",
    sentiment: "Neutral",
    materials: [],
    samples: [],
    outcomes: "",
    followUpActions: "",
  },
  aiFilledFields: [], 
  suggestedFollowUps: [],
  chat: {
    sessionId: nanoid(),
    messages: [
      {
        id: nanoid(),
        role: "assistant",
        text:
          'Log interaction details here (e.g., "Met Dr. Smith, discussed Product X efficacy, positive sentiment, shared brochure") or ask for help.',
      },
    ],
    isThinking: false,
  },
  saveStatus: "idle", 
  error: null,
};

export const submitStructuredInteraction = createAsyncThunk(
  "interaction/submitStructured",
  async (_, { getState }) => {
    const f = getState().interaction.form;
    return api.createInteraction({
      hcp_name: f.hcpName,
      interaction_type: f.interactionType,
      date: f.date,
      time: f.time,
      attendees: f.attendees,
      topics_discussed: f.topicsDiscussed,
      sentiment: f.sentiment,
      outcomes: f.outcomes,
      follow_up_actions: f.followUpActions,
      materials: f.materials.map((m) => ({ material_name: m })),
      samples: f.samples.map((s) => ({ sample_name: s, quantity: 1 })),
      source: "form",
    });
  }
);

export const sendChatMessage = createAsyncThunk(
  "interaction/sendChatMessage",
  async (message, { getState }) => {
    const sessionId = getState().interaction.chat.sessionId;
    return api.chat(message, sessionId);
  }
);

const interactionSlice = createSlice({
  name: "interaction",
  initialState,
  reducers: {
    fieldChanged(state, action) {
      const { field, value } = action.payload;
      state.form[field] = value;
    },
    materialAdded(state, action) {
      state.form.materials.push(action.payload);
    },
    sampleAdded(state, action) {
      state.form.samples.push(action.payload);
    },
    userMessageAppended(state, action) {
      state.chat.messages.push({ id: nanoid(), role: "user", text: action.payload });
    },
    formReset(state) {
      state.form = { ...initialState.form, date: new Date().toISOString().slice(0, 10) };
      state.aiFilledFields = [];
      state.suggestedFollowUps = [];
      state.saveStatus = "idle";
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(submitStructuredInteraction.pending, (state) => {
        state.saveStatus = "saving";
      })
      .addCase(submitStructuredInteraction.fulfilled, (state, action) => {
        state.saveStatus = "saved";
        state.form.id = action.payload.id;
      })
      .addCase(submitStructuredInteraction.rejected, (state, action) => {
        state.saveStatus = "error";
        state.error = action.error.message;
      })
      .addCase(sendChatMessage.pending, (state) => {
        state.chat.isThinking = true;
      })
      .addCase(sendChatMessage.fulfilled, (state, action) => {
        const data = action.payload;
        state.chat.isThinking = false;
        state.chat.messages.push({ id: nanoid(), role: "assistant", text: data.reply });

        if (data.interaction) {
          const i = data.interaction;
          const filled = [];
          const map = {
            hcpName: i.hcp_name,
            interactionType: i.interaction_type,
            date: i.date,
            time: i.time,
            attendees: i.attendees,
            topicsDiscussed: i.topics_discussed,
            sentiment: i.sentiment,
            outcomes: i.outcomes,
            followUpActions: i.follow_up_actions,
          };
          Object.entries(map).forEach(([field, value]) => {
            if (value) {
              state.form[field] = value;
              filled.push(field);
            }
          });
          state.form.id = i.id;
          state.aiFilledFields = filled;
        }
        state.suggestedFollowUps = data.suggested_follow_ups || [];
      })
      .addCase(sendChatMessage.rejected, (state, action) => {
        state.chat.isThinking = false;
        state.chat.messages.push({
          id: nanoid(),
          role: "assistant",
          text: `Sorry, something went wrong reaching the assistant (${action.error.message}).`,
        });
      });
  },
});

export const { fieldChanged, materialAdded, sampleAdded, userMessageAppended, formReset } =
  interactionSlice.actions;
export default interactionSlice.reducer;
