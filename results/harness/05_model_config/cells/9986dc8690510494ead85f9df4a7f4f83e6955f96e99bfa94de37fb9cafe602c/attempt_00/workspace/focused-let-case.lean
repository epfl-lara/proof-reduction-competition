lemma Typing.progress (der : Typing [] t τ) : t.Value ∨ ∃ t', t ⭢βᵛ t' := by
  generalize eq : [] = Γ at der
  have der' : Typing Γ t τ := der
  induction der <;> subst eq
  case var mem => simpa using mem
  case abs | tabs => left; constructor; exact der'.wf.2.1
  case app l r ih_l ih_r =>
    right
    rcases ih_l rfl l with vl | ⟨t₁', hl⟩
    · rcases ih_r rfl r with vr | ⟨t₂', hr⟩
      · obtain ⟨σ, b, rfl⟩ := l.canonical_form_abs vl
        exact ⟨_, .abs vl.lc vr⟩
      · exact ⟨_, .appᵣ vl hr⟩
    · exact ⟨_, .appₗ r.wf.2.1 hl⟩
  case tapp d sub ih =>
    right
    have lc := (sub.wf _ _ _).2.1.lc
    rcases ih rfl d with v | ⟨t', h⟩
    · obtain ⟨σ, b, rfl⟩ := d.canonical_form_tabs v
      exact ⟨_, .tabs v.lc lc⟩
    · exact ⟨_, .tapp lc h⟩
  case let' d _ ih _ =>
    have body := (body_let.mp der'.wf.2.1).2
    have := ih rfl d
    grind only [→ Red.let_body, → Red.let_bind]
  case inl d _ ih | inr d _ ih =>
    rcases ih rfl d with v | ⟨t', h⟩
    · left; constructor; exact v
    · exact Or.inr ⟨_, by constructor; exact h⟩
  case case d _ _ ih _ _ =>
    right
    have bodies := (body_case.mp der'.wf.2.1).2
    rcases ih rfl d with v | ⟨t', h⟩
    · obtain ⟨b, rfl | rfl⟩ := d.canonical_form_sum v <;>
        grind only [cases Value, → Red.case_inl, → Red.case_inr]
    · exact ⟨_, .case h bodies.1 bodies.2⟩
  case sub d _ ih => exact ih rfl d
