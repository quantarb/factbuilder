from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Literal
import pandas as pd
from datetime import date, datetime
import hashlib
import json
import multiprocessing
import queue
from django.db.models import Sum
from django.db import transaction, IntegrityError
from finance.models import BankTransaction, CreditCardTransaction, Account
from facts.models import FactDefinition, FactDefinitionVersion, FactInstance, FactInstanceDependency
from facts.context import normalize_context, hash_context
from facts.schema_validation import validate_context
from facts.graph import build_dependency_graph, detect_cycles
from facts.executor import execute_expression

# --- Fact Infrastructure ---

FactKind = Literal["observed", "computed"]
FactDataType = Literal["dataframe", "scalar", "dict", "list", "distribution"]

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

def resolve_fact(reg: FactRegistry, store: FactStore, fact_id: str, context: Dict[str, Any] = None) -> FactInstance:
    if context is None:
        context = {}
        
    # Check in-memory store first
    if store.has(fact_id):
        return store.get(fact_id)

    spec = reg.spec(fact_id)
    if not spec:
        raise ValueError(f"Fact {fact_id} not registered")

    # Validate context against schema if available
    if spec.parameters_schema:
        try:
            validate_context(context, spec.parameters_schema)
        except ValueError as e:
            # Create error instance
            instance = FactInstance(
                status='error',
                error=str(e),
                context=normalize_context(context),
                context_hash=hash_context(context)
            )
            store.set(fact_id, instance)
            return instance

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
        
        # Use safe execution if it's a dynamic producer (from DB)
        if spec.version_obj:
            value = safe_execute(spec.producer, dep_values, context, spec.version_obj.logic_type)
        else:
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
            
        try:
            with transaction.atomic():
                instance, created = FactInstance.objects.get_or_create(
                    fact_version=spec.version_obj,
                    context_hash=ctx_hash,
                    defaults={
                        'context': normalize_context(context),
                        'value': value_to_store,
                        'status': status,
                        'error': error
                    }
                )
                if created:
                    # Link dependencies
                    for dep_id, dep_inst in dep_instances.items():
                        FactInstanceDependency.objects.create(
                            parent_instance=instance,
                            dependency_instance=dep_inst,
                            dependency_fact_id=dep_id
                        )
        except IntegrityError:
            # Race condition: another process created it. Re-fetch.
            instance = FactInstance.objects.get(
                fact_version=spec.version_obj,
                context_hash=ctx_hash
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

    # Cycle detection
    graph = build_dependency_graph(reg)
    cycles = detect_cycles(graph)
    if cycles:
        raise ValueError(f"Cycle detected in fact dependencies: {cycles}")

    return reg

def create_dynamic_producer(code_str):
    # We just return the code string or a wrapper, 
    # but for safe_execute we need the code to be executed in a restricted env.
    # Here we return a callable that safe_execute can use or inspect.
    # To keep it simple with existing structure, we'll return a wrapper that
    # executes the code. But safe_execute will handle the isolation.
    
    def dynamic_producer(deps, context):
        # This function body is what runs inside the safe environment
        local_scope = {}
        # Restricted globals are handled in safe_execute_worker
        # But for local testing without safe_execute (if needed), we can have a fallback?
        # No, we should enforce safe_execute.
        # However, the `producer` field in FactSpec expects a callable.
        # We will attach the code to the function object so safe_execute can retrieve it.
        pass
    
    dynamic_producer.code = code_str
    return dynamic_producer

# --- Safe Execution ---

def safe_execute_worker(code_str, deps, context, result_queue):
    """
    Worker function to run in a separate process.
    """
    try:
        # Restricted globals
        safe_globals = {
            "__builtins__": {
                "len": len, "min": min, "max": max, "sum": sum, "abs": abs,
                "sorted": sorted, "range": range, "enumerate": enumerate,
                "map": map, "filter": filter, "any": any, "all": all,
                "list": list, "dict": dict, "set": set, "tuple": tuple,
                "int": int, "float": float, "str": str, "bool": bool,
                "print": print, # Optional, maybe redirect stdout
            },
            "pd": pd, # Whitelisted pandas
            "date": date,
            "datetime": datetime,
            "Sum": Sum,
            # Models are tricky in multiprocessing because of DB connections.
            # Ideally, we pass data in `deps` and `context` and avoid DB access in facts.
            # But existing code uses models. 
            # For now, we'll allow models but Django DB connection might break in fork.
            # Best practice: Facts should only use `deps` and `context`.
            # If we must use models, we need to ensure DB connections are handled.
            # Given the constraints, let's assume facts should rely on deps.
            # But `all_transactions` uses models. 
            # We will allow models for now but this is risky in multiprocessing without care.
            "BankTransaction": BankTransaction,
            "CreditCardTransaction": CreditCardTransaction,
            "Account": Account
        }
        
        local_scope = {}
        wrapped_code = f"def dynamic_producer(deps, context):\n" + "\n".join(["    " + line for line in code_str.splitlines()])
        
        exec(wrapped_code, safe_globals, local_scope)
        func = local_scope['dynamic_producer']
        
        # Execute
        res = func(deps, context)
        result_queue.put({"status": "success", "value": res})
    except Exception as e:
        result_queue.put({"status": "error", "error": str(e)})

def safe_execute(producer_func, deps, context, logic_type='python', timeout=5):
    """
    Executes the producer in a separate process with timeout.
    """
    if not hasattr(producer_func, 'code'):
        # It's a native python function (not dynamic), run directly
        return producer_func(deps, context)

    code_str = producer_func.code
    
    if logic_type == 'expression':
        # Use simpleeval for expressions
        # Combine deps and context into names
        names = {**deps, **context}
        return execute_expression(code_str, names)

    # Python execution
    result_queue = multiprocessing.Queue()
    
    # We need to close DB connections before forking to avoid issues
    # (Django handles this usually, but good to be safe if using 'spawn')
    # For 'fork' (default on Linux/Mac), it's okay but connections are shared.
    # Mac defaults to 'spawn' in Python 3.8+.
    
    p = multiprocessing.Process(target=safe_execute_worker, args=(code_str, deps, context, result_queue))
    p.start()
    p.join(timeout)
    
    if p.is_alive():
        p.terminate()
        p.join()
        raise TimeoutError("Fact computation timed out")
        
    if result_queue.empty():
        raise RuntimeError("Fact computation crashed without result")
        
    result = result_queue.get()
    if result['status'] == 'error':
        raise RuntimeError(result['error'])
        
    return result['value']
