import re

import numpy as np

from easycv.errors import (
    ArgumentNotProvidedError,
    InvalidArgumentError,
    InvalidMethodError,
)


class Validator:
    """
    This class is the base for all Validators. All Validators should be child from this class \
    and override the `validate` method.
    If default is set to None the argument is required and the Validator will throw an \
    :class:`~easycv.errors.transforms.ArgumentNotProvidedError`.

    :param default: Default value for the argument, defaults to None
    :type default: :class:`object`, optional
    """

    def __init__(self, default=None):
        self._default = default

    @property
    def default(self):
        return self._default

    def check(self, arg_name, kwargs):
        """
        Check if an argument satisfies the Validator conditions. If the default value is None
        the Validator throws an :class:`~easycv.errors.transforms.ArgumentNotProvidedError`, \
        otherwise it calls the validate method to make sure all conditions are verified and if \
        not, throws an :class:`~easycv.errors.transforms.InvalidArgumentError` with the \
        appropriate error message.

        :param arg_name: Name of the argument to validate
        :type arg_name: :class:`str`
        :param kwargs: Dictionary containing all arguments and their values
        :type kwargs: :class:`dict`
        """
        arg = kwargs.get(arg_name)
        if arg is None:
            if self._default is None:
                raise ArgumentNotProvidedError(arg_name)
            else:
                return self._default
        else:
            return self.validate(arg_name, kwargs)

    def validate(self, arg_name, kwargs, inside_list=False):
        """
        Every Validator should override this method. This method should validate the arguments \
        named `arg_name` from `kwargs` by checking if it verifies the constrains. If the argument \
        is invalid it should throw an :class:`~easycv.errors.transforms.InvalidArgumentError` \
        with a message clarifying what is invalid and how to correct it. If this Validator is \
        inside a the message should reflect that.

        :param arg_name: Name of the argument to validate
        :type arg_name: :class:`str`
        :param kwargs: Dictionary containing all arguments and their values
        :type kwargs: :class:`dict`
        :param inside_list: True if this Validator is inside a List, defaults to False
        :type inside_list: :class:`bool`, optional
        """
        pass

    def accept(self, other):
        """
        Every Validator should override this method. This method should check if the given
        validator can be accepted with the current validator parameters.

        :param other: Instance of a validator
        :type other: :class:`str`
        """
        pass


class Regex(Validator):
    """
    Validator to check if an argument verifies a certain regex pattern. To add regex flags just \
    include them in the constructor like an argument.

    :param pattern: Regex pattern to validate argument
    :type pattern: :class:`str`
    :param description: Description of accepted values, used in the error message
    :type description: :class:`str`, optional
    :param flags: Regex Flags
    :type flags: :class:`enum 'RegexFlag'`, optional
    """

    def __init__(self, pattern, *flags, description=None, default=None):
        self.pattern = pattern
        self._description = description
        self._regex = re.compile(pattern, *flags)
        super().__init__(default=default)

    def validate(self, arg_name, kwargs, inside_list=False):
        arg = kwargs.get(arg_name)
        match = self._regex.match(str(arg))
        if not bool(match):
            if self._description is not None:
                raise InvalidArgumentError(
                    'Invalid value for "{}". '.format(arg_name)
                    + "Must be a/an {}.".format(self._description)
                )
            else:
                raise InvalidArgumentError(
                    'Invalid value for "{}". '.format(arg_name)
                    + 'Must satisfy this regex pattern "{}.'.format(self.pattern)
                )
        else:
            return arg

    def accept(self, other):
        return isinstance(other, Regex) and self.pattern == other.pattern


class Number(Validator):
    """
    Validator to check if an argument is a number. More restrictions can be applied through \
    the keyword arguments.

    :param min_value: Minimum value allowed, defaults to -inf
    :type min_value: :class:`int`/:class:`float`, optional
    :param max_value: Maximum value allowed, defaults to inf
    :type max_value: :class:`int`/:class:`float`, optional
    :param only_integer: Allow only integers, defaults to False
    :type only_integer: :class:`bool`, optional
    :param only_odd: Allow only odd numbers, defaults to False
    :type only_odd: :class:`bool`, optional
    :param only_even: Allow only even numbers, defaults to False
    :type only_even: :class:`bool`, optional
    """

    def __init__(
        self,
        min_value=-float("inf"),
        max_value=float("inf"),
        only_integer=False,
        only_odd=False,
        only_even=False,
        default=None,
    ):
        self.only_odd = only_odd
        self.only_even = only_even
        self.min_value = min_value
        self.max_value = max_value
        self.only_integer = only_integer
        super().__init__(default=default)

    def validate(self, arg_name, kwargs, inside_list=False):
        arg = kwargs.get(arg_name)
        allowed_types = (int,) if self.only_integer else (int, float)
        if (
            not isinstance(arg, allowed_types)
            or not (self.min_value <= arg <= self.max_value)
            or (self.only_odd and arg % 2 == 0)
            or (self.only_even and arg % 2 != 0)
        ):
            if inside_list:
                prefix = "a list/tuple of " + (
                    "integers" if self.only_integer else "numbers"
                )
            else:
                if self.only_odd:
                    prefix = "an odd integer" if self.only_integer else "an odd number"
                elif self.only_even:
                    prefix = "an odd integer" if self.only_integer else "an even number"
                else:
                    prefix = "an integer" if self.only_integer else "a number"
            raise InvalidArgumentError(
                'Invalid value for "{}". Must be {} '.format(arg_name, prefix)
                + "between {} and {}.".format(self.min_value, self.max_value)
            )
        return arg

    def accept(self, other):
        if isinstance(other, Number):
            if self.min_value <= other.min_value and self.max_value >= other.max_value:
                flag = True
                if not other.only_odd and self.only_odd:
                    flag = False
                if not other.only_even and self.only_even:
                    flag = False
                if not other.only_integer and self.only_integer:
                    flag = False
                return flag
        return False


class Option(Validator):
    """
    Validator to check if an argument one of the allowed options.

    :param options: Allowed options
    :type options: :class:`list`
    """

    def __init__(self, options, default=None):
        self.options = options
        default = None if default is None else options[default]
        super().__init__(default=default)

    def validate(self, arg_name, kwargs, inside_list=False):
        arg = kwargs.get(arg_name)
        if arg not in self.options:
            raise InvalidArgumentError(
                'Invalid value for "{}". '.format(arg_name)
                + "Possible values: {}".format(", ".join(self.options))
            )
        else:
            return arg

    def accept(self, other):
        return isinstance(other, Option) and all(
            [opt in self.options for opt in other.options]
        )


class Method(Validator):
    """
    Validator to check if a method is valid and if the arguments called for that method are valid.

    :param methods: List containing supported methods or dictionary with methods as keys and \
    allowed arguments for that method as values
    :type methods: :class:`list`/:class:`dict`
    :param name: Name of the method attribute, this is the name of the parameter representing \
    the method sent to ``apply``, defaults to method
    :type name: :class:`str`
    """

    def __init__(self, methods, name="method", default=None):
        self.methods = methods
        self.method_name = name
        super().__init__(default=default)

    @property
    def contains_allowed(self):
        return isinstance(self.methods, dict)

    @property
    def allowed_methods(self):
        if self.contains_allowed:
            return list(self.methods.keys())
        else:
            return self.methods

    def allowed_args(self, method):
        return self.methods[method]

    def add_unspecified_allowed_args(self, default_args):
        specified_args = set(sum(self.methods.values(), []))
        not_specified = set(default_args) - specified_args - {"method"}
        if not_specified:
            for method in self.methods:
                self.methods[method].extend(not_specified)

    def check(self, arg_name, kwargs):
        arg = kwargs.get(arg_name)
        if arg is None:
            if self._default is None:
                raise ArgumentNotProvidedError(arg_name)
            else:
                kwargs[arg_name] = self._default
        return self.validate(arg_name, kwargs)

    def validate(self, arg_name, kwargs, inside_list=False):
        arg = kwargs.pop(arg_name)

        if arg not in self.methods:
            raise InvalidMethodError(
                self.methods.keys() if self.contains_allowed else self.methods
            )

        if self.contains_allowed:
            if any(a not in self.methods[arg] for a in kwargs if a != "method"):
                raise InvalidArgumentError(
                    'Invalid arguments for method "{}". '.format(arg)
                    + "Allowed arguments: {}".format(", ".join(self.methods[arg]))
                )

        return arg

    def accept(self, other):
        return isinstance(other, Method) and all(
            [opt in self.methods for opt in other.methods]
        )


class Type(Validator):
    """
    Validator to check if an argument is from the specified type.

    :param arg_type: Allowed type
    :type arg_type: :class:`type`
    """

    def __init__(self, arg_type, default=None):
        self.arg_type = arg_type
        super().__init__(default=default)

    def validate(self, arg_name, kwargs, inside_list=False):
        arg = kwargs.get(arg_name)
        if not isinstance(arg, self.arg_type):
            prefix = "a list/tuple of objects" if inside_list else "an object"
            raise InvalidArgumentError(
                'Invalid value for "{}". '.format(arg_name)
                + "Must be {} from class {}".format(prefix, self.arg_type.__name__)
            )
        return arg

    def accept(self, other):
        return isinstance(other, Type) and self.arg_type == other.arg_type


class List(Validator):
    """
    Validator to check if an argument is a list/tupple or a numpy array containing only elements \
    that satisfies the given Validator.

    :param validator: Validator to apply to each element
    :type validator: :class:`Validator`
    :param length: Mandatory length, defaults to None
    :type length: :class:`int`, optional
    """

    def __init__(self, validator, length=None, default=None):
        self.validator = validator
        self.length = length
        super().__init__(default=default)

    def validate(self, arg_name, kwargs, inside_list=False):
        arg = kwargs.get(arg_name)
        if not isinstance(arg, (list, tuple, np.ndarray)):
            raise InvalidArgumentError(
                'Invalid value for "{}". Must be a list or tuple.'.format(arg_name)
            )
        if self.length is not None and len(arg) != self.length:
            raise InvalidArgumentError(
                'Invalid value for "{}". Must be {} elements long.'.format(
                    arg_name, self.length
                )
            )

        for e in list(arg):
            self.validator.validate(arg_name, {arg_name: e}, inside_list=True)
        return arg

    def accept(self, other):
        if isinstance(other, List):
            if self.length() == other.length():
                return self.validator.accept(other.validator)
        return False
