lemma Typing.progress (der : Typing [] t τ) : t.Value ∨ ∃ t', t ⭢βᵛ t' := by
  generalize eq : [] = Γ at der
  induction der <;> subst eq
  case var mem => cases mem
  case' app l r ihl ihr =>
    right; rcases ihl rfl with vl | red
    · rcases ihr rfl with vr | red
      · obtain ⟨_, _, rfl⟩ := canonical_form_abs vl l
        exact ⟨_, .abs vl.lc vr⟩
      · exact ⟨_, .appᵣ vl red.choose_spec⟩
    · exact ⟨_, .appₗ r.wf.2.1 red.choose_spec⟩
  case' tapp der sub ih =>
    right; rcases ih rfl with val | red
    · obtain ⟨_, _, rfl⟩ := canonical_form_tabs val der
      exact ⟨_, .tabs val.lc sub.wf.2.1.lc⟩
    · exact ⟨_, .tapp sub.wf.2.1.lc red.choose_spec⟩
  case' let' L der h ih _ =>
    have b := body_let.mp (Typing.let' L der h).wf.2.1
    right; rcases ih rfl with val | red
    · exact ⟨_, .let_body val b.2⟩
    · exact ⟨_, .let_bind red.choose_spec b.2⟩
  case' inl ih => exact (ih rfl).imp Value.inl fun red => ⟨_, .inl red.choose_spec⟩
  case' inr ih => exact (ih rfl).imp Value.inr fun red => ⟨_, .inr red.choose_spec⟩
  case' case L der h₂ h₃ ih _ _ =>
    have b := body_case.mp (Typing.case L der h₂ h₃).wf.2.1
    right; rcases ih rfl with val | red
    · obtain ⟨_, rfl|rfl⟩ := canonical_form_sum val der
      · exact ⟨_, .case_inl (by cases val; assumption) b.2.1 b.2.2⟩
      · exact ⟨_, .case_inr (by cases val; assumption) b.2.1 b.2.2⟩
    · exact ⟨_, .case red.choose_spec b.2.1 b.2.2⟩
  case' sub ih => exact ih rfl
  case' abs L h _ => exact .inl (.abs (Typing.abs L h).wf.2.1)
  case' tabs L h _ => exact .inl (.tabs (Typing.tabs L h).wf.2.1)