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
    right
    cases lc with | tapp lc ty =>
      rcases ih rfl lc with v | ⟨t', h⟩
      · obtain ⟨σ, b, rfl⟩ := d.canonical_form_tabs v
        exact ⟨_, Red.tabs v.lc ty⟩
      · exact ⟨_, Red.tapp ty h⟩
  case let' d _ ih _ =>
    right
    cases lc with | let' L lc body =>
      rcases ih rfl lc with v | ⟨t', h⟩
      · exact ⟨_, Red.let_body v ⟨L, body⟩⟩
      · exact ⟨_, Red.let_bind h ⟨L, body⟩⟩
  case inl d _ ih =>
    rcases ih rfl d.wf.2.1 with v | ⟨t', h⟩
    · exact .inl (.inl v)
    · exact .inr ⟨_, Red.inl h⟩
  case inr d _ ih =>
    rcases ih rfl d.wf.2.1 with v | ⟨t', h⟩
    · exact .inl (.inr v)
    · exact .inr ⟨_, Red.inr h⟩
  case case d _ _ ih _ _ =>
    right
    cases lc with | case L lc b c =>
      rcases ih rfl lc with v | ⟨t', h⟩
      · obtain ⟨t', h | h⟩ := d.canonical_form_sum v
        · subst h; cases v with | inl v => exact ⟨_, Red.case_inl v ⟨L, b⟩ ⟨L, c⟩⟩
        · subst h; cases v with | inr v => exact ⟨_, Red.case_inr v ⟨L, b⟩ ⟨L, c⟩⟩
      · exact ⟨_, Red.case h ⟨L, b⟩ ⟨L, c⟩⟩
  case abs => exact .inl (.abs lc)
  case tabs => exact .inl (.tabs lc)
  case sub d _ ih => exact ih rfl lc
  case var => grind
