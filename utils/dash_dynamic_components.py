import functools
import json
from dash import callback, ALL, ALLSMALLER, ctx
from dash.dependencies import Input, Output, State

_ACTIVE = 'active_'
_ID = 'id_'


def add_active_to_component_id(component_id, active=True):
    if isinstance(component_id, dict):
        component_id = dict(component_id)
        if _ACTIVE in component_id:
            raise ValueError(f'key \'{_ACTIVE}\' cannot be present in component_id={component_id}')
        component_id[_ACTIVE] = active
    else:
        component_id = {_ID: component_id, _ACTIVE: active}
    return component_id


class _DynamicDashDependency:
    def __init__(self, component_id, component_property, **kwargs):
        self.component_id = component_id
        self.component_property = component_property
        self.kwargs = kwargs

    def __str__(self):
        return f"{self.component_id_str()}.{self.component_property}"

    def __repr__(self):
        return f"<{self.__class__.__name__} `{self}`>"

    def component_id_str(self):
        i = self.component_id

        def _dump(v):
            return json.dumps(v, sort_keys=True, separators=(",", ":"))

        def _json(k, v):
            vstr = v.to_json() if hasattr(v, "to_json") else json.dumps(v)
            return f"{json.dumps(k)}:{vstr}"

        if isinstance(i, dict):
            return "{" + ",".join(_json(k, i[k]) for k in sorted(i)) + "}"

        return i


class DynamicOutput(_DynamicDashDependency, Output):
    pass


class DynamicInput(_DynamicDashDependency, Input):
    pass


class DynamicState(_DynamicDashDependency, State):
    pass


_dash_dependency_types_mapping = {
    DynamicOutput: Output,
    DynamicInput: Input,
    DynamicState: State,
}


def _transform_dash_dependency(dash_dependency):
    if isinstance(dash_dependency, _DynamicDashDependency):
        new_component_id = add_active_to_component_id(dash_dependency.component_id, active=ALL)
        new_dash_dependency_type = _dash_dependency_types_mapping[type(dash_dependency)]
        return new_dash_dependency_type(new_component_id, dash_dependency.component_property, **dash_dependency.kwargs)
    else:
        return dash_dependency


def _does_dash_dependency_become_one_elem_list(dash_dependency):
    if not isinstance(dash_dependency, _DynamicDashDependency):
        return False
    component_id = dash_dependency.component_id
    if not isinstance(component_id, dict):
        return True
    return all(v is not ALL and v is not ALLSMALLER for v in component_id.values())


def dynamic_callback(*args, **kwargs):
    """
    Supports outputs, inputs and states as positional arguments in a flat form. Same for callback function:
    only positional arguments.
    :param args:
    :param kwargs:
    :return:
    """
    new_args = tuple(map(_transform_dash_dependency, args))

    inputs = filter(lambda arg: isinstance(arg, (Input, State, DynamicInput, DynamicState)), args)
    input_become_one_elem_list = list(map(_does_dash_dependency_become_one_elem_list, inputs))

    outputs = filter(lambda arg: isinstance(arg, (Output, DynamicOutput)), args)
    output_become_one_elem_list = list(map(_does_dash_dependency_become_one_elem_list, outputs))

    def callback_dynamic_with_args(callback_func):
        @functools.wraps(callback_func)
        def new_callback_func(*func_args):
            def get_single_item(l):
                if len(l) > 1:
                    raise ValueError(f'l should have at most 1 element; len(l)={len(l)}, l={l}')
                try:
                    return l[0]
                except IndexError:
                    return None

            new_func_args = tuple(
                get_single_item(arg) if becomes_list else arg
                for arg, becomes_list in zip(func_args, input_become_one_elem_list)
            )
            callback_result = callback_func(*new_func_args)

            if len(output_become_one_elem_list) == 0:
                if callback_result is not None:
                    raise RuntimeError(
                        f'callback returned not None but there is no Outputs; callback_result={callback_result}'
                    )
                return None
            elif len(output_become_one_elem_list) == 1:
                callback_result = [callback_result]
                ctx_outputs_list = [ctx.outputs_list]
            else:
                ctx_outputs_list = ctx.outputs_list

            new_callback_result = []
            for result_item, becomes_list, output_item in zip(callback_result, output_become_one_elem_list, ctx_outputs_list):
                if becomes_list:
                    if not isinstance(output_item, list):
                        raise RuntimeError(f'output_item should be a list; got type(output_item)={type(output_item)}; output_item={output_item}; ctx.outputs_list={ctx.outputs_list}')
                    if len(output_item) > 1:
                        raise RuntimeError(f'output_item should be 1- or 0-element list; got len(output_item)={len(output_item)}; output_item={output_item}; ctx.outputs_list={ctx.outputs_list}')
                    if len(output_item) == 0:
                        # we must ignore the result_item, whatever it is, because ALL wildcard matched no components; normally, the output_item should be just dash.no_update
                        new_result_item = []
                    else:
                        new_result_item = [result_item]
                else:
                    new_result_item = result_item
                new_callback_result.append(new_result_item)
            new_callback_result = tuple(new_callback_result)

            if len(output_become_one_elem_list) == 1:
                new_callback_result = new_callback_result[0]

            return new_callback_result

        return callback(*new_args, **kwargs)(new_callback_func)

    return callback_dynamic_with_args
