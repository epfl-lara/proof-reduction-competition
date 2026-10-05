lemma Typing.progress (der : Typing [] t τ) : t.Value ∨ ∃ t', t ⭢βᵛ t' := by
  generalize eq : [] = Γ at der
  have der' : Typing Γ t τ := der
  induction der <;> subst eq
  case var mem => simp at mem
  case abs => exact .inl (.abs der'.wf.2.1)
  case tabs => exact .inl (.tabs der'.wf.2.1)
  case sub ih => exact ih rfl ‹_›
  case app t₁ _ _ t₂ l r ih_l ih_r =>
    right
    rcases ih_l rfl l with vl | ⟨u, hr⟩
    · rcases ih_r rfl r with vr | ⟨u, hr⟩
      · obtain ⟨σ, b, rfl⟩ := l.canonical_form_abs vl
        exact ⟨_, Red.abs vl.lc vr⟩
      · exact ⟨_, Red.appᵣ vl hr⟩
    · exact ⟨_, Red.appₗ r.wf.2.1 hr⟩
  case tapp σ' der sub ih =>
    have lc := (sub.wf _ _ _).2.1.lc
    right
    rcases ih rfl der with val | ⟨u, hr⟩
    · obtain ⟨σ, b, rfl⟩ := der.canonical_form_tabs val
      exact ⟨_, Red.tabs val.lc lc⟩
    · exact ⟨_, Red.tapp lc hr⟩
  case let' t₁ σ t₂ τ L der _ ih _ =>
    have body := (body_let.mp der'.wf.2.1).2
    right
    rcases ih rfl der with val | ⟨u, hr⟩
    · exact ⟨_, Red.let_body val body⟩
    · exact ⟨_, Red.let_bind hr body⟩
  case inl der _ ih =>
    rcases ih rfl der with val | ⟨u, hr⟩
    · exact .inl (.inl val)
    · exact .inr ⟨_, Red.inl hr⟩
  case inr der _ ih =>
    rcases ih rfl der with val | ⟨u, hr⟩
    · exact .inl (.inr val)
    · exact .inr ⟨_, Red.inr hr⟩
  case case t₁ _ _ t₂ _ t₃ _ der _ _ ih _ _ =>
    obtain ⟨_, b₂, b₃⟩ := body_case.mp der'.wf.2.1
    right
    rcases ih rfl der with val | ⟨u, hr⟩
    · obtain ⟨u, h | h⟩ := der.canonical_form_sum val
      · subst h
        cases val with | inl v => exact ⟨_, Red.case_inl v b₂ b₃⟩
      · subst h
        cases val with | inr v => exact ⟨_, Red.case_inr v b₂ b₃⟩
    · exact ⟨_, Red.case hr b₂ b₃⟩
