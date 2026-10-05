theorem bisimilarity_congr_choice :
    (p ~[lts (defs := defs)] q) → (choice p r) ~[lts (defs := defs)] (choice q r) := by
  intro h
  refine ⟨@ChoiceBisim _ _ defs, ?_, ?_⟩
  · exact ChoiceBisim.choice h
  intro s1 s2 hr μ
  cases hr with
  | choice hpq =>
    constructor
    · intro s1' ht
      cases ht with
      | choiceL ht =>
        obtain ⟨s2', ht2, hb⟩ := hpq.follow_fst ht
        exact ⟨s2', Tr.choiceL ht2, ChoiceBisim.bisim hb⟩
      | choiceR ht => exact ⟨s1', Tr.choiceR ht, ChoiceBisim.bisim (HomBisimilarity.refl _)⟩
    · intro s2' ht
      cases ht with
      | choiceL ht =>
        obtain ⟨s1', ht1, hb⟩ := hpq.follow_snd ht
        exact ⟨s1', Tr.choiceL ht1, ChoiceBisim.bisim hb⟩
      | choiceR ht => exact ⟨s2', Tr.choiceR ht, ChoiceBisim.bisim (HomBisimilarity.refl _)⟩
  | bisim hpq =>
    constructor
    · intro s1' ht
      obtain ⟨s2', ht2, hb⟩ := hpq.follow_fst ht
      exact ⟨s2', ht2, ChoiceBisim.bisim hb⟩
    · intro s2' ht
      obtain ⟨s1', ht1, hb⟩ := hpq.follow_snd ht
      exact ⟨s1', ht1, ChoiceBisim.bisim hb⟩
