lemma Typing.progress (der : Typing [] t τ) : t.Value ∨ ∃ t', t ⭢βᵛ t' := by
  generalize eq : [] = Γ at der
  have der' := der
  induction der <;> subst eq <;> have lc := der'.wf.2.1
  case var mem => simpa using mem
  case sub d _ ih => exact ih rfl d
  case' app l r il ir =>
    cases lc
    rcases il rfl l with vl | ⟨_, hl⟩
    case' inl =>
      rcases ir rfl r with vr | ⟨_, hr⟩
      case' inl =>
        obtain ⟨_, _, rfl⟩ := l.canonical_form_abs vl
  case' tapp σ' d _ ih =>
    cases lc
    rcases ih rfl d with v | ⟨_, h⟩
    case' inl =>
      obtain ⟨_, _, rfl⟩ := d.canonical_form_tabs v
  case' let' d _ ih _ =>
    have b := (body_let.mp lc).2
    rcases ih rfl d with v | ⟨_, h⟩
  case' inl d _ ih | inr d _ ih =>
    rcases ih rfl d with v | ⟨_, h⟩
  case' case d _ _ ih _ _ =>
    obtain ⟨_, b, c⟩ := body_case.mp lc
    rcases ih rfl d with v | ⟨_, h⟩
    case' inl =>
      obtain ⟨_, e | e⟩ := d.canonical_form_sum v <;> subst e <;> cases v
  all_goals first
  | exact .inl (by constructor; assumption)
  | exact .inr ⟨_, by solve_by_elim [Red.abs, Red.appᵣ, Red.tabs,
      Red.let_body, Red.case_inl, Red.case_inr]⟩
