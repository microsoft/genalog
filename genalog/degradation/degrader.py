# ---------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License.
# ---------------------------------------------------------

import copy
import inspect
from enum import Enum

from genalog.degradation import effect

DEFAULT_METHOD_PARAM_TO_INCLUDE = "src"


class ImageState(Enum):
    ORIGINAL_STATE = "ORIGINAL_STATE"
    CURRENT_STATE = "CURRENT_STATE"


class Degrader:
    """ An object for applying multiple degradation effects onto an image"""

    def __init__(self, effects):
        """
        Arguments:
            effects (list) : a list of 2-element tuple (method_name, method_kwargs) where:

                :method_name: the name of the degradation method (method must be defined in 'genalog.degradation.effect')
                :method_kwargs: the keyword arguments of the corresponding method

        Example:
        ::

            [
                ("blur", {"radius": 3}),
                ("bleed_through", {"alpha": 0.8),
                ("morphology", {"operation": "open", "kernel_shape": (3,3), "kernel_type": "ones"})
            ]

        The example above will apply degradation effects to the images
        in the following sequence:
        ::

                "blur" -> "bleed_through" -> "morphological operation (open)"
        """
        Degrader.validate_effects(effects)
        self.effects_to_apply = copy.deepcopy(effects)
        self._add_default_method_param()

    @staticmethod
    def validate_effects(effects):
        """Validate the effects list

        Arguments:
            effects (list) : a list of 2-element tuple ``(method_name, method_kwargs)``
                that defines:

                1. ``method_name`` : the name of the degradation method \
                    (method must be defined in ``genalog.degradation.effect``)
                2. ``method_kwargs`` : the keyword arguments of the corresponding method

        Example:
        ::

            [
                ("blur", {"radius": "3"}),
                ("bleed_through", {"alpha":"0.8"}),
                ("morphology", {"operation": "open", "kernel_shape": (3,3), "kernel_type": "ones"}),
            ]

        Raises:
            ValueError: raise this error when:
                ``method_name`` not defined in "genalog.degradation.effect"
                ``method_kwargs`` is not a valid keyword arguments in the corresponding method
        """
        for effect_tuple in effects:
            method_name, method_kwargs = effect_tuple
            try:
                # Try to find corresponding degradation method in the module
                method = getattr(effect, method_name)
            except AttributeError:
                raise ValueError(
                    f"Method '{method_name}' is not defined in 'genalog.degradation.effect'"
                )
            # Get the method signatures
            method_sign = inspect.signature(method)
            # Check if method parameters are valid
            for (
                param_name
            ) in method_kwargs.keys():  # i.e. ["operation", "kernel_shape", ...]
                if param_name not in method_sign.parameters:
                    method_args = [param for param in method_sign.parameters]
                    raise ValueError(
                        f"Invalid parameter name '{param_name}' for method 'genalog.degradation.effect.{method_name}()'. " +
                        f"Method parameter names are: {method_args}"
                    )

    def _add_default_method_param(self):
        """All methods in "genalog.degradation.effect" module have a required
        method parameter named "src". This parameter will be included if not provided
        by the input keyword argument dictionary.
        """
        for effect_tuple in self.effects_to_apply:
            method_name, method_kwargs = effect_tuple
            if DEFAULT_METHOD_PARAM_TO_INCLUDE not in method_kwargs:
                method_kwargs[
                    DEFAULT_METHOD_PARAM_TO_INCLUDE
                ] = ImageState.CURRENT_STATE

    def apply_effects(self, src):
        """Apply degradation effects in sequence

        Arguments:
            src (numpy.ndarray) : source image of shape (rows, cols)

        Returns:
             a copy of the source image {numpy.ndarray} after apply the effects
        """
        self.original_state = src
        self.current_state = src
        # Preserve the original effect instructions
        effects_to_apply = copy.deepcopy(self.effects_to_apply)
        for effect_tuple in effects_to_apply:
            method_name, method_kwargs = effect_tuple
            method = getattr(effect, method_name)
            # Replace constants (i.e. ImageState.ORIGINAL_STATE) with actual image state
            method_kwargs = self.insert_image_state(method_kwargs)
            # Calling the degradation method
            self.current_state = method(**method_kwargs)
        return self.current_state

    def insert_image_state(self, kwargs):
        """Replace the enumeration (ImageState) with the actual image in
        the keyword argument dictionary

        Arguments:
            kwargs (dict) : keyword argument dictionary

            Ex: {"src": ImageState.ORIGINAL_STATE, "radius": 5}

        Returns:
            return keyword argument dictionary replaced with
            reference to the image
        """
        for keyword, argument in kwargs.items():
            if argument is ImageState.ORIGINAL_STATE:
                kwargs[keyword] = self.original_state.copy()
            if argument is ImageState.CURRENT_STATE:
                kwargs[keyword] = self.current_state.copy()
        return kwargs
