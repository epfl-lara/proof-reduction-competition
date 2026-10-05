lemma Typing.progress (der : Typing [] t τ) : t.Value ∨ ∃ t', t ⭢βᵛ t' := by
  generalize eq : [] = Γ at der
  have lc := der.wf.2.1
  induction der <;> subst eq
  case var | sub => simp_all
  case abs | tabs => left; constructor; exact lc
  case' app l _ ih ih_r | tapp der _ ih | inl ih | inr ih => cases lc
  case' let' ih _ => have ⟨_, body⟩ := body_let.mp lc
  case' case der _ _ ih _ _ => have ⟨_, b₂, b₃⟩ := body_case.mp lc
  all_goals rcases ih rfl ‹_› with val | ⟨_, red⟩
  case' app.inl =>
    rcases ih_r rfl ‹_› with vr | ⟨_, hr⟩
    case' inl => obtain ⟨_, _, rfl⟩ := l.canonical_form_abs val
  case' tapp.inl => obtain ⟨_, _, rfl⟩ := der.canonical_form_tabs val
  case' case.inl => obtain ⟨_, rfl | rfl⟩ := der.canonical_form_sum val <;> cases val
  solve_by_elim* (maxDepth := 8) [Or.inr, Exists.intro, Red.abs, Red.appᵣ, Red.tabs, Red.let_body, Red.case_inl, Red.case_inr]
