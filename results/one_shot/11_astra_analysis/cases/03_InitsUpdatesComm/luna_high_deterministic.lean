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
  refine ⟨updatedStates σ ks' vs', rfl, ?_⟩
  have Hk : isDefined σ' ks := UpdateStatesDefined Hup
  have Hlen1 := InitStatesLength Hinit
  have Hlen2 := UpdateStatesLength Hup
  induction Hup generalizing σ''
  case update_none =>
    simp_all
    refine ⟨updatedStatesInit Hlen1 (InitStatesNotDefined Hinit) (InitStatesNodup Hinit), ?_⟩
    simp [InitStatesUpdated Hinit]
    exact UpdateStates.update_none
  case update_some σ x v σ₀ xs vs σ₁ Hup Hups ih =>
    refine ⟨?_, ?_⟩
    · apply updatedStatesInit Hlen1
      apply UpdateStateNotDefMonotone' ?_ Hup
      apply UpdateStatesNotDefMonotone' ?_ Hups
      exact InitStatesNotDefined Hinit
      exact InitStatesNodup Hinit
    · apply UpdateStates.update_some (σ':=updatedStates σ₀ ks' vs')
      · simp [UpdateStateUpdated Hup, updatedStates]
        rw [← updatedStateComm']
        · have Hdef := UpdateStateDefined' Hup
          simp [isDefined, Option.isSome] at Hdef
          split at Hdef <;> simp_all
          next val heq =>
          apply updatedStateUpdate (v':=val)
          apply InitStatesSomeMonotone heq
          apply updatedStatesInit
          · omega
          · apply UpdateStateNotDefMonotone' ?_ Hup
            apply UpdateStatesNotDefMonotone' ?_ Hups
            apply InitStatesNotDefined Hinit
          · exact InitStatesNodup Hinit
        · rw [List.unzip_zip] <;> simp_all
          have Hnd := InitStatesNotDefined Hinit
          simp only [isDefined] at *
          apply Not.intro
          intro Hin
          specialize Hnd _ Hin
          simp_all
      · apply ((ih Hinit ?_ ?_).2)
        · exact UpdateStatesDefined Hups <;> simp_all
        · exact UpdateStatesLength Hups
