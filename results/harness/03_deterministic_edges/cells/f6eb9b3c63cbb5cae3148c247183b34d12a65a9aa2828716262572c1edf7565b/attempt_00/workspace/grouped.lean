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
  case' let' => have b := (body_let.mp lc).2
  case' case => obtain ⟨a, b, c⟩ := body_case.mp lc
  case' tapp d _ ih | let' d _ ih _ | inl d _ ih | inr d _ ih | case d _ _ ih _ _ =>
    rcases ih rfl d with v | ⟨_, h⟩
  case' tapp.inl => obtain ⟨_, _, rfl⟩ := d.canonical_form_tabs v
  case' case.inl =>
    obtain ⟨_, e | e⟩ := d.canonical_form_sum v <;> subst e <;> cases v
  all_goals try exact .inl (by constructor; assumption)
  all_goals cases lc
  all_goals exact .inr ⟨_, by solve_by_elim [Red.abs, Red.appᵣ, Red.tabs,
    Red.let_body, Red.case_inl, Red.case_inr]⟩
