lemma Typing.progress (der : Typing [] t τ) : t.Value ∨ ∃ t', t ⭢βᵛ t' := by
  generalize eq : [] = Γ at der
  have der' : Typing Γ t τ := der
  induction der <;> subst eq
  case var mem => simpa using mem
  case abs => exact Or.inl (.abs der'.wf.2.1)
  case tabs => exact Or.inl (.tabs der'.wf.2.1)
  case app t₁ _ _ t₂ l r ih_l ih_r =>
    right
    rcases ih_l rfl l with vl | ⟨t₁', hl⟩
    · rcases ih_r rfl r with vr | ⟨t₂', hr⟩
      · obtain ⟨σ, b, rfl⟩ := l.canonical_form_abs vl
        exact ⟨_, .abs vl.lc vr⟩
      · exact ⟨_, .appᵣ vl hr⟩
    · exact ⟨_, .appₗ r.wf.2.1 hl⟩
  case tapp σ' d sub ih =>
    right
    have lc : σ'.LC := by grind
    rcases ih rfl d with v | ⟨t', h⟩
    · obtain ⟨σ, b, rfl⟩ := d.canonical_form_tabs v
      exact ⟨_, .tabs v.lc lc⟩
    · exact ⟨_, .tapp lc h⟩
  case let' t₁ σ t₂ τ L d _ ih _ =>
    right
    have body := (body_let.mp der'.wf.2.1).2
    rcases ih rfl d with v | ⟨t', h⟩
    · exact ⟨_, .let_body v body⟩
    · exact ⟨_, .let_bind h body⟩
  case inl d _ ih =>
    rcases ih rfl d with v | ⟨t', h⟩
    · exact Or.inl (.inl v)
    · exact Or.inr ⟨_, .inl h⟩
  case inr d _ ih =>
    rcases ih rfl d with v | ⟨t', h⟩
    · exact Or.inl (.inr v)
    · exact Or.inr ⟨_, .inr h⟩
  case case t₁ _ _ t₂ _ t₃ _ d _ _ ih _ _ =>
    right
    have bodies := (body_case.mp der'.wf.2.1).2
    rcases ih rfl d with v | ⟨t', h⟩
    · obtain ⟨b, rfl | rfl⟩ := d.canonical_form_sum v
      · cases v with
        | inl v => exact ⟨_, .case_inl v bodies.1 bodies.2⟩
      · cases v with
        | inr v => exact ⟨_, .case_inr v bodies.1 bodies.2⟩
    · exact ⟨_, .case h bodies.1 bodies.2⟩
  case sub d _ ih => exact ih rfl d
