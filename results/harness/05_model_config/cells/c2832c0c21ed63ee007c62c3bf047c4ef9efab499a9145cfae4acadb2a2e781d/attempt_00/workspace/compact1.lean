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
    have := ih rfl d.wf.2.1
    grind only [→ Red.let_body, → Red.let_bind]
  case inl d _ ih | inr d _ ih =>
    rcases ih rfl d.wf.2.1 with v | ⟨_, v⟩ <;> [left; right] <;>
      repeat' first | assumption | constructor
  case case d _ _ ih _ _ =>
    obtain ⟨_, h₂, h₃⟩ := body_case.mp lc
    right
    rcases ih rfl d.wf.2.1 with v | ⟨t', red⟩
    · obtain ⟨b, rfl | rfl⟩ := d.canonical_form_sum v <;> cases v <;>
        solve_by_elim [Exists.intro, Red.case_inl, Red.case_inr]
    · exact ⟨_, .case red h₂ h₃⟩
