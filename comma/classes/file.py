
import typing
import warnings

import comma.exceptions
import comma.helpers
import comma.typing


__author__ = "Jérémie Lumbroso <lumbroso@cs.princeton.edu>"

__all__ = [
    "CommaFile"
]


class CommaFile(object):
    """
    Store the metadata associated with a CSV/DSV file. This includes the
    `header` (a list of column names) if it exists; the `primary_key` (that is,
    whether one of the columns should function as an index for rows); and
    the internal parameters, such as dialect and encoding, that are detetcted
    when the table data was loaded.
    """

    # Internal instance variable containing header
    _header = None

    # Internal instance variable with params
    _params = None

    # "Primary key" through which to access the records
    _primary_key = None

    def __init__(
        self,
        header: comma.typing.OptionalHeaderType = None,
        primary_key: typing.Optional[str] = None,
        params: typing.Optional[comma.typing.CommaInfoParamsType] = None,
    ):
        """
        Creates a new `CommaFile` object. It is possible to specify a `header`,
        which should be an iterable of strings. If a `header` is specified, it
        is also possible to specify a `primary_key`, which should be an
        element of the `header` list, which will be used to index the rows.

        The `params` is a dictionary of settings that are typically
        autogenerated by the opening methods; they contain information such
        as the dialect, line terminator, etc..

        """

        if header is not None:
            try:
                self._header = list(map(str, header))
            except Exception as exc:
                raise comma.exceptions.CommaInvalidHeaderException(
                    "`header` does not seem to be an iterable of strings"
                )

        self._params = params
        self._primary_key = primary_key

    @property
    def header(self) -> comma.typing.OptionalHeaderType:
        """
        The header of the associated `CommaFile`, if such a header has been
        defined and `None` otherwise. The header is a list of strings, which
        are the names of the column of the dataset table. When specified, it
        is possible to access the columns of the associated `CommaTable` by
        their name, both to get a column-slice of the dataset, or the access
        that field in a row.
        """
        return self._header

    @header.setter
    def header(self, value: comma.typing.OptionalHeaderType):
        """
        Changes the header associated with this `CommaFile`; this operation
        only affects the metadata, but does not modify any of the underlying
        rows.
        """

        # equivalent to a delete

        if value is None:
            self._header = None
            return

        validated_header = comma.helpers.validate_header(value)

        # if we are replacing an existing header, check length

        if self._header is not None:
            old_length = len(self._header)
            new_length = len(validated_header)

            if old_length != new_length:
                warnings.warn(
                    "changing length of header; was {old}, now is {new}".format(
                        old=old_length,
                        new=new_length))

        self._header = validated_header

    @header.deleter
    def header(self):
        """
        Deletes the header associated with this `CommaFile`; this operation
        only affects the metadata, but does not modify any of the underlying
        rows.
        """
        self._header = None

    @property
    def primary_key(self) -> str:
        """
        This property can be set when the `header` property has also been
        defined. It should be either `None` (if unset) or the name of a
        column of `header`. The associated `CommaTable` will then allow
        for the access of records indexed by the column of that same name.
        """
        return self._primary_key

    @primary_key.setter
    def primary_key(self, value: str):
        """
        Change the `primary_key` of this object. Should refer to an
        element in `header`. Should not be set before setting `header`.
        """
        # shortcuts to un-setting the primary key
        if value is None or value == "" or value == False:
            del self.primary_key
            return

        # from this point on, consider we are setting the primary key

        # first check whether there are headers
        if self.header is None:
            raise comma.exceptions.CommaNoHeaderException(
                "cannot set the primary key of a `CommaFile` "
                "that does not have a header"
            )

        # next check if proposed header belongs to headers
        if value not in self.header:
            # Try to get a string representation of headers for diagnostic
            # purposes for user; yes, the exception is too broad because
            # we don't really care why the headers couldn't be converted
            # to string

            # Thanks @pylover!
            # See: https://gist.github.com/pylover/7870c235867cf22817ac5b096defb768

            # noinspection PyBroadException
            try:
                header_string = self.header.__repr__()
            except Exception:  # pylint: disable=too-general-exception
                header_string = ""

            raise comma.exceptions.CommaKeyError(
                "the requested primary key (" +
                value +
                ") is not one of the headers: " +
                header_string
            )

        # seems we have validated the primary key and so setting it
        self._primary_key = value

    @primary_key.deleter
    def primary_key(self):
        """
        Delete the `primary_key` of this `CommaFile`.
        """
        self._primary_key = None

