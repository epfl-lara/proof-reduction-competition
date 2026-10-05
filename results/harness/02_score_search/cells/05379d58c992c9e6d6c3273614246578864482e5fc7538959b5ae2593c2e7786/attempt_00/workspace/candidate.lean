lemma Typing.progress (der : Typing [] t τ) : t.Value ∨ ∃ t', t ⭢βᵛ t' := by
  generalize eq : [] = Γ at der
  have lc := der.wf.2.1
  induction der <;> subst eq
  case app l r ih_l ih_r =>
    right
    rcases ih_l rfl l.wf.2.1 with v | ⟨t', h⟩
    · rcases ih_r rfl r.wf.2.1 with w | ⟨t', h⟩
      · obtain ⟨σ, b, rfl⟩ := l.canonical_form_abs v
        exact ⟨_, Red.abs v.lc w⟩
      · exact ⟨_, Red.appᵣ v h⟩
    · exact ⟨_, Red.appₗ r.wf.2.1 h⟩
  case tapp d s ih =>
    cases lc with | tapp lc ty =>
      rcases ih rfl lc with v | ⟨t', h⟩
      · obtain ⟨σ, b, rfl⟩ := d.canonical_form_tabs v
        exact .inr ⟨_, Red.tabs v.lc ty⟩
      · exact .inr ⟨_, Red.tapp ty h⟩
  case case d _ _ ih _ _ =>
    obtain ⟨lc, b, c⟩ := body_case.mp lc
    rcases ih rfl lc with v | ⟨t', h⟩
    · obtain ⟨t', rfl | rfl⟩ := d.canonical_form_sum v <;>
        cases v <;> exact .inr ⟨_, by solve_by_elim [Red.case_inl, Red.case_inr]⟩
    · exact .inr ⟨_, Red.case h b c⟩
  case let' d _ ih _ =>
    obtain ⟨lc, b⟩ := body_let.mp lc
    rcases ih rfl lc with v | ⟨t', h⟩
      <;> exact .inr ⟨_, by solve_by_elim [Red.let_body, Red.let_bind]⟩
  case inl d _ ih | inr d _ ih =>
    rcases ih rfl d.wf.2.1 with v | ⟨t', h⟩
    · exact .inl (by solve_by_elim [Value.inl, Value.inr])
    · exact .inr ⟨_, by solve_by_elim [Red.inl, Red.inr]⟩
  case abs => exact .inl (.abs lc)
  case tabs => exact .inl (.tabs lc)
  case sub d _ ih => exact ih rfl lc
  case var => grind
