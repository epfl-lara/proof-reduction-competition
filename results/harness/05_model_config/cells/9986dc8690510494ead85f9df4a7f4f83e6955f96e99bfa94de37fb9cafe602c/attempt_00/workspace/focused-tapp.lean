lemma Typing.progress (der : Typing [] t τ) : t.Value ∨ ∃ t', t ⭢βᵛ t' := by
  generalize eq : [] = Γ at der
  have der' := der
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
    have lc := (sub.wf _ _ _).2.1.lc
    have := ih rfl d
    grind only [→ canonical_form_tabs, → Value.lc, → Red.tabs, → Red.tapp]
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
    obtain ⟨_, b₂, b₃⟩ := body_case.mp der'.wf.2.1
    rcases ih rfl d with v | ⟨t', h⟩
    · obtain ⟨b, rfl | rfl⟩ := d.canonical_form_sum v <;>
        cases v <;> exact ⟨_, by solve_by_elim [Red.case_inl, Red.case_inr]⟩
    · exact ⟨_, .case h b₂ b₃⟩
  case sub d _ ih => exact ih rfl d
