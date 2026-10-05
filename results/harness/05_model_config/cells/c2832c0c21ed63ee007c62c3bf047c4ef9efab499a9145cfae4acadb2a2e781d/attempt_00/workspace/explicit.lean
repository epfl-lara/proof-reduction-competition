lemma Typing.progress (der : Typing [] t τ) : t.Value ∨ ∃ t', t ⭢βᵛ t' := by
  generalize eq : [] = Γ at der
  have lc := der.wf.2.1
  induction der <;> subst eq
  case var mem => simpa using mem
  case abs => exact .inl (.abs lc)
  case tabs => exact .inl (.tabs lc)
  case sub ih => exact ih rfl lc
  case app t₁ _ _ t₂ l r ih_l ih_r =>
    right
    rcases ih_l rfl l.wf.2.1 with vl | ⟨t', red⟩
    · rcases ih_r rfl r.wf.2.1 with vr | ⟨t', red⟩
      · obtain ⟨σ, b, rfl⟩ := l.canonical_form_abs vl
        exact ⟨_, .abs vl.lc vr⟩
      · exact ⟨_, .appᵣ vl red⟩
    · exact ⟨_, .appₗ r.wf.2.1 red⟩
  case tapp σ' d s ih =>
    right
    rcases ih rfl d.wf.2.1 with v | ⟨t', red⟩
    · obtain ⟨σ, b, rfl⟩ := d.canonical_form_tabs v
      exact ⟨_, .tabs v.lc s.wf.2.1.lc⟩
    · exact ⟨_, .tapp s.wf.2.1.lc red⟩
  case let' d _ ih _ =>
    have h := body_let.mp lc
    right
    rcases ih rfl d.wf.2.1 with v | ⟨t', red⟩
    · exact ⟨_, .let_body v h.2⟩
    · exact ⟨_, .let_bind red h.2⟩
  case inl d _ ih =>
    rcases ih rfl d.wf.2.1 with v | ⟨t', red⟩
    · exact .inl (.inl v)
    · exact .inr ⟨_, .inl red⟩
  case inr d _ ih =>
    rcases ih rfl d.wf.2.1 with v | ⟨t', red⟩
    · exact .inl (.inr v)
    · exact .inr ⟨_, .inr red⟩
  case case d _ _ ih _ _ =>
    have h := body_case.mp lc
    right
    rcases ih rfl d.wf.2.1 with v | ⟨t', red⟩
    · obtain ⟨b, e | e⟩ := d.canonical_form_sum v
      · subst e
        cases v with | inl v => exact ⟨_, .case_inl v h.2.1 h.2.2⟩
      · subst e
        cases v with | inr v => exact ⟨_, .case_inr v h.2.1 h.2.2⟩
    · exact ⟨_, .case red h.2.1 h.2.2⟩
