lemma Typing.progress (der : Typing [] t τ) : t.Value ∨ ∃ t', t ⭢βᵛ t' := by
  generalize eq : [] = Γ at der
  have der' : Typing Γ t τ := der
  induction der <;> subst eq
  case var => grind
  case app t₁ _ _ t₂ l r ih_l ih_r =>
    cases ih_l rfl l with
    | inl val_l =>
        cases ih_r rfl r with
        | inl val_r =>
            obtain ⟨σ, b, rfl⟩ := l.canonical_form_abs val_l
            exact Or.inr ⟨b ^ᵗᵗ t₂, Red.abs l.wf.2.1 val_r⟩
        | inr red_r =>
            obtain ⟨t₂', red_r⟩ := red_r
            exact Or.inr ⟨t₁.app t₂', Red.appᵣ val_l red_r⟩
    | inr red_l =>
        obtain ⟨t₁', red_l⟩ := red_l
        exact Or.inr ⟨t₁'.app t₂, Red.appₗ r.wf.2.1 red_l⟩
  case tapp σ' der _ ih =>
    cases ih rfl der with
    | inl val =>
        obtain ⟨_, b, rfl⟩ := der.canonical_form_tabs val
        exact Or.inr ⟨b ^ᵗᵞ σ', Red.tabs der.wf.2.1 (by grind)⟩
    | inr red =>
        obtain ⟨t', red⟩ := red
        exact Or.inr ⟨.tapp t' σ', Red.tapp (by grind) red⟩
  case let' t₁ σ t₂ τ L der _ ih _ =>
    cases ih rfl der with
    | inl val => exact Or.inr ⟨t₂ ^ᵗᵗ t₁, Red.let_body val (by grind)⟩
    | inr red =>
        obtain ⟨t₁', red⟩ := red
        exact Or.inr ⟨t₁'.let' t₂, Red.let_bind red (by grind)⟩
  case inl der _ ih =>
    cases ih rfl der with
    | inl val => exact Or.inl (.inl val)
    | inr red =>
        obtain ⟨t', red⟩ := red
        exact Or.inr ⟨.inl t', Red.inl red⟩
  case inr der _ ih =>
    cases ih rfl der with
    | inl val => exact Or.inl (.inr val)
    | inr red =>
        obtain ⟨t', red⟩ := red
        exact Or.inr ⟨.inr t', Red.inr red⟩
  case case t₁ _ _ t₂ _ t₃ _ der _ _ ih _ _ =>
    cases ih rfl der with
    | inl val =>
        obtain ⟨u, lr⟩ := der.canonical_form_sum val
        cases lr with
        | inl eq =>
            subst t₁
            cases val with
            | inl val_u => exact Or.inr ⟨t₂ ^ᵗᵗ u, Red.case_inl val_u (by grind) (by grind)⟩
        | inr eq =>
            subst t₁
            cases val with
            | inr val_u => exact Or.inr ⟨t₃ ^ᵗᵗ u, Red.case_inr val_u (by grind) (by grind)⟩
    | inr red =>
        obtain ⟨t₁', red⟩ := red
        exact Or.inr ⟨t₁'.case t₂ t₃, Red.case red (by grind) (by grind)⟩
  case sub => grind
  case abs σ _ τ L _ _ =>
    exact Or.inl (Value.abs (LC.abs L (by grind only [→ wf, cases Term.LC]) (by grind only [→ wf])))
  case tabs L _ _ =>
    exact Or.inl (Value.tabs (LC.tabs L (by grind only [→ wf, cases Term.LC]) (by grind only [→ wf])))
