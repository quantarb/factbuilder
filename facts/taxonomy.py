from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Literal
import pandas as pd
from datetime import date, datetime
from django.db.models import Sum
from finance.models import BankTransaction, CreditCardTransaction, Account

# --- Fact Infrastructure ---

FactKind = Literal["observed", "computed"]
FactDataType = Literal["dataframe", "scalar", "dict", "list"]

@dataclass(frozen=True)
class FactSpec:
    id: str
    kind: FactKind
    data_type: FactDataType
    requires: List[str]
    producer: Optional[Callable[[Dict[str, Any], Dict[str, Any]], Any]]
    description: str
    # NEW: Metadata for schema and templating
    parameters_schema: Dict[str, Any] = field(default_factory=dict)
    output_template: Optional[str] = None

class FactRegistry:
    def __init__(self):
        self._specs: Dict[str, FactSpec] = {}

    def register(self, spec: FactSpec):
        self._specs[spec.id] = spec

    def spec(self, fact_id: str) -> FactSpec:
        return self._specs.get(fact_id)

    def all_specs(self) -> Dict[str, FactSpec]:
        return self._specs

class FactStore:
    def __init__(self):
        self._values: Dict[str, Any] = {}

    def set(self, fact_id: str, value: Any):
        self._values[fact_id] = value

    def get(self, fact_id: str):
        return self._values.get(fact_id)

    def has(self, fact_id: str) -> bool:
        return fact_id in self._values

def resolve_fact(reg: FactRegistry, store: FactStore, fact_id: str, context: Dict[str, Any] = None):
    if context is None:
        context = {}
        
    if store.has(fact_id):
        return store.get(fact_id)

    spec = reg.spec(fact_id)
    if not spec:
        raise ValueError(f"Fact {fact_id} not registered")

    if spec.producer is None:
        raise ValueError(f"Fact {fact_id} must be provided externally or have a producer")

    deps = {d: resolve_fact(reg, store, d, context) for d in spec.requires}
    value = spec.producer(deps, context)
    store.set(fact_id, value)
    return value

def to_dot(reg: FactRegistry) -> str:
    lines = ["digraph FactTaxonomy {", 'rankdir="LR";', 'node [shape=box];']
    for spec in reg.all_specs().values():
        label = f"{spec.id}\\n({spec.kind}, {spec.data_type})"
        lines.append(f'"{spec.id}" [label="{label}"];')
        for dep in spec.requires:
            lines.append(f'"{dep}" -> "{spec.id}";')
    lines.append("}")
    return "\n".join(lines)

# --- Producers ---

def _get_all_transactions(deps: Dict[str, Any], context: Dict[str, Any]) -> pd.DataFrame:
    user = context.get('user')
    bank_qs = BankTransaction.objects.all()
    cc_qs = CreditCardTransaction.objects.all()
    
    if user:
        bank_qs = bank_qs.filter(account__user=user)
        cc_qs = cc_qs.filter(account__user=user)
    
    bank_txs = list(bank_qs.values('posting_date', 'description', 'amount', 'type', 'account__name'))
    for tx in bank_txs:
        tx['date'] = tx.pop('posting_date')
        tx['category'] = 'Bank Transaction'
        
    cc_txs = list(cc_qs.values('transaction_date', 'description', 'amount', 'category', 'type', 'account__name'))
    for tx in cc_txs:
        tx['date'] = tx.pop('transaction_date')

    all_txs = bank_txs + cc_txs
    df = pd.DataFrame(all_txs)
    
    if not df.empty:
        df['date'] = pd.to_datetime(df['date']).dt.date
        df['amount'] = df['amount'].astype(float)
    else:
        df = pd.DataFrame(columns=['date', 'description', 'amount', 'type', 'account__name', 'category'])
        
    return df

# --- Registry Setup ---

def build_taxonomy() -> FactRegistry:
    reg = FactRegistry()
    
    # 1. Register Base Fact
    reg.register(FactSpec(
        id="all_transactions",
        kind="computed",
        data_type="dataframe",
        requires=[],
        producer=_get_all_transactions,
        description="All transactions from database normalized"
    ))
    
    # 2. Register Dynamic Facts from Database
    try:
        from facts.models import DynamicFact
        
        def create_dynamic_producer(code_str):
            local_scope = {}
            global_scope = {
                "pd": pd,
                "date": date,
                "datetime": datetime,
                "Sum": Sum,
                "BankTransaction": BankTransaction,
                "CreditCardTransaction": CreditCardTransaction,
                "Account": Account
            }
            try:
                wrapped_code = f"def dynamic_producer(deps, context):\n" + "\n".join(["    " + line for line in code_str.splitlines()])
                exec(wrapped_code, global_scope, local_scope)
                return local_scope['dynamic_producer']
            except Exception as e:
                print(f"Error compiling dynamic fact: {e}")
                return None

        for dyn_fact in DynamicFact.objects.filter(is_active=True):
            producer_func = create_dynamic_producer(dyn_fact.code)
            if producer_func:
                reg.register(FactSpec(
                    id=dyn_fact.id,
                    kind=dyn_fact.kind,
                    data_type=dyn_fact.data_type,
                    requires=dyn_fact.requires,
                    producer=producer_func,
                    description=dyn_fact.description,
                    # Load new metadata fields
                    parameters_schema=dyn_fact.parameters_schema,
                    output_template=dyn_fact.output_template
                ))
                
    except Exception as e:
        print(f"Could not load dynamic facts: {e}")

    return reg