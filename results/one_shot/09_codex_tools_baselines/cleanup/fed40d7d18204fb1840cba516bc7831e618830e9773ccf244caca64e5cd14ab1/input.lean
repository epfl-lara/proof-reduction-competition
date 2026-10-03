theorem bisimilarity_congr_choice :
    (p ~[lts (defs := defs)] q) → (choice p r) ~[lts (defs := defs)] (choice q r) := by
  intro h
  refine ⟨@ChoiceBisim _ _ defs, .choice h, ?_⟩
  intro s1 s2 hr μ
  cases hr with
  | choice hb =>
    constructor
    · intro s' ht
      cases ht with
      | choiceL ht =>
        obtain ⟨q', hq, h'⟩ := hb.follow_fst ht
        exact ⟨q', Tr.choiceL hq, .bisim h'⟩
      | choiceR ht =>
        exact ⟨_, Tr.choiceR ht, .bisim (HomBisimilarity.refl _)⟩
    · intro s' ht
      cases ht with
      | choiceL ht =>
        obtain ⟨p', hp, h'⟩ := hb.follow_snd ht
        exact ⟨p', Tr.choiceL hp, .bisim h'⟩
      | choiceR ht =>
        exact ⟨_, Tr.choiceR ht, .bisim (HomBisimilarity.refl _)⟩
  | bisim hb =>
    constructor
    · intro s' ht
      obtain ⟨q', hq, h'⟩ := hb.follow_fst ht
      exact ⟨q', hq, .bisim h'⟩
    · intro s' ht
      obtain ⟨p', hp, h'⟩ := hb.follow_snd ht
      exact ⟨p', hp, .bisim h'⟩