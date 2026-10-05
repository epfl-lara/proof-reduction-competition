lemma Typing.progress (der : Typing [] t τ) : t.Value ∨ ∃ t', t ⭢βᵛ t' := by
  generalize eq : [] = Γ at der
  have der' := der
  induction der <;> subst eq
  case var mem => simp at mem
  case abs => exact .inl (.abs der'.wf.2.1)
  case tabs => exact .inl (.tabs der'.wf.2.1)
  case sub ih => exact ih rfl ‹_›
  case app l r il ir =>
    right
    rcases il rfl l with vl | ⟨u, hr⟩
    · rcases ir rfl r with vr | ⟨u, hr⟩
      · obtain ⟨σ, b, rfl⟩ := l.canonical_form_abs vl
        exact ⟨_, Red.abs vl.lc vr⟩
      · exact ⟨_, Red.appᵣ vl hr⟩
    · exact ⟨_, Red.appₗ r.wf.2.1 hr⟩
  case tapp der sub ih =>
    have := ih rfl der
    grind only [→ Sub.wf, → Ty.Wf.lc, → Value.lc, → canonical_form_tabs,
      → Red.tabs, → Red.tapp]
  case let' der _ ih _ =>
    have := ih rfl der
    have := (body_let.mp der'.wf.2.1).2
    grind only [→ Red.let_body, → Red.let_bind]
  case inl der _ ih =>
    have := ih rfl der
    grind only [→ Value.inl, → Red.inl]
  case inr der _ ih =>
    have := ih rfl der
    grind only [→ Value.inr, → Red.inr]
  case case der _ _ ih _ _ =>
    obtain ⟨_, b₂, b₃⟩ := body_case.mp der'.wf.2.1
    right
    rcases ih rfl der with val | ⟨u, hr⟩
    · obtain ⟨u, rfl | rfl⟩ := der.canonical_form_sum val
      · cases val with | inl v => exact ⟨_, Red.case_inl v b₂ b₃⟩
      · cases val with | inr v => exact ⟨_, Red.case_inr v b₂ b₃⟩
    · exact ⟨_, Red.case hr b₂ b₃⟩
