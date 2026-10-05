lemma Typing.progress (der : Typing [] t τ) : t.Value ∨ ∃ t', t ⭢βᵛ t' := by
  generalize eq : [] = Γ at der
  have lc := der.wf.2.1
  induction der <;> subst eq
  case var mem => simpa using mem
  case abs | tabs => left; constructor; exact lc
  case sub ih => exact ih rfl lc
  case' app l r ih ih_r => cases lc
  case' tapp der sub ih => cases lc
  case' let' ih _ => have ⟨_, body⟩ := body_let.mp lc
  case' case der _ _ ih _ _ => have ⟨_, b₂, b₃⟩ := body_case.mp lc
  case' inl ih | inr ih => cases lc
  all_goals rcases ih rfl (by assumption) with val | ⟨_, red⟩
  case' app.inl =>
    rcases ih_r rfl (by assumption) with vr | ⟨_, hr⟩
    case' inl => obtain ⟨_, _, rfl⟩ := l.canonical_form_abs val
  case' tapp.inl => obtain ⟨_, _, rfl⟩ := der.canonical_form_tabs val
  case' case.inl => obtain ⟨_, h | h⟩ := der.canonical_form_sum val <;> subst h <;> cases val
  all_goals first
    | (left; constructor; assumption)
    | (right; exact ⟨_, by solve_by_elim [Red.abs, Red.appᵣ, Red.tabs, Red.let_body, Red.case_inl, Red.case_inr]⟩)
