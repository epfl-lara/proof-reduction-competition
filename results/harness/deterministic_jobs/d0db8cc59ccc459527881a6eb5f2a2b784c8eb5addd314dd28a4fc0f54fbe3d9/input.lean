lemma Typing.progress (der : Typing [] t τ) : t.Value ∨ ∃ t', t ⭢βᵛ t' := by
  generalize eq : [] = Γ at der
  have lc := der.wf.2.1
  induction der <;> subst eq
  case var => grind
  case abs => exact .inl (.abs lc)
  case tabs => exact .inl (.tabs lc)
  case sub der _ ih => exact ih rfl lc
  case app l r ih_l ih_r =>
    right
    rcases ih_l rfl l.wf.2.1 with v | ⟨_, h⟩
    · rcases ih_r rfl r.wf.2.1 with w | ⟨_, h⟩
      · obtain ⟨_, _, rfl⟩ := l.canonical_form_abs v
        exact ⟨_, .abs v.lc w⟩
      · exact ⟨_, .appᵣ v h⟩
    · exact ⟨_, .appₗ r.wf.2.1 h⟩
  case tapp der _ ih =>
    cases lc with
    | tapp lc h =>
      right
      rcases ih rfl lc with v | ⟨_, step⟩
      · obtain ⟨_, _, rfl⟩ := der.canonical_form_tabs v
        exact ⟨_, .tabs v.lc h⟩
      · exact ⟨_, .tapp h step⟩
  case let' der _ ih _ =>
    obtain ⟨lc, body⟩ := body_let.mp lc
    right
    rcases ih rfl lc with v | ⟨_, h⟩
    · exact ⟨_, .let_body v body⟩
    · exact ⟨_, .let_bind h body⟩
  case inl der _ ih =>
    exact (ih rfl der.wf.2.1).imp Value.inl (fun ⟨_, h⟩ => ⟨_, .inl h⟩)
  case inr der _ ih =>
    exact (ih rfl der.wf.2.1).imp Value.inr (fun ⟨_, h⟩ => ⟨_, .inr h⟩)
  case case der _ _ ih _ _ =>
    obtain ⟨lc, b, c⟩ := body_case.mp lc
    right
    rcases ih rfl lc with v | ⟨_, h⟩
    · obtain ⟨_, h | h⟩ := der.canonical_form_sum v <;> subst h <;> cases v
      · exact ⟨_, .case_inl ‹_› b c⟩
      · exact ⟨_, .case_inr ‹_› b c⟩
    · exact ⟨_, .case h b c⟩