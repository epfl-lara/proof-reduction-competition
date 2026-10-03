theorem InitsUpdatesComm
  {P : PureExpr} {σ σ' σ'' : SemanticStore P}
  {ks ks' : List P.Ident} {vs vs' : List P.Expr} :
  UpdateStates σ ks vs σ' →
  InitStates σ' ks' vs' σ'' →
  ∃ σ₁,
    σ₁ = (updatedStates σ ks' vs') ∧
    InitStates σ ks' vs' σ₁ ∧
    UpdateStates σ₁ ks vs σ'' := by
  intros Hup Hinit
  exists (updatedStates σ ks' vs')
  have Hk := UpdateStatesDefined Hup
  have Hlen1 := InitStatesLength Hinit
  induction Hup generalizing σ''
  case update_none =>
    refine ⟨rfl, updatedStatesInit Hlen1 (InitStatesNotDefined Hinit) (InitStatesNodup Hinit), ?_⟩
    rw [← InitStatesUpdated Hinit]
    constructor
  case update_some σ x v σ₀ xs vs σ₁ Hup Hups ih =>
    have Hb := updatedStatesInit Hlen1
      (UpdateStateNotDefMonotone' (UpdateStatesNotDefMonotone' (InitStatesNotDefined Hinit) Hups) Hup)
      (InitStatesNodup Hinit)
    refine ⟨rfl, Hb, ?_⟩
    apply UpdateStates.update_some (σ':=updatedStates σ₀ ks' vs')
    · simp [UpdateStateUpdated Hup, updatedStates]
      rw [← updatedStateComm']
      · have Hdef := UpdateStateDefined' Hup
        simp [isDefined, Option.isSome] at Hdef
        split at Hdef <;> norm_cast
        next val heq =>
          exact updatedStateUpdate (InitStatesSomeMonotone heq Hb)
      · rw [List.unzip_zip] <;> norm_cast
        have Hnd := InitStatesNotDefined Hinit
        simp only [isDefined] at *
        intro Hin
        specialize Hnd _ Hin
        simp_all
    · exact (ih Hinit (UpdateStatesDefined Hups)).2.2