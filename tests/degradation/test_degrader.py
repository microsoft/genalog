import copy
from unittest.mock import patch

import numpy as np
import pytest

from genalog.degradation.degrader import DEFAULT_METHOD_PARAM_TO_INCLUDE
from genalog.degradation.degrader import Degrader, ImageState

MOCK_IMAGE_SHAPE = (4, 3)
MOCK_IMAGE = np.arange(12, dtype=np.uint8).reshape(MOCK_IMAGE_SHAPE)


@pytest.fixture
def empty_degrader():
    effects = []
    return Degrader(effects)


@pytest.fixture(
    params=[
        [("blur", {"radius": 5})],
        [("blur", {"src": ImageState.ORIGINAL_STATE, "radius": 5})],
        [("blur", {"src": ImageState.CURRENT_STATE, "radius": 5})],
        [
            ("morphology", {"src": ImageState.ORIGINAL_STATE, "operation": "open"}),
            ("morphology", {"operation": "close"}),
            ("morphology", {"src": ImageState.ORIGINAL_STATE, "operation": "dilate"}),
            ("morphology", {"operation": "erode"}),
        ],
        [
            ("blur", {"radius": 5}),
            (
                "bleed_through",
                {
                    "src": ImageState.CURRENT_STATE,
                    "alpha": 0.7,
                    "background": ImageState.ORIGINAL_STATE,
                },
            ),
            (
                "morphology",
                {"operation": "open", "kernel_shape": (3, 3), "kernel_type": "ones"},
            ),
        ],
    ]
)
def degrader(request):
    effects = request.param
    return Degrader(effects)


def test_empty_degrader_init(empty_degrader):
    assert empty_degrader.effects_to_apply == []


def test_degrader_init(degrader):
    assert degrader.effects_to_apply is not []
    for effect_tuple in degrader.effects_to_apply:
        method_name, method_kwargs = effect_tuple
        assert DEFAULT_METHOD_PARAM_TO_INCLUDE in method_kwargs
        param_value = method_kwargs[DEFAULT_METHOD_PARAM_TO_INCLUDE]
        assert (
            param_value is ImageState.ORIGINAL_STATE
            or param_value is ImageState.CURRENT_STATE
        )


@pytest.mark.parametrize(
    "effects, error_thrown",
    [
        ([], None),  # Empty effect
        (None, TypeError),
        ([("blur", {"radius": 5})], None),  # Validate input
        ([("not_a_func", {"radius": 5})], ValueError),  # Invalid method name
        ([("blur", {"not_a_argument": 5})], ValueError),  # Invalid kwargs
        ([("blur")], ValueError),  # Missing kwargs
        (
            [
                ("blur", {"radius": 5}),
                ("bleed_through", {"alpha": "0.8"}),
                ("morphology", {"operation": "open"}),
            ],
            None,
        ),  # Multiple effects
        (
            [
                ("blur", {"radius": 5}),
                ("bleed_through", {"not_argument": "0.8"}),
                ("morphology", {"missing value"}),
            ],
            ValueError,
        ),  # Multiple effects
    ],
)
def test_degrader_validate_effects(effects, error_thrown):
    if error_thrown:
        with pytest.raises(error_thrown):
            Degrader.validate_effects(effects)
    else:
        Degrader.validate_effects(effects)


def test_degrader_apply_effects(degrader):
    method_names = [effect[0] for effect in degrader.effects_to_apply]
    with patch("genalog.degradation.effect") as mock_effect:
        degrader.apply_effects(MOCK_IMAGE)
        for method in method_names:
            assert mock_effect[method].is_called()
        # assert degraded.shape == MOCK_IMAGE_SHAPE


def test_degrader_apply_effects_e2e(degrader):
    degraded = degrader.apply_effects(MOCK_IMAGE)
    assert degraded.shape == MOCK_IMAGE_SHAPE
    assert degraded.dtype == np.uint8


def test_degrader_instructions(degrader):
    original_instruction = copy.deepcopy(degrader.effects_to_apply)
    degrader.apply_effects(MOCK_IMAGE)
    degrader.apply_effects(MOCK_IMAGE)
    # Make sure the degradation instructions are not altered
    assert len(original_instruction) == len(degrader.effects_to_apply)
    for i in range(len(original_instruction)):
        org_method_name, org_method_arg = original_instruction[i]
        method_name, method_arg = degrader.effects_to_apply[i]
        assert org_method_name == method_name
        assert len(org_method_arg) == len(method_arg)
        for key in org_method_arg.keys():
            assert isinstance(org_method_arg[key], type(method_arg[key]))
            assert org_method_arg[key] == method_arg[key]
