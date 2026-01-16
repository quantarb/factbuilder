from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Literal
import pandas as pd
from datetime import date, datetime
import hashlib
import json
from django.db.models import Sum
from finance.models import BankTransaction, CreditCardTransaction, Account
from facts.models import FactDefinition, FactDefinitionVersion, FactInstance, FactInstanceDependency

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
    parameters_schema: Dict[str, Any] = field(default_factory=dict)
    output_template: Optional[str] = None
    version_obj: Optional[FactDefinitionVersion] = None # Link to DB version

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
        self._instances: Dict[str, FactInstance] = {}

    def set(self, fact_id: str, instance: FactInstance):
        self._instances[fact_id] = instance

    def get(self, fact_id: str) -> Optional[FactInstance]:
        return self._instances.get(fact_id)

    def has(self, fact_id: str) -> bool:
        return fact_id in self._instances

def normalize_context(context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize context for hashing:
    - Sort keys
    - Remove transient keys (user object, session IDs)
    - Convert dates to ISO strings
    """
    clean_ctx = {}
    for k, v in context.items():
        if k in ['user', 'request', 'session_id']:
            continue
        if isinstance(v, (date, datetime)):
            clean_ctx[k] = v.isoformat()
        else:
            clean_ctx[k] = v
    return clean_ctx

def hash_context(context: Dict[str, Any]) -> str:
    """SHA256 hash of normalized context."""
    norm = normalize_context(context)
    s = json.dumps(norm, sort_keys=True)
    return hashlib.sha256(s.encode('utf-8')).hexdigest()

def resolve_fact(reg: FactRegistry, store: FactStore, fact_id: str, context: Dict[str, Any] = None) -> FactInstance:
    if context is None:
        context = {}
        
    # Check in-memory store first
    if store.has(fact_id):
        return store.get(fact_id)

    spec = reg.spec(fact_id)
    if not spec:
        raise ValueError(f"Fact {fact_id} not registered")

    # Check DB cache if we have a version object
    ctx_hash = hash_context(context)
    if spec.version_obj:
        cached = FactInstance.objects.filter(
            fact_version=spec.version_obj,
            context_hash=ctx_hash,
            status='success'
        ).first()
        if cached:
            store.set(fact_id, cached)
            return cached

    # Resolve dependencies
    dep_instances = {}
    for dep_id in spec.requires:
        dep_instances[dep_id] = resolve_fact(reg, store, dep_id, context)

    # Prepare values for producer (Hydrate DataFrames if needed)
    dep_values = {}
    for k, inst in dep_instances.items():
        val = inst.value
        if val is not None:
            dep_spec = reg.spec(k)
            # If the dependency is a dataframe type but stored as a list of dicts, convert it
            if dep_spec and dep_spec.data_type == 'dataframe' and isinstance(val, list):
                try:
                    val = pd.DataFrame(val)
                except Exception:
                    pass # Keep as list if conversion fails
        dep_values[k] = val

    # Execute producer
    try:
        if spec.producer is None:
             raise ValueError(f"Fact {fact_id} has no producer")
        
        value = spec.producer(dep_values, context)
        status = 'success'
        error = None
    except Exception as e:
        value = None
        status = 'error'
        error = str(e)

    # Persist result if versioned
    instance = None
    if spec.version_obj:
        # Dehydrate DataFrames for storage
        value_to_store = value
        if isinstance(value, pd.DataFrame):
            # Convert dates to strings for JSON serialization
            df_copy = value.copy()
            for col in df_copy.columns:
                if pd.api.types.is_datetime64_any_dtype(df_copy[col]):
                    df_copy[col] = df_copy[col].dt.strftime('%Y-%m-%d')
                elif df_copy[col].dtype == 'object':
                     # Check if column contains date objects
                     try:
                         sample = df_copy[col].dropna().iloc[0]
                         if isinstance(sample, (date, datetime)):
                             df_copy[col] = df_copy[col].apply(lambda x: x.isoformat() if isinstance(x, (date, datetime)) else x)
                     except IndexError:
                         pass

            value_to_store = df_copy.to_dict(orient='records')
        else:
            value_to_store = value
            
        instance = FactInstance.objects.create(
            fact_version=spec.version_obj,
            context=normalize_context(context),
            context_hash=ctx_hash,
            value=value_to_store,
            status=status,
            error=error
        )
        # Link dependencies
        for dep_id, dep_inst in dep_instances.items():
            FactInstanceDependency.objects.create(
                parent_instance=instance,
                dependency_instance=dep_inst,
                dependency_fact_id=dep_id
            )
    else:
        # Ephemeral instance
        instance = FactInstance(
            value=value,
            status=status,
            error=error
        )

    store.set(fact_id, instance)
    
    if status == 'error':
        raise RuntimeError(f"Error computing {fact_id}: {error}")
        
    return instance

def to_dot(reg: FactRegistry) -> str:
    lines = ["digraph FactTaxonomy {", 'rankdir="LR";', 'node [shape=box];']
    for spec in reg.all_specs().values():
        label = f"{spec.id}\\n({spec.kind}, {spec.data_type})"
        lines.append(f'"{spec.id}" [label="{label}"];')
        for dep in spec.requires:
            lines.append(f'"{dep}" -> "{spec.id}";')
    lines.append("}")
    return "\n".join(lines)

# --- Registry Setup ---

def build_taxonomy() -> FactRegistry:
    reg = FactRegistry()
    
    # Load Approved Fact Versions from DB
    definitions = FactDefinition.objects.filter(is_active=True)
    
    for defn in definitions:
        # Get latest approved version
        version = defn.versions.filter(status='approved').order_by('-version').first()
        if not version:
            continue
            
        # Create producer
        producer_func = None
        
        if defn.id == 'all_transactions':
             producer_func = _get_all_transactions
        else:
            # Dynamic producer from code
            producer_func = create_dynamic_producer(version.code)
            
        if producer_func:
            reg.register(FactSpec(
                id=defn.id,
                kind="computed",
                data_type=defn.data_type,
                requires=version.requires,
                producer=producer_func,
                description=defn.description,
                parameters_schema=version.parameters_schema,
                output_template=version.output_template,
                version_obj=version
            ))

    return reg

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
        # Wrap code in a function
        wrapped_code = f"def dynamic_producer(deps, context):\n" + "\n".join(["    " + line for line in code_str.splitlines()])
        exec(wrapped_code, global_scope, local_scope)
        return local_scope['dynamic_producer']
    except Exception as e:
        print(f"Error compiling dynamic fact: {e}")
        return None

# --- Producers ---

def _get_all_transactions(deps: Dict[str, Any], context: Dict[str, Any]) -> List[Dict[str, Any]]:
    # Return list of dicts instead of DataFrame for JSON serialization
    user = context.get('user')
    bank_qs = BankTransaction.objects.all()
    cc_qs = CreditCardTransaction.objects.all()
    
    if user:
        bank_qs = bank_qs.filter(account__user=user)
        cc_qs = cc_qs.filter(account__user=user)
    
    bank_txs = list(bank_qs.values('posting_date', 'description', 'amount', 'type', 'account__name'))
    for tx in bank_txs:
        tx['date'] = tx.pop('posting_date').isoformat()
        tx['category'] = 'Bank Transaction'
        tx['amount'] = float(tx['amount'])
        
    cc_txs = list(cc_qs.values('transaction_date', 'description', 'amount', 'category', 'type', 'account__name'))
    for tx in cc_txs:
        tx['date'] = tx.pop('transaction_date').isoformat()
        tx['amount'] = float(tx['amount'])

    return bank_txs + cc_txs
