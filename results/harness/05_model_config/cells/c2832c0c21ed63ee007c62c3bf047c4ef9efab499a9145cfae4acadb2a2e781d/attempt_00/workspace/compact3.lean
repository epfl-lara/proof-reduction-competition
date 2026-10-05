lemma Typing.progress (der : Typing [] t τ) : t.Value ∨ ∃ t', t ⭢βᵛ t' := by
  generalize eq : [] = Γ at der
  have lc := der.wf.2.1
  induction der <;> subst eq
  case var mem => simpa using mem
  case abs => exact .inl (.abs lc)
  case tabs => exact .inl (.tabs lc)
  case sub ih => exact ih rfl lc
  case app l r ih_l ih_r =>
    right
    rcases ih_l rfl l.wf.2.1 with vl | ⟨t', red⟩
    · have := ih_r rfl r.wf.2.1
      grind only [→ canonical_form_abs, → Value.lc, → Red.abs, → Red.appᵣ vl]
    · exact ⟨_, .appₗ r.wf.2.1 red⟩
  case tapp d s ih =>
    have := ih rfl d.wf.2.1
    have := s.wf.2.1.lc
    grind only [→ canonical_form_tabs, → Value.lc, → Red.tapp, → Red.tabs]
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
