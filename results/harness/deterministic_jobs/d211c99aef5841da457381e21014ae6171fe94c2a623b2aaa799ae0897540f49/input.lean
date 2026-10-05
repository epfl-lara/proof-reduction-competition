theorem bisimilarity_congr_choice :
    (p ~[lts (defs := defs)] q) → (choice p r) ~[lts (defs := defs)] (choice q r) := by
  intro h
  refine ⟨(fun s t => s ~[lts (defs := defs)] t ∨
    (s = choice p r ∧ t = choice q r)), ?_, ?_⟩
  · exact Or.inr ⟨rfl, rfl⟩
  · intro s t hr μ
    rcases hr with hb | ⟨rfl, rfl⟩
    · constructor
      · intro s' hs
        obtain ⟨t', ht, hb'⟩ := hb.follow_fst hs
        exact ⟨t', ht, Or.inl hb'⟩
      · intro t' ht
        obtain ⟨s', hs, hb'⟩ := hb.follow_snd ht
        exact ⟨s', hs, Or.inl hb'⟩
    · constructor
      · intro s' hs
        cases hs with
        | choiceL hp =>
            obtain ⟨q', hq, hb'⟩ := h.follow_fst hp
            exact ⟨q', Tr.choiceL hq, Or.inl hb'⟩
        | choiceR hr =>
            exact ⟨s', Tr.choiceR hr, Or.inl (HomBisimilarity.refl _)⟩
      · intro t' ht
        cases ht with
        | choiceL hq =>
            obtain ⟨p', hp, hb'⟩ := h.follow_snd hq
            exact ⟨p', Tr.choiceL hp, Or.inl hb'⟩
        | choiceR hr =>
            exact ⟨t', Tr.choiceR hr, Or.inl (HomBisimilarity.refl _)⟩