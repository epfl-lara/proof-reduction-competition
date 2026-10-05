lemma Typing.progress (der : Typing [] t τ) : t.Value ∨ ∃ t', t ⭢βᵛ t' := by
  generalize eq : [] = Γ at der
  induction der <;> subst eq
  case var mem => simpa using mem
  case abs L h _ => exact .inl (.abs (Typing.abs L h).wf.2.1)
  case tabs L h _ => exact .inl (.tabs (Typing.tabs L h).wf.2.1)
  case sub ih => exact ih rfl
  case app t₁ _ _ t₂ l r ih_l ih_r =>
    right
    rcases ih_l rfl with vl | ⟨t₁', hl⟩
    · rcases ih_r rfl with vr | ⟨t₂', hr⟩
      · obtain ⟨σ, b, rfl⟩ := l.canonical_form_abs vl
        exact ⟨_, .abs vl.lc vr⟩
      · exact ⟨_, .appᵣ vl hr⟩
    · exact ⟨_, .appₗ r.wf.2.1 hl⟩
  case tapp σ' der sub ih =>
    right
    have lc := (sub.wf _ _ _).2.1.lc
    rcases ih rfl with val | ⟨t', red⟩
    · obtain ⟨σ, b, rfl⟩ := der.canonical_form_tabs val
      exact ⟨_, .tabs val.lc lc⟩
    · exact ⟨_, .tapp lc red⟩
  case let' t₁ σ t₂ τ L der h ih _ =>
    right
    have body : t₂.body := ⟨L, fun x hx => (h x hx).wf.2.1⟩
    rcases ih rfl with val | ⟨t', red⟩
    · exact ⟨_, .let_body val body⟩
    · exact ⟨_, .let_bind red body⟩
  case inl der _ ih =>
    rcases ih rfl with val | ⟨t', red⟩
    · exact .inl (.inl val)
    · exact .inr ⟨_, .inl red⟩
  case inr der _ ih =>
    rcases ih rfl with val | ⟨t', red⟩
    · exact .inl (.inr val)
    · exact .inr ⟨_, .inr red⟩
  case case t₁ _ _ t₂ _ t₃ L der h₂ h₃ ih _ _ =>
    right
    have b₂ : t₂.body := ⟨L, fun x hx => (h₂ x hx).wf.2.1⟩
    have b₃ : t₃.body := ⟨L, fun x hx => (h₃ x hx).wf.2.1⟩
    rcases ih rfl with val | ⟨t', red⟩
    · obtain ⟨t', h | h⟩ := der.canonical_form_sum val <;> subst h <;> cases val
      · exact ⟨_, .case_inl (by assumption) b₂ b₃⟩
      · exact ⟨_, .case_inr (by assumption) b₂ b₃⟩
    · exact ⟨_, .case red b₂ b₃⟩
