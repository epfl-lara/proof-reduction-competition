lemma Typing.progress (der : Typing [] t τ) : t.Value ∨ ∃ t', t ⭢βᵛ t' := by
  generalize eq : [] = Γ at der
  have lc := der.wf.2.1
  induction der <;> subst eq
  case var mem => simp at mem
  case sub ih => exact ih rfl lc
  case' app l r il ir =>
    cases lc
    rcases il rfl l.wf.2.1 with vl | ⟨_, hl⟩
    rcases ir rfl r.wf.2.1 with vr | ⟨_, hr⟩
    obtain ⟨_, _, rfl⟩ := l.canonical_form_abs vl
  case' tapp d _ ih | let' d _ ih _ | case d _ _ ih _ _ => cases lc
  case' tapp | let' | inl d _ ih | inr d _ ih | case =>
    rcases ih rfl d.wf.2.1 with v | ⟨_, h⟩
  case' tapp.inl => obtain ⟨_, _, rfl⟩ := d.canonical_form_tabs v
  case' case.inl => obtain ⟨_, rfl | rfl⟩ := d.canonical_form_sum v <;> cases v
  all_goals first | (left; constructor; assumption) | right
  all_goals solve_by_elim (maxDepth := 8) [Exists.intro, Red.abs, Red.tabs, Red.case_inl, Red.case_inr,
    Red.let_body, Red.appᵣ, Red.case]