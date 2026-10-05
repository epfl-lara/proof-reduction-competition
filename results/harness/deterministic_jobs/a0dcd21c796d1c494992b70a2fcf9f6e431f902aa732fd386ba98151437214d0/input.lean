lemma Typing.progress (der : Typing [] t τ) : t.Value ∨ ∃ t', t ⭢βᵛ t' := by
  generalize eq : [] = Γ at der
  have der' : Typing Γ t τ := der
  induction der <;> subst eq
  case var mem => grind
  case app t₁ _ _ t₂ l r ih_l ih_r =>
    right
    rcases ih_l rfl l with val_l | ⟨t₁', red_l⟩
    · rcases ih_r rfl r with val_r | ⟨t₂', red_r⟩
      · obtain ⟨σ, u, h⟩ := l.canonical_form_abs val_l
        use u ^ᵗᵗ t₂
        grind
      · exact ⟨t₁.app t₂', Red.appᵣ val_l red_r⟩
    · exact ⟨t₁'.app t₂, Red.appₗ r.wf.2.1 red_l⟩
  case tapp σ' d sub ih =>
    have lcσ : σ'.LC := (sub.wf [] σ' _).2.1.lc
    right
    cases ih rfl d with
    | inl val =>
        obtain ⟨δ, u, h⟩ := d.canonical_form_tabs val
        exact ⟨u ^ᵗᵞ σ', by grind⟩
    | inr red =>
        obtain ⟨u, step⟩ := red
        exact ⟨.tapp u σ', Red.tapp lcσ step⟩
  case let' t₁ σ t₂ τ L der h ih _ =>
    have ⟨_, hb⟩ := Term.body_let.mp (Typing.let' L der h).wf.2.1
    right
    cases ih rfl der with
    | inl val => exact ⟨t₂ ^ᵗᵗ t₁, Red.let_body val hb⟩
    | inr red =>
        obtain ⟨t₁', step⟩ := red
        exact ⟨t₁'.let' t₂, Red.let_bind step hb⟩
  case inl der _ ih =>
    cases ih rfl der with
    | inl val => grind
    | inr red =>
        obtain ⟨u, step⟩ := red
        exact Or.inr ⟨.inl u, Red.inl step⟩
  case inr der _ ih =>
    cases ih rfl der with
    | inl val => grind
    | inr red =>
        obtain ⟨u, step⟩ := red
        exact Or.inr ⟨.inr u, Red.inr step⟩
  case case t₁ σ τ t₂ δ t₃ L der h₂ h₃ ih _ _ =>
    have ⟨_, hb₂, hb₃⟩ := Term.body_case.mp (Typing.case L der h₂ h₃).wf.2.1
    right
    cases ih rfl der with
    | inl val =>
        obtain ⟨u, h | h⟩ := der.canonical_form_sum val
        · subst t₁
          cases val with
          | inl vu => exact ⟨t₂ ^ᵗᵗ u, Red.case_inl vu hb₂ hb₃⟩
        · subst t₁
          cases val with
          | inr vu => exact ⟨t₃ ^ᵗᵗ u, Red.case_inr vu hb₂ hb₃⟩
    | inr red =>
        obtain ⟨u, step⟩ := red
        exact ⟨.case u t₂ t₃, Red.case step hb₂ hb₃⟩
  case sub => grind
  case abs σ body τ L h ih =>
    grind
  case tabs L h ih =>
    grind