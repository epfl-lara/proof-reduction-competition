theorem bisimilarity_congr_choice :
    (p ~[lts (defs := defs)] q) → (choice p r) ~[lts (defs := defs)] (choice q r) := by
  intro h
  refine ⟨ChoiceBisim, ChoiceBisim.choice h, ?_⟩
  intro s1 s2 hr μ
  cases hr with
  | choice h =>
    constructor
    · intro s' htr
      cases htr with
      | choiceL htr =>
        obtain ⟨s', htr', hr'⟩ := h.follow_fst htr
        exact ⟨s', Tr.choiceL htr', ChoiceBisim.bisim hr'⟩
      | choiceR htr =>
        exact ⟨s', Tr.choiceR htr, ChoiceBisim.bisim (HomBisimilarity.refl _)⟩
    · intro s' htr
      cases htr with
      | choiceL htr =>
        obtain ⟨s', htr', hr'⟩ := h.follow_snd htr
        exact ⟨s', Tr.choiceL htr', ChoiceBisim.bisim hr'⟩
      | choiceR htr =>
        exact ⟨s', Tr.choiceR htr, ChoiceBisim.bisim (HomBisimilarity.refl _)⟩
  | bisim h =>
    constructor
    · intro s' htr
      obtain ⟨s', htr', hr'⟩ := h.follow_fst htr
      exact ⟨s', htr', ChoiceBisim.bisim hr'⟩
    · intro s' htr
      obtain ⟨s', htr', hr'⟩ := h.follow_snd htr
      exact ⟨s', htr', ChoiceBisim.bisim hr'⟩
