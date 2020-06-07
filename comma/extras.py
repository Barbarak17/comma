import codecs
import collections
import csv
import io
import os
import pathlib
import urllib, urllib.parse
import zipfile

import comma.helpers


__author__ = ("Jérémie Lumbroso <lumbroso@cs.princeton.edu>")

__all__ = [
    "detect_csv_type",
    "detect_encoding",
    "is_binary_string",
]


# Better CSV dialect detection, thanks to clevercsv

detect_csv_type = None

try:
    import clevercsv
    
    def detect_csv_type(sample, delimiters=None):
        sniffer = clevercsv.Sniffer()
        truncated_sample = sample[:comma.helpers.MAX_SAMPLE_CHUNKSIZE]
        simple_dialect = sniffer.detect(sample=truncated_sample, delimiters=delimiters)
        line_terminator = comma.helpers.detect_line_terminator(truncated_sample)

        dialect = simple_dialect.to_csv_dialect()
        dialect.lineterminator = line_terminator

        return {
            "dialect": dialect,
            "simple_dialect": simple_dialect,
            "has_header": sniffer.has_header(sample=truncated_sample),
            "line_terminator": line_terminator,
        }

except ImportError:
    clevercsv = None
    
    # define a helper based on the standard CSV package
    def detect_csv_type(sample, delimiters=None):
        sniffer = csv.Sniffer()
        truncated_sample = sample[:comma.helpers.MAX_SAMPLE_CHUNKSIZE]

        line_terminator = comma.helpers.detect_line_terminator(truncated_sample)

        dialect = sniffer.sniff(sample=truncated_sample, delimiters=delimiters)
        dialect.lineterminator = line_terminator

        return {
            "dialect": dialect,
            "simple_dialect": None,
            "has_header": sniffer.has_header(sample=truncated_sample),
            "line_terminator": line_terminator,
        }


# Better detection of binary data (i.e., zipped files), thanks to binaryornot


# In case the package is not available: Define our own helper method
# Based on file(1), see https://stackoverflow.com/a/7392391/408734
TEXT_CHARS = bytearray({7,8,9,10,12,13,27} | set(range(0x20, 0x100)) - {0x7f})


def _is_binary_string_internal(bytestring):
    return bool(bytestring.translate(None, TEXT_CHARS))


_is_binary_string = _is_binary_string_internal

try:
    # See https://github.com/audreyr/binaryornot/
    import binaryornot
    import binaryornot.helpers
    
    # Alias to helper method
    _is_binary_string = binaryornot.helpers.is_binary_string

except ImportError:  # pragma: no cover
    binaryornot = None


def is_binary_string(bytestring, truncate=True):
    """
    Detect, using heuristics, whether a string of bytes is text or binary data.
    If available, this will use the `binaryornot` lightweight package.
    """
    
    if bytestring is None:
        return False
    
    bytestring_length = -1
    try:
        bytestring_length = len(bytestring)
        
    except TypeError:
        return False
    
    if truncate and bytestring_length > comma.helpers.MAX_SAMPLE_CHUNKSIZE:
        return _is_binary_string(bytestring[:comma.helpers.MAX_SAMPLE_CHUNKSIZE])
    
    return _is_binary_string(bytestring)


# Better encoding detection

# Borrowed from requests.util, helper method to detect encoding of JSON
# outputs returned by the HTTP requests.
#
# See https://github.com/psf/requests/blob/3e7d0a873f838e0001f7ac69b1987147128a7b5f/requests/utils.py#L856-L891


# Null bytes; no need to recreate these on each call to guess_json_utf

_null = '\x00'.encode('ascii')  # encoding to ASCII for Python 3
_null2 = _null * 2
_null3 = _null * 3


def _detect_encoding_by_bom(data, default=None):
    """
    :rtype: str
    """

    # JSON always starts with two ASCII characters, so detection is as
    # easy as counting the nulls and from their location and count
    # determine the encoding. Also detect a BOM, if present.

    sample = data[:4]

    if sample in (codecs.BOM_UTF32_LE, codecs.BOM_UTF32_BE):
        return 'utf-32'     # BOM included
    if sample[:3] == codecs.BOM_UTF8:
        return 'utf-8-sig'  # BOM included, MS style (discouraged)
    if sample[:2] in (codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE):
        return 'utf-16'     # BOM included

    nullcount = sample.count(_null)

    if nullcount == 0:
        return default

    if nullcount == 2:
        if sample[::2] == _null2:   # 1st and 3rd are null
            return 'utf-16-be'
        if sample[1::2] == _null2:  # 2nd and 4th are null
            return 'utf-16-le'
        # Did not detect 2 valid UTF-16 ascii-range characters

    if nullcount == 3:
        if sample[:3] == _null3:
            return 'utf-32-be'
        if sample[1:] == _null3:
            return 'utf-32-le'
        # Did not detect a valid UTF-32 ascii-range character

    return default


detect_encoding = _detect_encoding_by_bom

# If chardet is available, use it as a second round of guessing
# if the previous method was unsuccessful

try:
    import chardet
    
    def detect_encoding(sample, default="utf-8"):
        # First try a fool-proof deterministic method
        encoding = _detect_encoding_by_bom(sample)
        if encoding is not None:
            return encoding
        
        # If that doesn't work, try a heuristic
        result = chardet.detect(sample)
        if result is not None and result.get("encoding") is not None:
            return result.get("encoding")
        
        return default
    
except ImportError:
    chardet = None


