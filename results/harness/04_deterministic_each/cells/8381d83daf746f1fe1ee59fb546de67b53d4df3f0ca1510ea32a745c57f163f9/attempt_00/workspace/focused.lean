lemma Typing.progress (der : Typing [] t τ) : t.Value ∨ ∃ t', t ⭢βᵛ t' := by
  generalize eq : [] = Γ at der
  induction der <;> subst eq
  case var mem => simpa using mem
  case abs L h _ => exact .inl (.abs (Typing.abs L h).wf.2.1)
  case tabs L h _ => exact .inl (.tabs (Typing.tabs L h).wf.2.1)
  case sub ih => exact ih rfl
  case' app l r ih_l ih_r =>
    have := l.wf.2.1
    have := r.wf.2.1
    rcases ih_l rfl with vl | ⟨_, hl⟩
    case' inl =>
      rcases ih_r rfl with vr | ⟨_, hr⟩
      case' inl => obtain ⟨_, _, rfl⟩ := l.canonical_form_abs vl
  case' tapp der sub ih =>
    have := der.wf.2.1
    have := (sub.wf _ _ _).2.1.lc
    rcases ih rfl with val | ⟨_, red⟩
    case' inl => obtain ⟨_, _, rfl⟩ := der.canonical_form_tabs val
  case' let' L der h ih _ =>
    have := (body_let.mp (Typing.let' L der h).wf.2.1).2
    rcases ih rfl with val | ⟨_, red⟩
  case' inl ih | inr ih => rcases ih rfl with val | ⟨_, red⟩
  case' case L der h₂ h₃ ih _ _ =>
    have ⟨_, b₂, b₃⟩ := body_case.mp (Typing.case L der h₂ h₃).wf.2.1
    rcases ih rfl with val | ⟨_, red⟩
    case' inl => obtain ⟨_, h | h⟩ := der.canonical_form_sum val <;> subst h <;> cases val
  all_goals first
    | (left; constructor; assumption)
    | (right; exact ⟨_, by solve_by_elim [Red.abs, Red.appᵣ, Red.tabs, Red.let_body, Red.case_inl, Red.case_inr]⟩)
