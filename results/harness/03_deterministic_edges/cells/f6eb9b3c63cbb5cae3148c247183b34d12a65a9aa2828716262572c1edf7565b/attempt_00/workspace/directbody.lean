lemma Typing.progress (der : Typing [] t τ) : t.Value ∨ ∃ t', t ⭢βᵛ t' := by
  generalize eq : [] = Γ at der
  have der' := der
  induction der <;> subst eq <;> have lc := der'.wf.2.1
  case var mem => simpa using mem
  case sub d _ ih => exact ih rfl d
  case' app l r il ir =>
    rcases il rfl l with vl | ⟨_, hl⟩
    case' inl =>
      rcases ir rfl r with vr | ⟨_, hr⟩
      case' inl =>
        obtain ⟨_, _, rfl⟩ := l.canonical_form_abs vl
  case' tapp d _ ih | let' d _ ih _ | inl d _ ih | inr d _ ih | case d _ _ ih _ _ =>
    rcases ih rfl d with v | ⟨_, h⟩
  case' tapp.inl => obtain ⟨_, _, rfl⟩ := d.canonical_form_tabs v
  case' case.inl =>
    obtain ⟨_, rfl | rfl⟩ := d.canonical_form_sum v <;> cases v
  all_goals first
  | exact .inl (by constructor; assumption)
  | cases lc; exact .inr ⟨_, by solve_by_elim -symm (maxDepth := 7) [Exists.intro, Red.abs, Red.appᵣ, Red.tabs,
    Red.let_body, Red.case, Red.case_inl, Red.case_inr]⟩
