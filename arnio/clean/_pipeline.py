"""Pipeline class and ``clean()`` function."""

from __future__ import annotations

import json
from typing import Any

from arnio.adapt._detect import resolve_adapter
from arnio.clean._registry import get_step
from arnio.exceptions import PipelineError

# Step specification types that users can pass:
#   - str:                    "strip_whitespace"
#   - tuple[str, dict]:       ("normalize_case", {"case": "lower"})
StepSpec = str | tuple[str, dict[str, Any]]


def _normalize_step(spec: StepSpec) -> tuple[str, dict[str, Any]]:
    """Normalize a step specification to (name, params)."""
    if isinstance(spec, str):
        return spec, {}
    if isinstance(spec, tuple) and len(spec) == 2:
        name, params = spec
        if isinstance(name, str) and isinstance(params, dict):
            return name, params
    raise TypeError(
        f"Step must be a string or (string, dict) tuple, got {type(spec).__name__}: {spec!r}"
    )


def clean(data: Any, steps: list[StepSpec]) -> Any:
    """Apply declarative cleaning operations and return cleaned data.

    **Critical rule:** The return type matches the input type. If a pandas
    DataFrame goes in, a pandas DataFrame comes out. If a list of dicts
    goes in, a list of dicts comes out.

    Args:
        data: Any supported data type.
        steps: List of step specifications. Each step is either:
            - A string: ``"strip_whitespace"``
            - A tuple: ``("normalize_case", {"case": "lower"})``

    Returns:
        Cleaned data in the same type as the input.
    """
    adapter = resolve_adapter(data)
    adapter = adapter.working_copy()

    for idx, spec in enumerate(steps):
        name, params = _normalize_step(spec)
        step_fn = get_step(name)

        try:
            adapter = step_fn(adapter, **params)
        except Exception as exc:
            raise PipelineError(name, idx, exc) from exc

    return adapter.unwrap()


class Pipeline:
    """Reusable, serializable cleaning pipeline.

    A pipeline is a sequence of cleaning steps that can be defined once
    and applied to multiple datasets.

    Examples:
        >>> pipe = ar.Pipeline([
        ...     "strip_whitespace",
        ...     "drop_duplicates",
        ...     ("normalize_case", {"case": "lower"}),
        ... ])
        >>> cleaned_df = pipe.run(df)
        >>> pipe.to_yaml()  # Save for version control
    """

    __slots__ = ("_steps",)

    def __init__(self, steps: list[StepSpec]) -> None:
        # Validate all steps eagerly
        self._steps: list[tuple[str, dict[str, Any]]] = [
            _normalize_step(s) for s in steps
        ]

    @property
    def steps(self) -> list[tuple[str, dict[str, Any]]]:
        """Return the pipeline's step definitions."""
        return list(self._steps)

    def run(self, data: Any) -> Any:
        """Execute the pipeline on data.

        Args:
            data: Any supported data type.

        Returns:
            Cleaned data in the same type as the input.
        """
        # Reconstruct step specs for clean()
        step_specs: list[StepSpec] = [
            name if not params else (name, params)
            for name, params in self._steps
        ]
        return clean(data, step_specs)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the pipeline to a dict."""
        return {
            "steps": [
                {"name": name, "params": params}
                for name, params in self._steps
            ],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Pipeline:
        """Deserialize a pipeline from a dict."""
        if not isinstance(data, dict):
            raise ValueError(f"Expected a dictionary, got {type(data).__name__}")
        
        steps: list[StepSpec] = []
        raw_steps = data.get("steps", [])
        if not isinstance(raw_steps, list):
            raise ValueError(f"Pipeline 'steps' must be a list, got {type(raw_steps).__name__}")
            
        for step_data in raw_steps:
            name = step_data["name"]
            params = step_data.get("params", {})
            if params:
                steps.append((name, params))
            else:
                steps.append(name)
        return cls(steps)

    def to_json(self, *, indent: int = 2) -> str:
        """Serialize to a JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    @classmethod
    def from_json(cls, json_str: str) -> Pipeline:
        """Deserialize from a JSON string."""
        return cls.from_dict(json.loads(json_str))

    def to_yaml(self) -> str:
        """Serialize to a YAML string.

        Requires PyYAML (``pip install arnio[yaml]``).
        """
        try:
            import yaml
        except ImportError:
            raise ImportError(
                "PyYAML is required for YAML serialization. "
                "Install it with: pip install arnio[yaml]"
            ) from None

        return yaml.dump(self.to_dict(), default_flow_style=False, sort_keys=False)

    @classmethod
    def from_yaml(cls, yaml_str: str) -> Pipeline:
        """Deserialize from a YAML string.

        Requires PyYAML (``pip install arnio[yaml]``).
        """
        try:
            import yaml
        except ImportError:
            raise ImportError(
                "PyYAML is required for YAML deserialization. "
                "Install it with: pip install arnio[yaml]"
            ) from None

        return cls.from_dict(yaml.safe_load(yaml_str))

    def __len__(self) -> int:
        return len(self._steps)

    def __repr__(self) -> str:
        step_names = [name for name, _ in self._steps]
        return f"Pipeline({step_names})"
