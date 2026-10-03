theorem bisimilarity_congr_choice :
    (p ~[lts (defs := defs)] q) → (choice p r) ~[lts (defs := defs)] (choice q r) := by
  intro h
  exists @ChoiceBisim _ _ defs
  constructor
  · exact ChoiceBisim.choice h
  intro s1 s2 rel μ
  constructor
  · intro s1' htr
    cases rel with
    | choice hbisim =>
      obtain ⟨_, hr, hb⟩ := hbisim
      cases htr with
      | choiceL htr =>
        obtain ⟨s2', htr2, hr2⟩ := hb.follow_fst hr htr
        exact ⟨s2', Tr.choiceL htr2,
          ChoiceBisim.bisim (hb.le_bisimilarity _ _ hr2)⟩
      | choiceR htr =>
        exact ⟨s1', Tr.choiceR htr,
          ChoiceBisim.bisim (HomBisimilarity.refl s1')⟩
    | bisim hbisim =>
      obtain ⟨_, hr, hb⟩ := hbisim
      obtain ⟨s2', htr2, hr2⟩ := hb.follow_fst hr htr
      exact ⟨s2', htr2, ChoiceBisim.bisim (hb.le_bisimilarity _ _ hr2)⟩
  · intro s2' htr
    cases rel with
    | choice hbisim =>
      obtain ⟨_, hr, hb⟩ := hbisim
      cases htr with
      | choiceL htr =>
        obtain ⟨s1', htr1, hr1⟩ := hb.follow_snd hr htr
        exact ⟨s1', Tr.choiceL htr1,
          ChoiceBisim.bisim (hb.le_bisimilarity _ _ hr1)⟩
      | choiceR htr =>
        exact ⟨s2', Tr.choiceR htr,
          ChoiceBisim.bisim (HomBisimilarity.refl s2')⟩
    | bisim hbisim =>
      obtain ⟨_, hr, hb⟩ := hbisim
      obtain ⟨s1', htr1, hr1⟩ := hb.follow_snd hr htr
      exact ⟨s1', htr1, ChoiceBisim.bisim (hb.le_bisimilarity _ _ hr1)⟩