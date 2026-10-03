theorem bisimilarity_congr_choice :
    (p ~[lts (defs := defs)] q) → (choice p r) ~[lts (defs := defs)] (choice q r) := by
  intro h
  refine ⟨@ChoiceBisim _ _ defs, .choice h, ?_⟩
  intro s1 s2 hr μ
  cases hr with
  | choice h =>
    unfold lts
    constructor
    · intro s1' htr
      cases htr with
      | choiceL htr =>
        obtain ⟨s2', htr', hr'⟩ := h.follow_fst htr
        exact ⟨s2', Tr.choiceL htr', .bisim hr'⟩
      | choiceR htr =>
        exact ⟨s1', Tr.choiceR htr, .bisim (HomBisimilarity.refl _)⟩
    · intro s2' htr
      cases htr with
      | choiceL htr =>
        obtain ⟨s1', htr', hr'⟩ := h.follow_snd htr
        exact ⟨s1', Tr.choiceL htr', .bisim hr'⟩
      | choiceR htr =>
        exact ⟨s2', Tr.choiceR htr, .bisim (HomBisimilarity.refl _)⟩
  | bisim h =>
    constructor
    · intro s1' htr
      obtain ⟨s2', htr', hr'⟩ := h.follow_fst htr
      exact ⟨s2', htr', .bisim hr'⟩
    · intro s2' htr
      obtain ⟨s1', htr', hr'⟩ := h.follow_snd htr
      exact ⟨s1', htr', .bisim hr'⟩