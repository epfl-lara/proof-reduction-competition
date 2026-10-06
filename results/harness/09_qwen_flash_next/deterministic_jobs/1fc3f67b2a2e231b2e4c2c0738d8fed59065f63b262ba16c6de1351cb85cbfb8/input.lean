lemma Typing.progress (der : Typing [] t τ) : t.Value ∨ ∃ t', t ⭢βᵛ t' := by
  generalize eq : [] = Γ at der
  have d2 := der
  induction der <;> subst eq
  case var h => cases h
  case app l r i1 i2 =>
    right
    obtain v|⟨_, h⟩ := i1 rfl l
    · obtain w|⟨_, h2⟩ := i2 rfl r
      · obtain ⟨_, _, rfl⟩ := l.canonical_form_abs v
        exact ⟨_, .abs v.lc w⟩
      · exact ⟨_, .appᵣ v h2⟩
    · exact ⟨_, .appₗ r.wf.2.1 h⟩
  case tapp _ d s i =>
    right
    obtain v|⟨_, h⟩ := i rfl d
    · obtain ⟨_, _, rfl⟩ := d.canonical_form_tabs v
      exact ⟨_, .tabs v.lc s.wf.2.1.lc⟩
    · exact ⟨_, .tapp s.wf.2.1.lc h⟩
  case let' d _ i _ =>
    right
    obtain v|⟨_, h⟩ := i rfl d
    · exact ⟨_, .let_body v (body_let.mp d2.wf.2.1).2⟩
    · exact ⟨_, .let_bind h (body_let.mp d2.wf.2.1).2⟩
  case inl d _ i => exact (i rfl d).imp .inl fun ⟨_, h⟩ => ⟨_, .inl h⟩
  case inr d _ i => exact (i rfl d).imp .inr fun ⟨_, h⟩ => ⟨_, .inr h⟩
  case case d _ _ i _ _ =>
    right
    obtain ⟨_, b2, b3⟩ := body_case.mp d2.wf.2.1
    obtain v|⟨_, h⟩ := i rfl d
    · obtain ⟨u, rfl|rfl⟩ := d.canonical_form_sum v
      · cases v with | inl w => exact ⟨_, .case_inl w b2 b3⟩
      · cases v with | inr w => exact ⟨_, .case_inr w b2 b3⟩
    · exact ⟨_, .case h b2 b3⟩
  case sub | abs | tabs => grind