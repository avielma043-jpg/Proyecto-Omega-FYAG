
import { create } from "zustand";

export const useAuthStore = create((set) => ({
  session: null,

  saveSession: (session) => {
    set({ session });
  },

  clearSession: () => {
    set({ session: null });
  },
}));
